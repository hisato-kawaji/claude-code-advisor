import sqlite3
import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
from contextlib import contextmanager


class DatabaseManager:
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_database()

    @contextmanager
    def get_connection(self):
        """データベース接続のコンテキストマネージャー"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def init_database(self):
        """データベースとテーブルを初期化"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # セッションエントリテーブル
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS session_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    unique_key TEXT UNIQUE NOT NULL,
                    session_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    entry_type TEXT NOT NULL,
                    date TEXT NOT NULL,
                    message_json TEXT NOT NULL,
                    input_tokens INTEGER DEFAULT 0,
                    output_tokens INTEGER DEFAULT 0,
                    cache_creation_tokens INTEGER DEFAULT 0,
                    cache_read_tokens INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            columns = {row[1] for row in cursor.execute("PRAGMA table_info(session_entries)")}
            if "request_key" not in columns:
                cursor.execute("ALTER TABLE session_entries ADD COLUMN request_key TEXT")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_request_key ON session_entries(request_key)")

            # インデックスを作成（高速クエリのため）
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp
                ON session_entries(timestamp)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_session_id
                ON session_entries(session_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_date
                ON session_entries(date)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_entry_type
                ON session_entries(entry_type)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_date_type
                ON session_entries(date, entry_type)
            """)

            # 同期メタデータテーブル
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sync_metadata (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    last_sync TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    files_processed INTEGER DEFAULT 0,
                    entries_added INTEGER DEFAULT 0
                )
            """)

            conn.commit()

    def generate_unique_key(self, entry: Dict) -> str:
        """エントリからユニークキーを生成（重複チェック用）"""
        session_id = entry.get("sessionId", "")
        timestamp = entry.get("timestamp", "")
        entry_type = entry.get("type", "")

        # メッセージの一部も含めてより確実なユニーク性を保証
        message = entry.get("message", {})
        content_preview = ""
        if isinstance(message, dict):
            content = message.get("content", "")
            if isinstance(content, str):
                content_preview = content[:100]
            elif isinstance(content, list) and len(content) > 0:
                content_preview = str(content[0])[:100]

        unique_str = f"{session_id}|{timestamp}|{entry_type}|{content_preview}"
        return hashlib.sha256(unique_str.encode()).hexdigest()

    def bulk_insert_entries(self, entries: List[Dict]) -> tuple[int, int, int]:
        """Import stable UUIDs, retain legacy rows, and report malformed records separately."""
        inserted = skipped = invalid = 0
        request_keys = set()
        with self.get_connection() as conn:
            for entry in entries:
                try:
                    timestamp = entry.get("timestamp", "")
                    dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                    session_id = entry.get("sessionId")
                    entry_type = entry.get("type")
                    if not session_id or not entry_type:
                        raise ValueError("missing session/type")
                    message = entry.get("message") or {}
                    usage = message.get("usage") or {} if isinstance(message, dict) else {}
                    counts = [int(usage.get(k) or 0) for k in ("input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")]
                    if any(n < 0 for n in counts):
                        raise ValueError("negative usage")
                    request_key = str(entry.get("requestId") or "") if entry_type == "assistant" else ""
                    if request_key:
                        request_keys.add(request_key)
                    legacy_key = self.generate_unique_key(entry)
                    uuid = entry.get("uuid")
                    key = "uuid:" + str(uuid) if uuid else legacy_key
                    old = conn.execute("SELECT id, message_json FROM session_entries WHERE unique_key = ?", (legacy_key,)).fetchone()
                    if old and key != legacy_key:
                        previous = json.loads(old["message_json"])
                        if previous.get("uuid") == uuid:
                            # Preserve existing historical values while recording provenance.
                            conn.execute("UPDATE session_entries SET message_json = ?, request_key = ? WHERE id = ?", (json.dumps(entry), request_key or None, old["id"]))
                            skipped += 1
                            continue
                    cursor = conn.execute("""INSERT OR IGNORE INTO session_entries
                        (unique_key, session_id, timestamp, entry_type, date, message_json,
                         input_tokens, output_tokens, cache_creation_tokens, cache_read_tokens, request_key)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (key, session_id, timestamp, entry_type, dt.date().isoformat(),
                         json.dumps(entry), *counts, request_key or None))
                    if cursor.rowcount:
                        inserted += 1
                    else:
                        # Refresh provenance and the request identity without creating duplicates.
                        conn.execute("UPDATE session_entries SET message_json = ?, request_key = ? WHERE unique_key = ?",
                                     (json.dumps(entry), request_key or None, key))
                        skipped += 1
                except (ValueError, TypeError, AttributeError, json.JSONDecodeError):
                    invalid += 1
            for request_key in request_keys:
                rows = conn.execute("SELECT id, message_json FROM session_entries WHERE request_key = ? ORDER BY timestamp, id", (request_key,)).fetchall()
                if len(rows) < 2:
                    continue
                # Multiple transcript blocks can repeat the same API request usage.
                # Keep the final recorded usage once, retaining all message contents.
                usage_fields = ("input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")
                chosen = None
                for row in reversed(rows):
                    record = json.loads(row["message_json"])
                    usage = (record.get("message") or {}).get("usage") or {}
                    if any(k in usage for k in usage_fields):
                        chosen = (row["id"], [int(usage.get(k) or 0) for k in usage_fields])
                        break
                if chosen is None:
                    continue
                conn.execute("UPDATE session_entries SET input_tokens=0, output_tokens=0, cache_creation_tokens=0, cache_read_tokens=0 WHERE request_key = ?", (request_key,))
                conn.execute("UPDATE session_entries SET input_tokens=?, output_tokens=?, cache_creation_tokens=?, cache_read_tokens=? WHERE id=?", (*chosen[1], chosen[0]))
        return inserted, skipped, invalid

    def get_entries_by_date_range(self, start_date: str, end_date: str) -> List[Dict]:
        """日付範囲でエントリを取得"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT message_json FROM session_entries
                WHERE date >= ? AND date <= ?
                ORDER BY timestamp
            """, (start_date, end_date))

            return [json.loads(row["message_json"]) for row in cursor.fetchall()]

    def get_entries_for_prompt_analysis(self, start_date: str, end_date: str) -> List[Dict]:
        """プロンプト単位のターン分析用に、期間内のuser/assistantエントリを
        セッション・時系列順で取得する"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT session_id, timestamp, entry_type, message_json,
                       input_tokens, output_tokens,
                       cache_creation_tokens, cache_read_tokens
                FROM session_entries
                WHERE date >= ? AND date <= ?
                  AND entry_type IN ('user', 'assistant')
                ORDER BY session_id, timestamp, id
            """, (start_date, end_date))

            return [dict(row) for row in cursor.fetchall()]

    def get_daily_stats(self, date: str) -> Dict:
        """日次統計を高速取得"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # セッション数と基本統計
            cursor.execute("""
                SELECT
                    COUNT(DISTINCT session_id) as total_sessions,
                    COUNT(*) as total_messages,
                    SUM(CASE WHEN entry_type = 'user' THEN 1 ELSE 0 END) as user_messages,
                    SUM(CASE WHEN entry_type = 'assistant' THEN 1 ELSE 0 END) as assistant_messages,
                    SUM(input_tokens) as total_input_tokens,
                    SUM(output_tokens) as total_output_tokens,
                    SUM(cache_creation_tokens) as cache_creation_tokens,
                    SUM(cache_read_tokens) as cache_read_tokens
                FROM session_entries
                WHERE date = ?
            """, (date,))

            row = cursor.fetchone()

            return {
                "date": date,
                "total_sessions": row["total_sessions"] or 0,
                "total_messages": row["total_messages"] or 0,
                "user_messages": row["user_messages"] or 0,
                "assistant_messages": row["assistant_messages"] or 0,
                "total_input_tokens": row["total_input_tokens"] or 0,
                "total_output_tokens": row["total_output_tokens"] or 0,
                "cache_creation_tokens": row["cache_creation_tokens"] or 0,
                "cache_read_tokens": row["cache_read_tokens"] or 0,
            }

    def get_total_entries_count(self) -> int:
        """総エントリ数を取得"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM session_entries")
            return cursor.fetchone()["count"]

    def get_sync_status(self) -> Dict:
        """最終同期時刻・総エントリ数・取り込み済みデータの最新日付を取得"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT last_sync FROM sync_metadata
                ORDER BY id DESC LIMIT 1
            """)
            row = cursor.fetchone()
            last_sync = row["last_sync"] if row else None

            cursor.execute("SELECT COUNT(*) as count, MAX(date) as latest_date FROM session_entries")
            row = cursor.fetchone()

            return {
                "last_sync": last_sync,
                "total_entries": row["count"] or 0,
                "latest_data_date": row["latest_date"],
            }

    def record_sync(self, files_processed: int, entries_added: int):
        """同期メタデータを記録"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO sync_metadata (files_processed, entries_added)
                VALUES (?, ?)
            """, (files_processed, entries_added))

    def get_daily_history(self, days: int = 30) -> List[Dict]:
        """日次履歴を高速取得（最適化版）"""
        from datetime import date, timedelta

        current_date = date.today()
        history = []

        with self.get_connection() as conn:
            cursor = conn.cursor()

            for i in range(days):
                target_date = (current_date - timedelta(days=i)).isoformat()

                cursor.execute("""
                    SELECT
                        COUNT(DISTINCT session_id) as total_sessions,
                        COUNT(*) as total_messages,
                        SUM(CASE WHEN entry_type = 'user' THEN 1 ELSE 0 END) as user_messages,
                        SUM(CASE WHEN entry_type = 'assistant' THEN 1 ELSE 0 END) as assistant_messages,
                        SUM(input_tokens) as total_input_tokens,
                        SUM(output_tokens) as total_output_tokens,
                        SUM(cache_creation_tokens) as cache_creation_tokens,
                        SUM(cache_read_tokens) as cache_read_tokens
                    FROM session_entries
                    WHERE date = ?
                """, (target_date,))

                row = cursor.fetchone()

                history.append({
                    "date": target_date,
                    "total_sessions": row["total_sessions"] or 0,
                    "total_messages": row["total_messages"] or 0,
                    "user_messages": row["user_messages"] or 0,
                    "assistant_messages": row["assistant_messages"] or 0,
                    "total_input_tokens": row["total_input_tokens"] or 0,
                    "total_output_tokens": row["total_output_tokens"] or 0,
                    "cache_creation_tokens": row["cache_creation_tokens"] or 0,
                    "cache_read_tokens": row["cache_read_tokens"] or 0,
                })

        return list(reversed(history))

    def get_analysis_stats(self, start_date: str, end_date: str) -> Dict:
        """分析用の統計データを高速取得"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # 基本統計
            cursor.execute("""
                SELECT
                    COUNT(DISTINCT session_id) as total_sessions,
                    COUNT(*) as total_messages,
                    SUM(CASE WHEN entry_type = 'user' THEN 1 ELSE 0 END) as user_messages,
                    SUM(CASE WHEN entry_type = 'assistant' THEN 1 ELSE 0 END) as assistant_messages,
                    SUM(input_tokens) as total_input_tokens,
                    SUM(output_tokens) as total_output_tokens,
                    SUM(cache_creation_tokens) as cache_creation_tokens,
                    SUM(cache_read_tokens) as cache_read_tokens
                FROM session_entries
                WHERE date >= ? AND date <= ?
            """, (start_date, end_date))

            row = cursor.fetchone()

            return {
                "total_sessions": row["total_sessions"] or 0,
                "total_messages": row["total_messages"] or 0,
                "user_messages": row["user_messages"] or 0,
                "assistant_messages": row["assistant_messages"] or 0,
                "total_input_tokens": row["total_input_tokens"] or 0,
                "total_output_tokens": row["total_output_tokens"] or 0,
                "cache_creation_tokens": row["cache_creation_tokens"] or 0,
                "cache_read_tokens": row["cache_read_tokens"] or 0,
            }

    def get_sample_user_messages(self, start_date: str, end_date: str, limit: int = 10) -> List[str]:
        """サンプルユーザーメッセージを取得"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT message_json FROM session_entries
                WHERE date >= ? AND date <= ? AND entry_type = 'user'
                ORDER BY timestamp DESC
                LIMIT ?
            """, (start_date, end_date, limit))

            messages = []
            for row in cursor.fetchall():
                entry = json.loads(row["message_json"])
                message = entry.get("message", {})
                content = message.get("content", "")

                # 文字列の場合
                if isinstance(content, str) and len(content.strip()) > 10:
                    messages.append(content[:300])
                # リストの場合
                elif isinstance(content, list):
                    for item in content:
                        if isinstance(item, dict) and item.get("type") == "text":
                            text = item.get("text", "")
                            if len(text.strip()) > 10:
                                messages.append(text[:300])
                                break

            return messages

    def get_hourly_stats(self, date: str) -> List[Dict]:
        """指定された日付の1時間ごとの統計を取得（JST対応）"""
        # 0時から23時までの全時間帯のデフォルト値を作成
        hourly_results = {
            i: {"hour": i, "input_tokens": 0, "output_tokens": 0, "cache_creation_tokens": 0, "cache_read_tokens": 0} for i in range(24)
        }

        with self.get_connection() as conn:
            cursor = conn.cursor()
            # JST (+9時間) で集計するようにクエリを修正
            cursor.execute("""
                SELECT
                    CAST(strftime('%H', timestamp, '+9 hours') AS INTEGER) as hour,
                    SUM(input_tokens) as total_input_tokens,
                    SUM(output_tokens) as total_output_tokens,
                    SUM(cache_creation_tokens) as cache_creation_tokens,
                    SUM(cache_read_tokens) as cache_read_tokens
                FROM session_entries
                WHERE date(timestamp, '+9 hours') = ?
                GROUP BY hour
            """, (date,))

            for row in cursor.fetchall():
                hour = row["hour"]
                if hour in hourly_results:
                    hourly_results[hour]["input_tokens"] = row["total_input_tokens"] or 0
                    hourly_results[hour]["output_tokens"] = row["total_output_tokens"] or 0
                hourly_results[hour]["cache_creation_tokens"] = row["cache_creation_tokens"] or 0
                hourly_results[hour]["cache_read_tokens"] = row["cache_read_tokens"] or 0
        
        # 辞書の値のリストを時間順にソートして返す
        return sorted(list(hourly_results.values()), key=lambda x: x["hour"])
