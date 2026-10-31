"""プロンプト単位のトークン帰属（ターン分割）ロジック。

セッションJSONLでは1つのユーザープロンプトに対して複数のassistantメッセージ
（テキスト・ツール実行）とtool_result（type=userだが実体はツール結果）が続く。
usageはassistant側に分散して記録されるため、「本物のユーザープロンプト」から
次のプロンプト直前までを1ターンとして区切り、区間内のusageを合算して
プロンプトに帰属させる。

制限:
- tool_result / isMeta / サブエージェント内部(isSidechain)のuserエントリは
  ターン起点にせず、消費は進行中のターンに帰属させる
- ターン起点より前に現れたassistant消費（期間境界をまたいだセッションの続き等）は
  unattributedとして別集計する。取得漏れや帰属の正確性は検証できない
"""
import json
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# 一覧APIで返すプロンプト本文の上限文字数
MAX_PROMPT_CHARS = 2000

COMMAND_NAME_RE = re.compile(r"<command-name>(.*?)</command-name>", re.S)
COMMAND_ARGS_RE = re.compile(r"<command-args>(.*?)</command-args>", re.S)

# ハーネスが自動生成するuserエントリの先頭パターン。人が書いたプロンプトではなく、
# 直前のプロンプトが起動した作業の継続なので、ターン起点にせず現行ターンに帰属させる
SYSTEM_GENERATED_PREFIXES = (
    "<task-notification>",
    "<system-reminder>",
    "[Request interrupted",
    "Stop hook feedback:",
    "Caveat: The messages below",
)

HISTOGRAM_BUCKETS = [
    (0, 1_000, "〜1K"),
    (1_000, 5_000, "1K〜5K"),
    (5_000, 10_000, "5K〜10K"),
    (10_000, 50_000, "10K〜50K"),
    (50_000, 100_000, "50K〜100K"),
    (100_000, None, "100K〜"),
]


def _extract_text(entry: Dict) -> Optional[str]:
    """userエントリからプロンプトテキストを抽出する。tool_resultを含む場合はNone"""
    message = entry.get("message")
    if isinstance(message, str):
        return message
    if not isinstance(message, dict):
        return None

    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        if any(
            isinstance(item, dict) and item.get("type") == "tool_result"
            for item in content
        ):
            return None
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(item.get("text", ""))
            elif isinstance(item, str):
                parts.append(item)
        text = " ".join(p for p in parts if p)
        return text or None
    return None


def classify_user_entry(entry: Dict) -> Tuple[str, Optional[str], bool]:
    """userエントリを (kind, prompt_text, is_command) に分類する。

    kind:
      - "prompt": ターンの起点となる入力（通常プロンプト or スラッシュコマンド）
      - "noise": tool_result / meta / サブエージェント内部など。
        ターン起点にはならず、消費は進行中のターンに含める
    """
    if entry.get("isSidechain") or entry.get("_analytics_source", {}).get("kind") == "subagent":
        # サブエージェントへの内部プロンプト。別履歴や並行処理の親ターンは特定できない
        return ("noise", None, False)

    text = _extract_text(entry)
    if not text or not text.strip():
        return ("noise", None, False)
    text = text.strip()

    if "<local-command-stdout>" in text:
        # ローカルコマンドの出力エントリ。直前のターンの一部
        return ("noise", None, False)

    if text.startswith(SYSTEM_GENERATED_PREFIXES):
        return ("noise", None, False)

    if "<command-name>" in text:
        # スラッシュコマンド起動。以降の消費をコマンドに帰属させるため
        # ターン起点として扱い、is_commandフラグを立てる
        name_m = COMMAND_NAME_RE.search(text)
        args_m = COMMAND_ARGS_RE.search(text)
        display = name_m.group(1).strip() if name_m else "(command)"
        args = args_m.group(1).strip() if args_m else ""
        if args:
            display = f"{display} {args}"
        return ("prompt", display, True)

    if entry.get("isMeta"):
        return ("noise", None, False)

    return ("prompt", text, False)


def _parse_ts(ts: Optional[str]) -> Optional[datetime]:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None


def _count_tool_uses(entry: Dict) -> int:
    message = entry.get("message")
    if not isinstance(message, dict):
        return 0
    content = message.get("content")
    if not isinstance(content, list):
        return 0
    return sum(
        1
        for item in content
        if isinstance(item, dict) and item.get("type") == "tool_use"
    )


def _extract_project(entry: Dict) -> Optional[str]:
    cwd = entry.get("cwd")
    if isinstance(cwd, str) and cwd.strip():
        return cwd.rstrip("/").rsplit("/", 1)[-1]
    return None


def build_turns(rows: List[Dict], pricing_settings: Optional[Dict] = None) -> Tuple[List[Dict], Dict]:
    """DB行（session_id, timestamp順）からターン一覧と未帰属集計を作る。

    rows の各要素: session_id, timestamp, entry_type, message_json,
    input_tokens, output_tokens, cache_creation_tokens, cache_read_tokens

    戻り値: (turns, unattributed)
    """
    turns: List[Dict] = []
    unattributed = {
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_creation_tokens": 0,
        "cache_read_tokens": 0,
        "assistant_messages": 0,
    }

    # With equal timestamps the order of a user and assistant event is ambiguous.
    ambiguous = {(r["session_id"], r["timestamp"]) for r in rows if r["entry_type"] == "user"}
    current: Optional[Dict] = None
    current_session: Optional[str] = None

    def finalize(turn: Optional[Dict]):
        if turn is None:
            return
        start = _parse_ts(turn.pop("_start_ts"))
        end = _parse_ts(turn.pop("_end_ts"))
        duration = 0.0
        if start and end and end > start:
            duration = round((end - start).total_seconds(), 1)
        turn["duration_seconds"] = duration
        turn["total_tokens"] = sum(turn[k] for k in ("input_tokens", "output_tokens", "cache_creation_tokens", "cache_read_tokens"))
        cost = turn.pop("_cost")
        turn["estimated_cost_usd"] = round(cost, 6) if cost is not None else None
        turns.append(turn)

    for row in rows:
        session_id = row["session_id"]
        if session_id != current_session:
            # セッションが変わったら進行中のターンを確定
            finalize(current)
            current = None
            current_session = session_id

        try:
            entry = json.loads(row["message_json"])
        except (json.JSONDecodeError, TypeError):
            continue

        entry_type = row["entry_type"]

        if entry_type == "user":
            kind, text, is_command = classify_user_entry(entry)
            if kind == "prompt":
                finalize(current)
                current = {
                    "session_id": session_id,
                    "project": _extract_project(entry),
                    "project_path": entry.get("cwd"),
                    "timestamp": row["timestamp"],
                    "prompt": text[:MAX_PROMPT_CHARS],
                    "prompt_length": len(text),
                    "is_command": is_command,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cache_creation_tokens": 0,
                    "cache_read_tokens": 0,
                    "assistant_messages": 0,
                    "tool_use_count": 0,
                    "_cost": 0.0 if pricing_settings and pricing_settings.get("contract") == "api" else None,
                    "_start_ts": row["timestamp"],
                    "_end_ts": row["timestamp"],
                }
            elif current is not None:
                # tool_result等もターンの経過時間に含める
                current["_end_ts"] = row["timestamp"]

        elif entry_type == "assistant":
            sidechain = entry.get("isSidechain") or entry.get("_analytics_source", {}).get("kind") == "subagent"
            target = current if current is not None and not sidechain and (session_id, row["timestamp"]) not in ambiguous else unattributed
            target["input_tokens"] += row["input_tokens"] or 0
            target["output_tokens"] += row["output_tokens"] or 0
            target["cache_creation_tokens"] += row["cache_creation_tokens"] or 0
            target["cache_read_tokens"] += row["cache_read_tokens"] or 0
            target["assistant_messages"] += 1
            if target is current and current is not None:
                from .pricing import estimate_entry
                priced_entry = dict(entry)
                priced_message = dict(entry.get("message") or {})
                priced_usage = dict(priced_message.get("usage") or {})
                for source, column in (("input_tokens", "input_tokens"), ("output_tokens", "output_tokens"),
                                       ("cache_creation_input_tokens", "cache_creation_tokens"), ("cache_read_input_tokens", "cache_read_tokens")):
                    priced_usage[source] = row[column] or 0
                if not priced_usage["cache_creation_input_tokens"]:
                    priced_usage["cache_creation"] = {}
                priced_message["usage"] = priced_usage
                priced_entry["message"] = priced_message
                cost = estimate_entry(priced_entry, pricing_settings or {})
                if current["_cost"] is not None:
                    current["_cost"] = current["_cost"] + cost if cost is not None else None
                current["tool_use_count"] += _count_tool_uses(entry)
                current["_end_ts"] = row["timestamp"]

    finalize(current)
    return turns, unattributed


def summarize_turns(turns: List[Dict], unattributed: Dict) -> Dict:
    """ターン一覧からサマリー統計（分布・帰属率・上位消費プロンプト）を作る"""
    total_prompts = len(turns)
    command_prompts = sum(1 for t in turns if t["is_command"])

    per_turn = sorted(t["total_tokens"] for t in turns)
    total_tokens = sum(per_turn)
    total_cost = (sum(t["estimated_cost_usd"] for t in turns)
                  if turns and all(t["estimated_cost_usd"] is not None for t in turns) else None)

    def percentile(values: List[int], p: float) -> float:
        if not values:
            return 0.0
        idx = (len(values) - 1) * p
        lo, hi = int(idx), min(int(idx) + 1, len(values) - 1)
        frac = idx - lo
        return values[lo] * (1 - frac) + values[hi] * frac

    histogram = []
    for low, high, label in HISTOGRAM_BUCKETS:
        count = sum(
            1
            for v in per_turn
            if v >= low and (high is None or v < high)
        )
        histogram.append({"label": label, "count": count})

    attributed_all = sum(
        t["input_tokens"]
        + t["output_tokens"]
        + t["cache_creation_tokens"]
        + t["cache_read_tokens"]
        for t in turns
    )
    unattributed_all = (
        unattributed["input_tokens"]
        + unattributed["output_tokens"]
        + unattributed["cache_creation_tokens"]
        + unattributed["cache_read_tokens"]
    )
    denominator = attributed_all + unattributed_all
    coverage = None if denominator == 0 else attributed_all / denominator * 100

    top_prompts = sorted(
        turns, key=lambda t: t["total_tokens"], reverse=True
    )[:10]

    return {
        "total_prompts": total_prompts,
        "command_prompts": command_prompts,
        "total_tokens": total_tokens,
        "total_cost_usd": total_cost,
        "avg_tokens_per_prompt": round(total_tokens / total_prompts, 1) if total_prompts else 0.0,
        "median_tokens_per_prompt": round(percentile(per_turn, 0.5), 1),
        "p90_tokens_per_prompt": round(percentile(per_turn, 0.9), 1),
        "max_tokens_per_prompt": per_turn[-1] if per_turn else 0,
        "attributed_tokens": attributed_all,
        "unattributed_tokens": unattributed_all,
        "attribution_coverage_pct": round(coverage, 2) if coverage is not None else None,
        "histogram": histogram,
        "top_prompts": top_prompts,
    }
