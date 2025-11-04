import json
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from collections import defaultdict


class ClaudeDataCollector:
    def __init__(self, claude_data_path: str):
        self.claude_path = Path(os.path.expanduser(claude_data_path))
        self.history_file = self.claude_path / "history.jsonl"
        self.projects_dir = self.claude_path / "projects"

    def read_jsonl(self, file_path: Path) -> List[Dict]:
        """JSONLファイルを読み込む"""
        data = []
        if not file_path.exists():
            return data

        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    data.append(json.loads(line.strip()))
                except json.JSONDecodeError:
                    continue
        return data

    def get_all_sessions(self) -> List[Dict]:
        """全てのセッションデータを取得"""
        all_sessions = []

        if not self.projects_dir.exists():
            return all_sessions

        for project_dir in self.projects_dir.iterdir():
            if not project_dir.is_dir():
                continue

            for session_file in project_dir.glob("*.jsonl"):
                session_data = self.read_jsonl(session_file)
                all_sessions.extend(session_data)

        return all_sessions

    def get_usage_stats(self, start_date: datetime, end_date: datetime) -> Dict:
        """指定期間の使用統計を取得"""
        sessions = self.get_all_sessions()

        stats = {
            "total_sessions": set(),
            "total_messages": 0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "cache_creation_tokens": 0,
            "cache_read_tokens": 0,
            "user_messages": 0,
            "assistant_messages": 0,
        }

        for entry in sessions:
            # タイムスタンプを解析
            timestamp = entry.get("timestamp")
            if not timestamp:
                continue

            try:
                entry_date = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            except:
                continue

            # 期間内かチェック
            if not (start_date <= entry_date <= end_date):
                continue

            # セッションIDを記録
            session_id = entry.get("sessionId")
            if session_id:
                stats["total_sessions"].add(session_id)

            # メッセージタイプをカウント
            entry_type = entry.get("type")
            if entry_type == "user":
                stats["user_messages"] += 1
                stats["total_messages"] += 1
            elif entry_type == "assistant":
                stats["assistant_messages"] += 1
                stats["total_messages"] += 1

                # トークン使用量を集計
                message = entry.get("message", {})
                usage = message.get("usage", {})

                stats["total_input_tokens"] += usage.get("input_tokens", 0)
                stats["total_output_tokens"] += usage.get("output_tokens", 0)
                stats["cache_creation_tokens"] += usage.get("cache_creation_input_tokens", 0)
                stats["cache_read_tokens"] += usage.get("cache_read_input_tokens", 0)

        stats["total_sessions"] = len(stats["total_sessions"])
        return stats

    def get_daily_stats(self, date: datetime) -> Dict:
        """日次統計を取得"""
        start = date.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)
        end = start + timedelta(days=1)
        # Make start and end timezone-aware (UTC)
        from datetime import timezone
        start = start.replace(tzinfo=timezone.utc)
        end = end.replace(tzinfo=timezone.utc)
        return self.get_usage_stats(start, end)

    def get_weekly_stats(self, date: datetime) -> Dict:
        """週次統計を取得（指定日を含む週）"""
        from datetime import timezone
        start = date - timedelta(days=date.weekday())
        start = start.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
        end = start + timedelta(days=7)
        return self.get_usage_stats(start, end)

    def get_monthly_stats(self, date: datetime) -> Dict:
        """月次統計を取得"""
        from datetime import timezone
        start = date.replace(day=1, hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
        if date.month == 12:
            end = start.replace(year=date.year + 1, month=1)
        else:
            end = start.replace(month=date.month + 1)
        return self.get_usage_stats(start, end)

    def get_recent_sessions(self, limit: int = 10) -> List[Dict]:
        """最近のセッションを取得"""
        sessions = self.get_all_sessions()

        # タイムスタンプでソート
        sessions_with_time = []
        for entry in sessions:
            timestamp = entry.get("timestamp")
            if timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    sessions_with_time.append((dt, entry))
                except:
                    continue

        sessions_with_time.sort(key=lambda x: x[0], reverse=True)
        return [entry for _, entry in sessions_with_time[:limit]]

    def get_session_details(self, session_id: str) -> List[Dict]:
        """特定のセッションの詳細を取得"""
        all_sessions = self.get_all_sessions()
        return [entry for entry in all_sessions if entry.get("sessionId") == session_id]
