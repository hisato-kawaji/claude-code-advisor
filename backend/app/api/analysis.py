from fastapi import APIRouter, Depends, Query, HTTPException
from datetime import datetime, timedelta
from app.models.schemas import (
    PerformanceAnalysis,
    BestPracticesCheck,
    PromptImprovement,
    TokenReflection
)
from app.services.data_collector import ClaudeDataCollector
from app.services.analyzer import ClaudeAnalyzer
from app.config import get_settings, Settings

router = APIRouter(prefix="/api/analysis", tags=["analysis"])


def get_collector(settings: Settings = Depends(get_settings)) -> ClaudeDataCollector:
    return ClaudeDataCollector(settings.claude_data_path)


def get_analyzer(settings: Settings = Depends(get_settings)) -> ClaudeAnalyzer:
    settings.validate_openai_config()
    return ClaudeAnalyzer(settings.openai_api_key, settings.openai_model)


@router.get("/performance", response_model=PerformanceAnalysis)
async def analyze_performance(
    days: int = Query(7, description="Number of days to analyze"),
    collector: ClaudeDataCollector = Depends(get_collector),
    analyzer: ClaudeAnalyzer = Depends(get_analyzer)
):
    """パフォーマンスを分析してフィードバックを提供"""
    from datetime import timezone
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days)

    # 期間内のセッションを取得
    all_sessions = collector.get_all_sessions()

    # 期間でフィルタ
    filtered_sessions = []
    for session in all_sessions:
        timestamp = session.get("timestamp")
        if not timestamp:
            continue
        try:
            session_date = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            if start_date <= session_date <= end_date:
                filtered_sessions.append(session)
        except:
            continue

    if not filtered_sessions:
        raise HTTPException(status_code=404, detail="No sessions found in the specified period")

    # LLMで分析
    analysis = analyzer.analyze_performance(filtered_sessions)

    return PerformanceAnalysis(**analysis)


@router.get("/best-practices", response_model=BestPracticesCheck)
async def check_best_practices(
    days: int = Query(7, description="Number of days to analyze"),
    collector: ClaudeDataCollector = Depends(get_collector),
    analyzer: ClaudeAnalyzer = Depends(get_analyzer)
):
    """ベストプラクティスに沿っているかチェック"""
    from datetime import timezone
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days)

    # 期間内のセッションを取得
    all_sessions = collector.get_all_sessions()

    # 期間でフィルタ
    filtered_sessions = []
    for session in all_sessions:
        timestamp = session.get("timestamp")
        if not timestamp:
            continue
        try:
            session_date = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            if start_date <= session_date <= end_date:
                filtered_sessions.append(session)
        except:
            continue

    if not filtered_sessions:
        raise HTTPException(status_code=404, detail="No sessions found in the specified period")

    # LLMでチェック
    result = analyzer.check_best_practices(filtered_sessions)

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


@router.get("/token-reflection", response_model=TokenReflection)
async def analyze_token_consumption(
    days: int = Query(7, description="Number of days to analyze"),
    collector: ClaudeDataCollector = Depends(get_collector),
    analyzer: ClaudeAnalyzer = Depends(get_analyzer)
):
    """トークン消費量を分析して振り返りを提供"""
    from datetime import timezone
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days)

    # 期間内のセッションを取得
    all_sessions = collector.get_all_sessions()

    # 期間でフィルタ
    filtered_sessions = []
    for session in all_sessions:
        timestamp = session.get("timestamp")
        if not timestamp:
            continue
        try:
            session_date = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            if start_date <= session_date <= end_date:
                filtered_sessions.append(session)
        except:
            continue

    # セッションがない場合はダミーデータを返す
    if not filtered_sessions:
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
    result = analyzer.analyze_token_consumption(filtered_sessions, days)

    return TokenReflection(**result)
