"""Opt-in OTLP/HTTP JSON log receiver. Never stores prompt or tool contents."""
import hashlib
import hmac
import json
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from app.config import get_settings, Settings
from app.services.db_manager import DatabaseManager

router = APIRouter(tags=['telemetry'])
ALLOWED = {'user_prompt', 'api_request', 'tool_result', 'api_error'}
FIELDS = {'event.name', 'event.timestamp', 'event.sequence', 'session.id', 'prompt.id', 'request_id',
          'client_request_id', 'model', 'input_tokens', 'output_tokens', 'cache_read_tokens',
          'cache_creation_tokens', 'cost_usd', 'duration_ms', 'success', 'query_source'}


def attrs(items):
    result = {}
    for item in items or []:
        value = item.get('value', {})
        for kind in ('stringValue', 'intValue', 'doubleValue', 'boolValue'):
            if kind in value:
                result[item.get('key')] = value[kind]
                break
    return result


def check_token(settings, authorization):
    token = settings.otel_receiver_token
    if not token or not authorization or not hmac.compare_digest(authorization, 'Bearer ' + token):
        raise HTTPException(status_code=403, detail='OTLP receiver disabled or unauthorized')


def init(db):
    with db.get_connection() as conn:
        conn.execute('CREATE TABLE IF NOT EXISTS otel_events (event_key TEXT PRIMARY KEY, event_name TEXT NOT NULL, timestamp TEXT, session_id TEXT, prompt_id TEXT, model TEXT, data TEXT NOT NULL)')

@router.post('/v1/logs')
async def receive_logs(request: Request, authorization: str | None = Header(default=None), settings: Settings = Depends(get_settings)):
    check_token(settings, authorization)
    if 'application/json' not in request.headers.get('content-type', ''):
        raise HTTPException(status_code=415, detail='Only OTLP HTTP/JSON logs are supported')
    if int(request.headers.get('content-length', '0')) > 2_000_000:
        raise HTTPException(status_code=413, detail='Batch too large')
    raw_body = await request.body()
    if len(raw_body) > 2_000_000:
        raise HTTPException(status_code=413, detail='Batch too large')
    try:
        payload = json.loads(raw_body)
        if not isinstance(payload, dict):
            raise ValueError('invalid payload')
    except (json.JSONDecodeError, ValueError):
        raise HTTPException(status_code=400, detail='Invalid OTLP JSON')
    db = DatabaseManager(settings.database_path)
    init(db)
    with db.get_connection() as conn:
        for resource in payload.get('resourceLogs', []):
            base = attrs(resource.get('resource', {}).get('attributes'))
            for scope in resource.get('scopeLogs', []):
                for log in scope.get('logRecords', []):
                    data = {**base, **attrs(log.get('attributes'))}
                    event = data.get('event.name', '')
                    event = str(event).removeprefix('claude_code.')
                    if event not in ALLOWED:
                        continue
                    data['event.name'] = event
                    safe = {k: v for k, v in data.items() if k in FIELDS}
                    if not safe.get('event.timestamp'):
                        safe['event.timestamp'] = log.get('timeUnixNano')
                    # A canonical hash makes OTLP retries idempotent without merging with JSONL.
                    raw = json.dumps(safe, sort_keys=True, ensure_ascii=False)
                    key = hashlib.sha256(raw.encode()).hexdigest()
                    conn.execute('INSERT OR IGNORE INTO otel_events VALUES (?, ?, ?, ?, ?, ?, ?)',
                                 (key, event, safe.get('event.timestamp'), safe.get('session.id'), safe.get('prompt.id'), safe.get('model'), raw))
    return {}

@router.get('/api/telemetry/summary')
def telemetry_summary(settings: Settings = Depends(get_settings)):
    db = DatabaseManager(settings.database_path)
    init(db)
    with db.get_connection() as conn:
        counts = {r[0]: r[1] for r in conn.execute('SELECT event_name, count(*) FROM otel_events GROUP BY event_name')}
        models = [{'model': r[0], 'requests': r[1]} for r in conn.execute("SELECT COALESCE(model, 'unknown'), count(*) FROM otel_events WHERE event_name = 'api_request' GROUP BY model ORDER BY count(*) DESC")]
        requests = [json.loads(r[0]) for r in conn.execute("SELECT data FROM otel_events WHERE event_name = 'api_request'")]
    totals = {}
    for field in ('input_tokens', 'output_tokens', 'cache_read_tokens', 'cache_creation_tokens'):
        valid = []
        for item in requests:
            try:
                valid.append(int(item[field]))
            except (ValueError, TypeError, KeyError):
                pass
        totals[field] = sum(valid) if len(valid) == len(requests) and valid else None
    costs = []
    for item in requests:
        try:
            costs.append(float(item['cost_usd']))
        except (ValueError, TypeError, KeyError):
            pass
    totals['estimated_cost_usd'] = sum(costs) if len(costs) == len(requests) and costs else None
    return {'enabled': bool(settings.otel_receiver_token), 'counts': counts, 'models': models,
            'totals': totals, 'note': 'OTLP events are independent from JSONL totals; do not add them together.'}
