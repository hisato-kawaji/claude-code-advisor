import json
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from collections import defaultdict
from functools import lru_cache
import hashlib
from .db_manager import DatabaseManager


class ClaudeDataCollector:
    def __init__(self, claude_data_path: str, db_path: str = None):
        self.claude_path = Path(os.path.expanduser(claude_data_path))
        self.history_file = self.claude_path / "history.jsonl"
        self.projects_dir = self.claude_path / "projects"
        self._cache_key = None

        # データベースマネージャーの初期化
        if db_path is None:
            db_path = str(self.claude_path.parent / "data" / "analytics.db")
        self.db = DatabaseManager(db_path)
        self._use_db = True  # DBを使用するかどうかのフラグ

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

    def _session_files(self):
        if not self.projects_dir.exists():
            return []
        # Parent transcripts and Claude Code's session/subagents/*.jsonl.
        return sorted(p for p in self.projects_dir.rglob("*.jsonl")
                      if p.is_file() and not p.is_symlink())

    def get_all_sessions(self) -> List[Dict]:
        result = []
        for path in self._session_files():
            for entry in self.read_jsonl(path):
                if isinstance(entry, dict):
                    entry["_analytics_source"] = {
                        "path": str(path.relative_to(self.projects_dir)),
                        "kind": "subagent" if "subagents" in path.parts else "session",
                    }
                    result.append(entry)
        return result

    def get_usage_stats(self, start_date: datetime, end_date: datetime) -> Dict:
        """指定期間の使用統計を取得（DB最適化版）"""
        if self._use_db:
            # DBから直接集計（高速）
            start_str = start_date.date().isoformat()
            end_str = end_date.date().isoformat()
            return self.db.get_analysis_stats(start_str, end_str)

        # フォールバック：ファイルから取得
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
        """日次統計を取得（DB使用時は高速）"""
        if self._use_db:
            # DBから直接取得（高速）
            date_str = date.date().isoformat()
            return self.db.get_daily_stats(date_str)
        else:
            # 従来の方法（JSONL読み込み）
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
        end = start + timedelta(days=6)
        return self.get_usage_stats(start, end)

    def get_monthly_stats(self, date: datetime) -> Dict:
        """月次統計を取得"""
        from datetime import timezone
        start = date.replace(day=1, hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
        if date.month == 12:
            end = start.replace(year=date.year + 1, month=1)
        else:
            end = start.replace(month=date.month + 1)
        return self.get_usage_stats(start, end - timedelta(days=1))

    def get_hourly_stats(self, date: datetime) -> List[Dict]:
        """1時間ごとの統計を取得（DB使用）"""
        if self._use_db:
            date_str = date.date().isoformat()
            return self.db.get_hourly_stats(date_str)
        
        # DBを使用しない場合のフォールバック
        # 24時間分の空のデータを返す
        return [{"hour": i, "input_tokens": 0, "output_tokens": 0} for i in range(24)]

    def get_recent_sessions(self, limit: int = 10) -> List[Dict]:
        """最近のセッションを取得（DB最適化版）"""
        if self._use_db:
            # DBから直接取得（高速）
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT message_json FROM session_entries
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (limit,))

                return [json.loads(row["message_json"]) for row in cursor.fetchall()]

        # フォールバック：ファイルから取得
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

    def get_daily_history_optimized(self, days: int = 30) -> List[Dict]:
        """最適化された日次履歴取得（DB使用時はさらに高速）"""
        if self._use_db:
            # DBから直接取得（最速）
            return self.db.get_daily_history(days)

        # 従来の最適化版（1回のファイル読み込みで全日分処理）
        from datetime import timezone

        # 全セッションを1回だけ読み込み
        all_sessions = self.get_all_sessions()

        # 日付ごとにデータをグループ化
        daily_data = defaultdict(lambda: {
            "sessions": set(),
            "total_messages": 0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "cache_creation_tokens": 0,
            "cache_read_tokens": 0,
            "user_messages": 0,
            "assistant_messages": 0,
        })

        for entry in all_sessions:
            timestamp = entry.get("timestamp")
            if not timestamp:
                continue

            try:
                entry_date = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            except:
                continue

            # 日付をキーとして使用
            date_key = entry_date.date()

            # セッションIDを記録
            session_id = entry.get("sessionId")
            if session_id:
                daily_data[date_key]["sessions"].add(session_id)

            # メッセージタイプをカウント
            entry_type = entry.get("type")
            if entry_type == "user":
                daily_data[date_key]["user_messages"] += 1
                daily_data[date_key]["total_messages"] += 1
            elif entry_type == "assistant":
                daily_data[date_key]["assistant_messages"] += 1
                daily_data[date_key]["total_messages"] += 1

                # トークン使用量を集計
                message = entry.get("message", {})
                usage = message.get("usage", {})

                daily_data[date_key]["total_input_tokens"] += usage.get("input_tokens", 0)
                daily_data[date_key]["total_output_tokens"] += usage.get("output_tokens", 0)
                daily_data[date_key]["cache_creation_tokens"] += usage.get("cache_creation_input_tokens", 0)
                daily_data[date_key]["cache_read_tokens"] += usage.get("cache_read_input_tokens", 0)

        # 過去N日分の結果を生成
        history = []
        current_date = datetime.now().date()

        for i in range(days):
            date = current_date - timedelta(days=i)
            data = daily_data.get(date, {
                "sessions": set(),
                "total_messages": 0,
                "total_input_tokens": 0,
                "total_output_tokens": 0,
                "cache_creation_tokens": 0,
                "cache_read_tokens": 0,
                "user_messages": 0,
                "assistant_messages": 0,
            })

            # setをカウントに変換
            result = {
                "date": date.strftime("%Y-%m-%d"),
                "total_sessions": len(data["sessions"]),
                "total_messages": data["total_messages"],
                "total_input_tokens": data["total_input_tokens"],
                "total_output_tokens": data["total_output_tokens"],
                "cache_creation_tokens": data["cache_creation_tokens"],
                "cache_read_tokens": data["cache_read_tokens"],
                "user_messages": data["user_messages"],
                "assistant_messages": data["assistant_messages"],
            }
            history.append(result)

        return list(reversed(history))

    def get_weekly_history_optimized(self, weeks: int = 26) -> List[Dict]:
        """Use the same deduplicated database as the weekly summary (UTC)."""
        from datetime import timezone
        today = datetime.now(timezone.utc).date()
        start = today - timedelta(days=today.weekday())
        history = []
        for index in reversed(range(weeks)):
            first = start - timedelta(weeks=index)
            last = first + timedelta(days=6)
            history.append({"date": first.isoformat(), **self.db.get_analysis_stats(first.isoformat(), last.isoformat())})
        return history

    def get_monthly_history_optimized(self, months: int = 12) -> List[Dict]:
        """Use the same deduplicated database as the monthly summary (UTC)."""
        from datetime import timezone
        current = datetime.now(timezone.utc).date().replace(day=1)
        history = []
        for _ in range(months):
            following = (current.replace(day=28) + timedelta(days=4)).replace(day=1)
            last = following - timedelta(days=1)
            history.append({"date": current.isoformat(), **self.db.get_analysis_stats(current.isoformat(), last.isoformat())})
            current = (current - timedelta(days=1)).replace(day=1)
        return list(reversed(history))

    def sync_to_database(self) -> Dict[str, int]:
        """JSONLファイルからDBへデータを同期（重複排除）"""
        files = self._session_files()
        entries = []
        malformed = 0
        for path in files:
            try:
                with path.open(encoding="utf-8") as source:
                    for line_number, line in enumerate(source, 1):
                        try:
                            entry = json.loads(line)
                            if not isinstance(entry, dict):
                                raise ValueError("Not an object")
                            entry["_analytics_source"] = {
                                "path": str(path.relative_to(self.projects_dir)),
                                "line": line_number,
                                "kind": "subagent" if "subagents" in path.parts else "session",
                            }
                            entries.append(entry)
                        except (json.JSONDecodeError, ValueError):
                            malformed += 1
            except (OSError, UnicodeError):
                malformed += 1
        inserted, skipped, invalid = self.db.bulk_insert_entries(entries)
        self.db.record_sync(len(files), inserted)
        return {"inserted": inserted, "skipped": skipped, "invalid": invalid,
                "malformed": malformed, "files_processed": len(files),
                "subagent_files": sum("subagents" in p.parts for p in files),
                "total_entries": self.db.get_total_entries_count()}

    def get_prompt_turns(self, days: int = 7) -> Dict:
        """プロンプト単位のトークン帰属分析データを取得（DB使用）

        各プロンプト（ターン起点）に、次のプロンプトまでのassistant消費を
        合算して帰属させる。帰属できなかった消費はサマリーのunattributedに
        計上され、attribution_coverage_pctで正確性を検証できる。
        """
        from datetime import date as date_cls
        from .prompt_turns import build_turns, summarize_turns

        end_date = date_cls.today()
        start_date = end_date - timedelta(days=days)

        rows = self.db.get_entries_for_prompt_analysis(
            start_date.isoformat(), end_date.isoformat()
        )
        from .settings_store import load_settings
        turns, unattributed = build_turns(rows, load_settings(self.db))
        summary = summarize_turns(turns, unattributed)

        return {"turns": turns, "summary": summary}

    def get_analysis_data_optimized(self, days: int = 7) -> Dict:
        """analyzer用の統計データを高速取得（DB使用）"""
        if self._use_db:
            from datetime import date, timedelta

            end_date = date.today()
            start_date = end_date - timedelta(days=days)

            # DBから統計とサンプルメッセージを取得
            stats = self.db.get_analysis_stats(start_date.isoformat(), end_date.isoformat())
            sample_messages = self.db.get_sample_user_messages(start_date.isoformat(), end_date.isoformat(), limit=10)

            return {
                "stats": stats,
                "sample_messages": sample_messages
            }
        else:
            # 従来の方法（フォールバック）
            from datetime import timezone
            current_date = datetime.now()
            start_date = current_date - timedelta(days=days)
            start = start_date.replace(tzinfo=timezone.utc)
            end = current_date.replace(tzinfo=timezone.utc)

            sessions = []
            for entry in self.get_all_sessions():
                timestamp = entry.get("timestamp")
                if timestamp:
                    try:
                        entry_date = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        if start <= entry_date <= end:
                            sessions.append(entry)
                    except:
                        continue

            # 統計計算
            user_messages = [s for s in sessions if s.get("type") == "user"]
            assistant_messages = [s for s in sessions if s.get("type") == "assistant"]

            total_input = sum(s.get("message", {}).get("usage", {}).get("input_tokens", 0) for s in assistant_messages)
            total_output = sum(s.get("message", {}).get("usage", {}).get("output_tokens", 0) for s in assistant_messages)
            cache_creation = sum(s.get("message", {}).get("usage", {}).get("cache_creation_input_tokens", 0) for s in assistant_messages)
            cache_read = sum(s.get("message", {}).get("usage", {}).get("cache_read_input_tokens", 0) for s in assistant_messages)

            sample_messages = []
            for msg in user_messages[:10]:
                content = msg.get("message", {}).get("content", "")
                if isinstance(content, str):
                    sample_messages.append(content[:300])

            return {
                "stats": {
                    "total_sessions": len(set(s.get("sessionId") for s in sessions if s.get("sessionId"))),
                    "total_messages": len(sessions),
                    "user_messages": len(user_messages),
                    "assistant_messages": len(assistant_messages),
                    "total_input_tokens": total_input,
                    "total_output_tokens": total_output,
                    "cache_creation_tokens": cache_creation,
                    "cache_read_tokens": cache_read,
                },
                "sample_messages": sample_messages
            }
