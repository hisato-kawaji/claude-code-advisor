from fastapi import APIRouter, Depends, Query
from datetime import datetime, timedelta, timezone
from typing import List
from app.models.schemas import UsageStats, ComparisonStats, HourlyUsage
from app.services.data_collector import ClaudeDataCollector
from app.config import get_settings, Settings

router = APIRouter(prefix="/api/stats", tags=["statistics"])


def get_collector(settings: Settings = Depends(get_settings)) -> ClaudeDataCollector:
    return ClaudeDataCollector(settings.claude_data_path, settings.database_path)


def calculate_change_percentage(current: dict, previous: dict) -> dict:
    """前回との変化率を計算"""
    changes = {}
    for key in current:
        if key == "date":
            continue
        curr_val = current[key]
        prev_val = previous.get(key, 0)

        if prev_val == 0:
            changes[key] = 100.0 if curr_val > 0 else 0.0
        else:
            changes[key] = ((curr_val - prev_val) / prev_val) * 100

    return changes


@router.get("/daily", response_model=ComparisonStats)
async def get_daily_stats(
    date: str = Query(None, description="Date in YYYY-MM-DD format"),
    collector: ClaudeDataCollector = Depends(get_collector)
):
    """日次統計と前日比を取得"""
    if date:
        current_date = datetime.fromisoformat(date)
    else:
        current_date = datetime.now(timezone.utc)

    current_stats = collector.get_daily_stats(current_date)
    previous_date = current_date - timedelta(days=1)
    previous_stats = collector.get_daily_stats(previous_date)

    current_stats["date"] = current_date.strftime("%Y-%m-%d")
    previous_stats["date"] = previous_date.strftime("%Y-%m-%d")

    return ComparisonStats(
        current=UsageStats(**current_stats),
        previous=UsageStats(**previous_stats),
        change_percentage=calculate_change_percentage(current_stats, previous_stats)
    )


@router.get("/weekly", response_model=ComparisonStats)
async def get_weekly_stats(
    date: str = Query(None, description="Date in YYYY-MM-DD format"),
    collector: ClaudeDataCollector = Depends(get_collector)
):
    """週次統計と先週比を取得"""
    if date:
        current_date = datetime.fromisoformat(date)
    else:
        current_date = datetime.now(timezone.utc)

    current_stats = collector.get_weekly_stats(current_date)
    previous_date = current_date - timedelta(weeks=1)
    previous_stats = collector.get_weekly_stats(previous_date)

    week_start = current_date - timedelta(days=current_date.weekday())
    current_stats["date"] = week_start.strftime("%Y-%m-%d")
    prev_week_start = previous_date - timedelta(days=previous_date.weekday())
    previous_stats["date"] = prev_week_start.strftime("%Y-%m-%d")

    return ComparisonStats(
        current=UsageStats(**current_stats),
        previous=UsageStats(**previous_stats),
        change_percentage=calculate_change_percentage(current_stats, previous_stats)
    )


@router.get("/monthly", response_model=ComparisonStats)
async def get_monthly_stats(
    date: str = Query(None, description="Date in YYYY-MM-DD format"),
    collector: ClaudeDataCollector = Depends(get_collector)
):
    """月次統計と先月比を取得"""
    if date:
        current_date = datetime.fromisoformat(date)
    else:
        current_date = datetime.now(timezone.utc)

    current_stats = collector.get_monthly_stats(current_date)
    # 月末の日付が前月に存在しない場合も、前月を正しく特定する。
    previous_date = current_date.replace(day=1) - timedelta(days=1)

    previous_stats = collector.get_monthly_stats(previous_date)

    month_start = current_date.replace(day=1)
    current_stats["date"] = month_start.strftime("%Y-%m-%d")
    prev_month_start = previous_date.replace(day=1)
    previous_stats["date"] = prev_month_start.strftime("%Y-%m-%d")

    return ComparisonStats(
        current=UsageStats(**current_stats),
        previous=UsageStats(**previous_stats),
        change_percentage=calculate_change_percentage(current_stats, previous_stats)
    )


@router.get("/hourly", response_model=List[HourlyUsage])
async def get_hourly_stats(
    date: str = Query(..., description="Date in YYYY-MM-DD format"),
    collector: ClaudeDataCollector = Depends(get_collector)
):
    """指定日の1時間ごとの統計を取得"""
    target_date = datetime.fromisoformat(date)
    hourly_data = collector.get_hourly_stats(target_date)
    return hourly_data


@router.get("/range")
async def get_range_stats(
    start_date: str = Query(..., description="Start date in YYYY-MM-DD format"),
    end_date: str = Query(..., description="End date in YYYY-MM-DD format"),
    collector: ClaudeDataCollector = Depends(get_collector)
):
    """指定期間の統計を取得"""
    start = datetime.fromisoformat(start_date)
    end = datetime.fromisoformat(end_date)

    stats = collector.get_usage_stats(start, end)
    stats["date"] = f"{start_date} to {end_date}"

    return UsageStats(**stats)


@router.get("/history/daily")
async def get_daily_history(
    days: int = Query(30, description="Number of days to retrieve"),
    collector: ClaudeDataCollector = Depends(get_collector)
):
    """過去N日分の日次統計を取得（最適化版）"""
    history = collector.get_daily_history_optimized(days)
    return {"history": history}


@router.get("/history/weekly")
async def get_weekly_history(
    weeks: int = Query(26, description="Number of weeks to retrieve (default: 26 weeks = ~6 months)"),
    collector: ClaudeDataCollector = Depends(get_collector)
):
    """過去N週分の週次統計を取得（最適化版）"""
    history = collector.get_weekly_history_optimized(weeks)
    return {"history": history}


@router.get("/history/monthly")
async def get_monthly_history(
    months: int = Query(12, description="Number of months to retrieve"),
    collector: ClaudeDataCollector = Depends(get_collector)
):
    """過去N月分の月次統計を取得（最適化版）"""
    history = collector.get_monthly_history_optimized(months)
    return {"history": history}

@router.post("/sync")
async def sync_database(
    collector: ClaudeDataCollector = Depends(get_collector)
):
    """データベースを最新のJSONLファイルと同期"""
    result = collector.sync_to_database()
    return {
        "status": "success",
        "inserted": result["inserted"],
        "skipped": result["skipped"],
        "invalid": result["invalid"],
        "malformed": result["malformed"],
        "files_processed": result["files_processed"],
        "subagent_files": result["subagent_files"],
        "total_entries": result["total_entries"]
    }


@router.get("/sync-status")
async def get_sync_status(
    collector: ClaudeDataCollector = Depends(get_collector)
):
    """最終同期時刻・総エントリ数・取り込み済みデータの最新日付を取得"""
    return collector.db.get_sync_status()
