"""Local-only settings; secrets and prices never leave this SQLite database."""
import fnmatch
import json
import re
from .db_manager import DatabaseManager

DEFAULTS = {"contract": "unknown", "monthly_subscription_usd": None, "provider": "anthropic", "rates": [], "excluded_projects": [], "redact_literals": []}


def load_settings(db: DatabaseManager):
    with db.get_connection() as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS app_settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        row = conn.execute("SELECT value FROM app_settings WHERE key = 'settings'").fetchone()
    return {**DEFAULTS, **(json.loads(row[0]) if row else {})}


def save_settings(db: DatabaseManager, settings: dict):
    with db.get_connection() as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS app_settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        conn.execute("INSERT OR REPLACE INTO app_settings (key, value) VALUES ('settings', ?)", (json.dumps(settings),))


def excluded(path, patterns):
    if not path:
        return bool(patterns)  # Cannot verify the project when exclusions are active.
    return any(fnmatch.fnmatch(path, p) or fnmatch.fnmatch(path.rstrip('/').rsplit('/', 1)[-1], p) for p in patterns)


PATTERNS = [
    (re.compile(r'-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----'), '[REDACTED PRIVATE KEY]'),
    (re.compile(r'\b(?:sk|sk-proj|sk-ant|ghp|github_pat)-[A-Za-z0-9_-]{12,}\b'), '[REDACTED TOKEN]'),
    (re.compile(r'\b(?:ghp|github_pat)_[A-Za-z0-9_]{12,}\b'), '[REDACTED TOKEN]'),
    (re.compile(r'\bAKIA[0-9A-Z]{16}\b'), '[REDACTED AWS KEY]'),
    (re.compile(r'(?i)\b(bearer)\s+[A-Za-z0-9._~+/-]{8,}'), r'\1 [REDACTED]'),
    (re.compile(r'(?i)\b(api[_-]?key|password|secret|token)\b(\s*[=:]\s*[\'"]?)[^\s\'"]{6,}'), r'\1\2[REDACTED]'),
    (re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b'), '[REDACTED EMAIL]'),
]


def redact(value, literals):
    if isinstance(value, str):
        for literal in sorted((x for x in literals if x), key=len, reverse=True):
            value = value.replace(literal, '[REDACTED]')
        for pattern, replacement in PATTERNS:
            value = pattern.sub(replacement, value)
        return value
    if isinstance(value, list):
        return [redact(item, literals) for item in value]
    if isinstance(value, dict):
        return {key: redact(item, literals) for key, item in value.items()}
    return value
