from fastapi import APIRouter, Depends, Query, HTTPException
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

router = APIRouter(prefix="/api/analysis", tags=["analysis"])


def get_collector(settings: Settings = Depends(get_settings)) -> ClaudeDataCollector:
    return ClaudeDataCollector(settings.claude_data_path, settings.database_path)


def get_analyzer(settings: Settings = Depends(get_settings)) -> ClaudeAnalyzer:
    settings.validate_openai_config()
    return ClaudeAnalyzer(settings.openai_api_key, settings.openai_model)


@router.get("/performance", response_model=PerformanceAnalysis)
async def analyze_performance(
    days: int = Query(7, description="Number of days to analyze"),
    collector: ClaudeDataCollector = Depends(get_collector),
    analyzer: ClaudeAnalyzer = Depends(get_analyzer)
):
    """パフォーマンスを分析してフィードバックを提供（DB最適化版）"""
    # DB最適化版：統計データとサンプルメッセージのみ取得
    data = collector.get_analysis_data_optimized(days)

    if data["stats"]["total_messages"] == 0:
        raise HTTPException(status_code=404, detail="No sessions found in the specified period")

    # LLMで分析
    analysis = analyzer.analyze_performance(data["stats"], data["sample_messages"])

    return PerformanceAnalysis(**analysis)


@router.get("/best-practices", response_model=BestPracticesCheck)
async def check_best_practices(
    days: int = Query(7, description="Number of days to analyze"),
    collector: ClaudeDataCollector = Depends(get_collector),
    analyzer: ClaudeAnalyzer = Depends(get_analyzer)
):
    """ベストプラクティスに沿っているかチェック（DB最適化版）"""
    # DB最適化版：サンプルメッセージのみ取得
    data = collector.get_analysis_data_optimized(days)

    if data["stats"]["total_messages"] == 0:
        raise HTTPException(status_code=404, detail="No sessions found in the specified period")

    # LLMでチェック
    result = analyzer.check_best_practices(data["sample_messages"])

    return BestPracticesCheck(**result)


@router.post("/improve-prompt", response_model=PromptImprovement)
async def improve_prompt(
    prompt: str = Query(..., description="The prompt to improve"),
    analyzer: ClaudeAnalyzer = Depends(get_analyzer)
):
    """プロンプトの改善提案を取得"""
    if not prompt or len(prompt.strip()) < 5:
        raise HTTPException(status_code=400, detail="Prompt is too short")

    result = analyzer.suggest_prompt_improvements(prompt)

    return PromptImprovement(**result)


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
                    "session_id": session.get("sessionId")
                })

            if len(user_prompts) >= limit:
                break

    return {"prompts": user_prompts}


PROMPT_TOKEN_SORT_KEYS = {
    "total_tokens",
    "output_tokens",
    "cache_read_tokens",
    "estimated_cost_usd",
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

    各プロンプトに、次のプロンプトまでのassistant消費（サブエージェント・
    ツール実行含む）を1対1で帰属させたターン一覧を返す。
    summary.attribution_coverage_pctで帰属の正確性を検証できる。
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


@router.get("/prompt-tokens/insights", response_model=PromptTokenInsights)
async def get_prompt_token_insights(
    days: int = Query(7, description="Number of days to analyze"),
    top: int = Query(15, ge=3, le=30, description="Number of top prompts to analyze"),
    collector: ClaudeDataCollector = Depends(get_collector),
    analyzer: ClaudeAnalyzer = Depends(get_analyzer)
):
    """消費上位プロンプトをLLMで分析し、高消費パターンと改善示唆を返す"""
    data = collector.get_prompt_turns(days)
    turns = data["turns"]

    if not turns:
        raise HTTPException(status_code=404, detail="No prompts found in the specified period")

    top_turns = sorted(turns, key=lambda t: t["total_tokens"], reverse=True)[:top]

    result = analyzer.analyze_prompt_token_patterns(data["summary"], top_turns, days)

    return PromptTokenInsights(**result)


@router.get("/token-reflection", response_model=TokenReflection)
async def analyze_token_consumption(
    days: int = Query(7, description="Number of days to analyze"),
    collector: ClaudeDataCollector = Depends(get_collector),
    analyzer: ClaudeAnalyzer = Depends(get_analyzer)
):
    """トークン消費量を分析して振り返りを提供（DB最適化版）"""
    # DB最適化版：統計データとサンプルメッセージのみ取得
    data = collector.get_analysis_data_optimized(days)

    # セッションがない場合はダミーデータを返す
    if data["stats"]["total_messages"] == 0:
        return TokenReflection(
            period_days=days,
            summary={
                "total_input_tokens": 0,
                "total_output_tokens": 0,
                "total_tokens": 0,
                "cache_creation_tokens": 0,
                "cache_read_tokens": 0,
                "estimated_cost_usd": 0.0,
                "avg_tokens_per_session": 0.0,
                "avg_tokens_per_day": 0.0,
                "input_output_ratio": 0.0
            },
            analysis={
                "efficiency_score": 0.0,
                "token_usage_pattern": "データがありません",
                "most_token_intensive_activities": [],
                "cost_optimization_suggestions": ["Claude Codeを使用してデータを生成してください"],
                "next_steps": ["Claude Codeでタスクを実行してトークン使用データを蓄積しましょう"]
            },
            reflection=f"過去{days}日間のトークン使用データが見つかりませんでした。Claude Codeを使用してタスクを実行すると、ここに詳細な振り返りが表示されます。"
        )

    # LLMでトークン消費を分析
    result = analyzer.analyze_token_consumption(data["stats"], data["sample_messages"], days)

    return TokenReflection(**result)
