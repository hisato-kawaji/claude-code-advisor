"""Local, evidence-limited cache-use observations; no prompts or LLM required."""
from datetime import datetime, timedelta, timezone
from .db_manager import DatabaseManager


def build_cache_advice(db: DatabaseManager, days: int):
    end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=days - 1)
    with db.get_connection() as conn:
        rows = conn.execute('''
            SELECT session_id,
                CASE WHEN json_extract(message_json, '$.isSidechain') = 1
                           OR json_extract(message_json, '$._analytics_source.kind') = 'subagent'
                     THEN 'subagent'
                     WHEN json_extract(message_json, '$._analytics_source.kind') = 'session'
                     THEN 'main' ELSE 'unknown' END AS source_kind,
                COALESCE(json_extract(message_json, '$._analytics_source.path'), '') AS source_path,
                COUNT(DISTINCT COALESCE(request_key, 'row:' || id)) AS request_count,
                SUM(CASE WHEN request_key IS NULL THEN 1 ELSE 0 END) AS missing_request_ids,
                SUM(input_tokens) AS input_tokens,
                SUM(output_tokens) AS output_tokens,
                SUM(cache_creation_tokens) AS cache_creation_tokens,
                SUM(cache_read_tokens) AS cache_read_tokens
            FROM session_entries
            WHERE date >= ? AND date <= ? AND entry_type = 'assistant'
              AND input_tokens + output_tokens + cache_creation_tokens + cache_read_tokens > 0
            GROUP BY session_id, source_kind, source_path
            ORDER BY cache_read_tokens DESC
        ''', (start.isoformat(), end.isoformat())).fetchall()

    fields = ('input_tokens', 'output_tokens', 'cache_creation_tokens', 'cache_read_tokens')
    totals = {key: sum(row[key] or 0 for row in rows) for key in fields}
    requests = sum(row['request_count'] for row in rows)
    read = totals['cache_read_tokens']
    input_total = totals['input_tokens'] + totals['cache_creation_tokens'] + read
    sources = {kind: sum(row['cache_read_tokens'] or 0 for row in rows if row['source_kind'] == kind)
               for kind in ('main', 'subagent', 'unknown')}
    top = [{"session_id": row['session_id'][:8], "source_kind": row['source_kind'],
            "request_count": row['request_count'], "cache_read_tokens": row['cache_read_tokens'] or 0,
            "cache_creation_tokens": row['cache_creation_tokens'] or 0,
            "avg_cache_read_per_request": round((row['cache_read_tokens'] or 0) / row['request_count'])}
           for row in rows[:5]]
    recommendations = []
    if requests:
        leading = top[0]
        leading_share = round(leading['cache_read_tokens'] * 100 / read, 1) if read else 0
        agent_hint = (
            f"子エージェントの記録が読み込み全体の {round(sources['subagent'] * 100 / read, 1)}% を占めています。"
            if read and sources['subagent'] else "この期間の子エージェント記録では読み込みが確認できません。"
        )
        recommendations = [
            {"title": "大きいセッションから確認する", "detail": f"上位の記録（セッションID先頭 {leading['session_id']}）は読み込み全体の {leading_share}% です。該当作業で /usage と /context を確認し、長い履歴や大量のツール出力が必要かを見直してください。累積読み込み量は現在のコンテキスト占有量ではありません。"},
            {"title": "区切りでコンテキストを整理する", "detail": "関連する作業では必要な前提を保持し、自然な区切りで /compact を検討してください。要約にはコストがあり、会話部分のキャッシュは再構築されるため、前後の利用量と作業結果を比較してください。"},
            {"title": "並列・サブエージェントの使い方を比較する", "detail": agent_hint + " 並列数や委譲範囲を変える場合は、同程度の仕事で親と子を合算した使用量・待ち時間・成果を比較してください。分離はメインのコンテキストを守りますが、総消費を必ず減らすわけではありません。"},
            {"title": "キャッシュの再作成も確認する", "detail": "キャッシュ読み込みは再利用の記録です。書き込みが繰り返し多い場合は /usage のキャッシュ情報を確認し、作業途中のモデル切り替えなどの影響を調べてください。原因はこの集計だけでは特定できません。"},
        ]
    return {
        "start_date": start.isoformat(), "end_date": end.isoformat(), "timezone": "UTC",
        "totals": totals, "request_count": requests,
        "missing_request_ids": sum(row["missing_request_ids"] for row in rows),
        "cache_read_share_of_input_pct": round(read * 100 / input_total, 1) if input_total else None,
        "sources": sources, "top_sessions": top, "recommendations": recommendations,
    }
