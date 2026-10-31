from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel, Field, ValidationError
from openai import OpenAIError
from typing import Any
from datetime import datetime, timedelta
from app.models.schemas import (
    PerformanceAnalysis,
    BestPracticesCheck,
    PromptImprovement,
    TokenReflection,
    PromptTokenAnalysis,
    PromptTokenInsights
)
from app.services.data_collector import ClaudeDataCollector
from app.services.analyzer import ClaudeAnalyzer
from app.config import get_settings, Settings
from app.services.settings_store import load_settings, redact, excluded
from app.services.cache_advice import build_cache_advice
from app.services.prompt_turns import classify_user_entry, summarize_turns
import json

router = APIRouter(prefix="/api/analysis", tags=["analysis"])


def get_collector(settings: Settings = Depends(get_settings)) -> ClaudeDataCollector:
    return ClaudeDataCollector(settings.claude_data_path, settings.database_path)


def get_analyzer(settings: Settings = Depends(get_settings)) -> ClaudeAnalyzer:
    settings.validate_openai_config()
    return ClaudeAnalyzer(settings.openai_api_key, settings.openai_model)


class PromptRequest(BaseModel):
    prompt: str = Field(min_length=5, max_length=20000)
    consent: bool
    project_path: str | None = None


class AdviceRequest(BaseModel):
    consent: bool
    prompt_excerpts: list[str] = Field(max_length=10)


class InsightsRequest(BaseModel):
    consent: bool
    period_days: int = Field(ge=1, le=365)
    summary: dict[str, Any]
    turns: list[dict[str, Any]] = Field(max_length=30)


def require_consent(consent: bool):
    if not consent:
        raise HTTPException(status_code=400, detail="Explicit consent is required to send data to OpenAI")


def analysis_response(model, operation):
    try:
        return model(**operation())
    except (ValueError, KeyError, TypeError, ValidationError, OpenAIError):
        raise HTTPException(status_code=502, detail="Analysis returned an invalid response")


@router.get("/performance", deprecated=True)
@router.get("/token-reflection", deprecated=True)
async def retired_analysis():
    # These endpoints previously fabricated scores or cost estimates.
    raise HTTPException(status_code=410, detail="This analysis is unavailable because its metrics were not evidence-based")


@router.get("/best-practices/preview")
async def preview_best_practices(days: int = Query(7, ge=1, le=365), collector: ClaudeDataCollector = Depends(get_collector)):
    config = load_settings(collector.db)
    end = datetime.now().date()
    rows = collector.db.get_entries_by_date_range((end - timedelta(days=days)).isoformat(), end.isoformat())
    excerpts = []
    for entry in reversed(rows):
        if entry.get("type") != "user" or excluded(entry.get("cwd"), config['excluded_projects']):
            continue
        kind, text, _ = classify_user_entry(entry)
        if kind == 'prompt' and text:
            excerpts.append(text[:300])
        if len(excerpts) == 10:
            break
    if not excerpts:
        raise HTTPException(status_code=404, detail="No eligible prompts found in the specified period")
    return {"prompt_excerpts": redact(excerpts, config['redact_literals'])}


@router.post("/best-practices", response_model=BestPracticesCheck)
async def check_best_practices(request: AdviceRequest, analyzer: ClaudeAnalyzer = Depends(get_analyzer), collector: ClaudeDataCollector = Depends(get_collector)):
    require_consent(request.consent)
    return analysis_response(BestPracticesCheck, lambda: analyzer.check_best_practices(redact(request.prompt_excerpts, load_settings(collector.db)['redact_literals'])))


@router.post("/improve-prompt/preview")
async def preview_prompt(request: PromptRequest, collector: ClaudeDataCollector = Depends(get_collector)):
    config = load_settings(collector.db)
    if request.project_path and excluded(request.project_path, config['excluded_projects']):
        raise HTTPException(status_code=403, detail="Project is excluded from external analysis")
    return {"prompt": redact(request.prompt, config['redact_literals']), "project_path": request.project_path}


@router.post("/improve-prompt", response_model=PromptImprovement)
async def improve_prompt(request: PromptRequest, analyzer: ClaudeAnalyzer = Depends(get_analyzer), collector: ClaudeDataCollector = Depends(get_collector)):
    require_consent(request.consent)
    config = load_settings(collector.db)
    if request.project_path and excluded(request.project_path, config['excluded_projects']):
        raise HTTPException(status_code=403, detail="Project is excluded from external analysis")
    if len(request.prompt.strip()) < 5:
        raise HTTPException(status_code=400, detail="Prompt is too short")
    return analysis_response(PromptImprovement, lambda: analyzer.suggest_prompt_improvements(redact(request.prompt, config['redact_literals'])))


@router.get("/recent-prompts")
async def get_recent_prompts(
    limit: int = Query(10, description="Number of recent prompts to retrieve"),
    collector: ClaudeDataCollector = Depends(get_collector)
):
    """最近のプロンプトを取得"""
    # 全セッションから取得（最大1000セッションまで検索）
    all_sessions = collector.get_recent_sessions(min(limit * 100, 1000))

    user_prompts = []
    for session in all_sessions:
        if session.get("type") == "user":
            message = session.get("message", {})

            # メッセージからテキストを抽出
            display = None

            if isinstance(message, dict):
                content = message.get("content")

                # contentが文字列の場合
                if isinstance(content, str):
                    display = content

                # contentがリストの場合
                elif isinstance(content, list):
                    # tool_resultを含むアイテムがあればスキップ
                    has_tool_result = any(
                        isinstance(item, dict) and item.get("type") == "tool_result"
                        for item in content
                    )
                    if has_tool_result:
                        continue

                    # textタイプのものを探す
                    text_parts = []
                    for item in content:
                        if isinstance(item, dict) and item.get("type") == "text":
                            text_parts.append(item.get("text", ""))
                        elif isinstance(item, str):
                            text_parts.append(item)
                    display = " ".join(text_parts)

                # displayフィールドも確認
                if not display:
                    display = message.get("display")

            elif isinstance(message, str):
                display = message

            # displayがまだリストの場合は文字列に変換
            if isinstance(display, list):
                display = " ".join(str(item) for item in display if item)

            # displayが文字列でない場合は文字列化
            if display and not isinstance(display, str):
                display = str(display)

            # 空でない場合のみ追加
            if display and isinstance(display, str) and display.strip():
                user_prompts.append({
                    "timestamp": session.get("timestamp"),
                    "prompt": display.strip()[:500],  # 最初の500文字
                    "session_id": session.get("sessionId"),
                    "project_path": session.get("cwd")
                })

            if len(user_prompts) >= limit:
                break

    return {"prompts": user_prompts}


PROMPT_TOKEN_SORT_KEYS = {
    "total_tokens",
    "output_tokens",
    "cache_read_tokens",
    "timestamp",
    "tool_use_count",
    "assistant_messages",
    "duration_seconds",
}


@router.get("/prompt-tokens", response_model=PromptTokenAnalysis)
async def get_prompt_token_analysis(
    days: int = Query(7, description="Number of days to analyze"),
    sort: str = Query("total_tokens", description="Sort key"),
    order: str = Query("desc", description="Sort order: asc or desc"),
    limit: int = Query(50, ge=1, le=200, description="Page size"),
    offset: int = Query(0, ge=0, description="Page offset"),
    include_commands: bool = Query(True, description="Include slash-command turns"),
    collector: ClaudeDataCollector = Depends(get_collector)
):
    """プロンプト単位のトークン帰属データを網羅的に取得（LLM不使用・高速）

    取得済みの履歴を時系列で推定帰属する。網羅性や正確性は保証しない。
    """
    if sort not in PROMPT_TOKEN_SORT_KEYS:
        raise HTTPException(status_code=400, detail=f"Invalid sort key: {sort}")

    data = collector.get_prompt_turns(days)
    turns = data["turns"]

    if not include_commands:
        turns = [t for t in turns if not t["is_command"]]

    turns = sorted(turns, key=lambda t: t[sort], reverse=(order != "asc"))
    total_count = len(turns)
    page = turns[offset:offset + limit]

    return PromptTokenAnalysis(
        period_days=days,
        summary=data["summary"],
        total_count=total_count,
        offset=offset,
        limit=limit,
        turns=page,
    )


@router.get("/cache-advice")
async def get_cache_advice(days: int = Query(7, ge=1, le=90), collector: ClaudeDataCollector = Depends(get_collector)):
    """Cache observations from local deduplicated usage, without sending content externally."""
    return build_cache_advice(collector.db, days)


@router.get("/prompt-tokens/insights/preview")
async def preview_insights(days: int = Query(7, ge=1, le=365), top: int = Query(15, ge=3, le=30), collector: ClaudeDataCollector = Depends(get_collector)):
    data = collector.get_prompt_turns(days)
    config = load_settings(collector.db)
    eligible = [t for t in data["turns"] if not excluded(t.get("project_path"), config["excluded_projects"])]
    turns = sorted(eligible, key=lambda t: t["total_tokens"], reverse=True)[:top]
    if not turns:
        raise HTTPException(status_code=404, detail="No prompts found in the specified period")
    # Return exactly the fields sent to the external model, including truncated text.
    fields = ("prompt", "total_tokens", "output_tokens", "cache_read_tokens", "tool_use_count", "duration_seconds")
    selected = [{k: t[k][:300] if k == "prompt" else t[k] for k in fields} for t in turns]
    # Excluded projects and unattributed usage are not forwarded in aggregates.
    unknown = {k: 0 for k in ("input_tokens", "output_tokens", "cache_creation_tokens", "cache_read_tokens", "assistant_messages")}
    summary = {k: v for k, v in summarize_turns(eligible, unknown).items() if k not in ("top_prompts", "attribution_coverage_pct")}
    return redact({"period_days": days, "summary": summary, "turns": selected}, config['redact_literals'])


@router.post("/prompt-tokens/insights", response_model=PromptTokenInsights)
async def get_prompt_token_insights(request: InsightsRequest, analyzer: ClaudeAnalyzer = Depends(get_analyzer), collector: ClaudeDataCollector = Depends(get_collector)):
    require_consent(request.consent)
    return analysis_response(PromptTokenInsights, lambda: analyzer.analyze_prompt_token_patterns(redact(request.summary, load_settings(collector.db)['redact_literals']), redact(request.turns, load_settings(collector.db)['redact_literals']), request.period_days))
