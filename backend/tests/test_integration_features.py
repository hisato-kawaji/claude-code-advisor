import json
import tempfile
import unittest
from pathlib import Path
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from app.api.analysis import get_collector
from app.api.stats import get_collector as get_stats_collector
from app.config import Settings, get_settings
from app.main import app
from app.services.data_collector import ClaudeDataCollector
from app.services.pricing import estimate_entry
from app.services.settings_store import redact, save_settings


class FeatureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.claude = root / 'claude'
        self.project = self.claude / 'projects' / 'example'
        (self.project / 's' / 'subagents').mkdir(parents=True)
        self.collector = ClaudeDataCollector(str(self.claude), str(root / 'db.sqlite'))
        self.settings = Settings(database_path=str(root / 'db.sqlite'), otel_receiver_token='test-token')
        app.dependency_overrides[get_collector] = lambda: self.collector
        app.dependency_overrides[get_stats_collector] = lambda: self.collector
        app.dependency_overrides[get_settings] = lambda: self.settings
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()
        self.temp.cleanup()

    def test_import_is_idempotent_and_child_not_attributed(self):
        day = datetime.now(timezone.utc).date().isoformat()
        def entry(t, uid, typ, content, extra=None):
            return dict(uuid=uid, type=typ, sessionId='s', timestamp=f'{day}T12:00:0{t}Z', cwd='/work/example', message=content, **(extra or {}))
        usage = {'input_tokens': 10, 'output_tokens': 3}
        parent = [entry(0, 'u', 'user', {'content': 'Please fix it'}), entry(1, 'a', 'assistant', {'content': [], 'usage': usage})]
        child = entry(2, 'c', 'assistant', {'content': [], 'usage': usage}, {'isSidechain': True})
        (self.project / 's.jsonl').write_text('\n'.join(map(json.dumps, parent)) + '\n{broken')
        (self.project / 's' / 'subagents' / 'a.jsonl').write_text(json.dumps(child) + '\n')
        first = self.collector.sync_to_database()
        second = self.collector.sync_to_database()
        self.assertEqual((first['inserted'], first['malformed'], first['subagent_files']), (3, 1, 1))
        self.assertEqual((second['inserted'], second['skipped']), (0, 3))
        data = self.collector.get_prompt_turns(7)
        self.assertEqual(data['turns'][0]['total_tokens'], 13)
        self.assertEqual(data['summary']['unattributed_tokens'], 13)

    def test_repeated_request_usage_is_counted_once_across_syncs(self):
        day = datetime.now(timezone.utc).date().isoformat()
        prompt = {'uuid': 'u', 'type': 'user', 'sessionId': 's', 'timestamp': f'{day}T12:00:00Z', 'message': {'content': 'hello world'}}
        def assistant(uid, second, count):
            return {'uuid': uid, 'requestId': 'req-1', 'type': 'assistant', 'sessionId': 's', 'timestamp': f'{day}T12:00:0{second}Z', 'message': {'content': [], 'usage': {'input_tokens': 10, 'output_tokens': count}}}
        file = self.project / 's.jsonl'
        file.write_text('\n'.join(map(json.dumps, [prompt, assistant('a', 1, 1)])) + '\n')
        self.collector.sync_to_database()
        file.write_text('\n'.join(map(json.dumps, [prompt, assistant('a', 1, 1), assistant('b', 2, 4), {'uuid': 'empty', 'requestId': 'req-1', 'type': 'assistant', 'sessionId': 's', 'timestamp': f'{day}T12:00:03Z', 'message': {'content': []}}])) + '\n')
        self.collector.sync_to_database()
        self.collector.sync_to_database()
        result = self.collector.get_prompt_turns(7)
        self.assertEqual(result['turns'][0]['total_tokens'], 14)
        weekly = self.collector.get_weekly_history_optimized(1)[0]
        monthly = self.collector.get_monthly_history_optimized(1)[0]
        self.assertEqual(weekly['total_input_tokens'] + weekly['total_output_tokens'], 14)
        self.assertEqual(monthly['total_input_tokens'] + monthly['total_output_tokens'], 14)

    def test_weekly_monthly_boundaries_and_hourly_cache(self):
        def item(uid, timestamp, n):
            return {'uuid': uid, 'type': 'assistant', 'sessionId': 's', 'timestamp': timestamp,
                    'message': {'usage': {'input_tokens': n, 'output_tokens': n, 'cache_creation_input_tokens': n, 'cache_read_input_tokens': n}}}
        entries = [item('a', '2026-02-22T23:00:00Z', 1), item('b', '2026-02-23T00:00:00Z', 2),
                   item('c', '2026-03-01T00:00:00Z', 4), item('d', '2026-03-02T00:00:00Z', 8)]
        self.collector.db.bulk_insert_entries(entries)
        weekly = self.client.get('/api/stats/weekly', params={'date': '2026-02-25'}).json()
        self.assertEqual(weekly['current']['total_input_tokens'], 6)
        self.assertEqual(weekly['previous']['total_input_tokens'], 1)
        monthly_response = self.client.get('/api/stats/monthly', params={'date': '2026-03-31'})
        self.assertEqual(monthly_response.status_code, 200)
        self.assertEqual(monthly_response.json()['previous']['total_input_tokens'], 3)
        self.assertEqual(monthly_response.json()['current']['total_input_tokens'], 12)
        hourly = self.client.get('/api/stats/hourly', params={'date': '2026-03-02'}).json()
        self.assertEqual(hourly[9]['cache_read_tokens'], 8)
        self.assertEqual(hourly[9]['cache_creation_tokens'], 8)

    def test_cache_advice_uses_complete_days_and_separates_agents(self):
        today = datetime.now(timezone.utc).date()
        def item(uid, offset, source, read, write):
            return {'uuid': uid, 'requestId': 'req-' + uid, 'type': 'assistant', 'sessionId': 'session1',
                    'timestamp': f'{(today - timedelta(days=offset)).isoformat()}T12:00:00Z',
                    '_analytics_source': {'kind': source, 'path': source},
                    'message': {'content': 'private content', 'usage': {'input_tokens': 10, 'output_tokens': 5,
                        'cache_creation_input_tokens': write, 'cache_read_input_tokens': read}}}
        self.collector.db.bulk_insert_entries([item('main', 0, 'session', 90, 0), item('child', 6, 'subagent', 190, 10), item('old', 7, 'session', 999, 0)])
        result = self.client.get('/api/analysis/cache-advice?days=7')
        self.assertEqual(result.status_code, 200)
        data = result.json()
        self.assertEqual(data['totals']['cache_read_tokens'], 280)
        self.assertEqual(data['sources'], {'main': 90, 'subagent': 190, 'unknown': 0})
        self.assertEqual(data['request_count'], 2)
        self.assertEqual(data['cache_read_share_of_input_pct'], 90.3)
        self.assertTrue(data['recommendations'])
        self.assertNotIn('private content', result.text)
        empty = self.client.get('/api/analysis/cache-advice?days=0')
        self.assertEqual(empty.status_code, 422)

    def test_pricing_contract_model_dates_and_cache_ttl(self):
        rate = {'provider': 'anthropic', 'model': 'model-a', 'valid_from': '2026-01-01', 'valid_until': '2026-12-31', 'input': 3, 'output': 15, 'cache_read': .3, 'cache_write_5m': 3.75, 'cache_write_1h': 6}
        config = {'contract': 'api', 'provider': 'anthropic', 'rates': [rate]}
        entry = {'timestamp': '2026-10-01T00:00:00Z', 'message': {'model': 'model-a', 'usage': {'input_tokens': 1000, 'output_tokens': 100, 'cache_read_input_tokens': 100, 'cache_creation_input_tokens': 200, 'cache_creation': {'ephemeral_5m_input_tokens': 100, 'ephemeral_1h_input_tokens': 100}}}}
        self.assertAlmostEqual(estimate_entry(entry, config), (3000+1500+30+375+600)/1000000)
        self.assertIsNone(estimate_entry(entry, {**config, 'contract': 'subscription'}))
        self.assertIsNone(estimate_entry(entry, {**config, 'rates': [rate, rate]}))
        del entry['message']['usage']['cache_creation']
        self.assertIsNone(estimate_entry(entry, config))

    def test_redaction_and_exclusion_before_send(self):
        save_settings(self.collector.db, {'contract': 'unknown', 'provider': 'anthropic', 'rates': [], 'excluded_projects': ['private*'], 'redact_literals': ['client-code']})
        redacted = self.client.post('/api/analysis/improve-prompt/preview', json={'prompt': 'alice@example.com client-code', 'consent': False, 'project_path': '/work/public'})
        self.assertNotIn('alice@example.com', redacted.text)
        self.assertNotIn('client-code', redacted.text)
        blocked = self.client.post('/api/analysis/improve-prompt/preview', json={'prompt': 'private content', 'consent': False, 'project_path': '/work/private-app'})
        self.assertEqual(blocked.status_code, 403)
        self.assertIn('[REDACTED', redact('sk-ant-abcdefghijklmnop', []))

    def test_otlp_is_authenticated_idempotent_and_does_not_store_content(self):
        event = {'resourceLogs': [{'scopeLogs': [{'logRecords': [{'attributes': [
            {'key': 'event.name', 'value': {'stringValue': 'api_request'}},
            {'key': 'event.timestamp', 'value': {'stringValue': '2026-10-01T00:00:00Z'}},
            {'key': 'prompt', 'value': {'stringValue': 'SECRET BODY'}},
            {'key': 'model', 'value': {'stringValue': 'model-a'}}]}]}]}]}
        self.assertEqual(self.client.post('/v1/logs', json=event).status_code, 403)
        for _ in range(2):
            self.assertEqual(self.client.post('/v1/logs', json=event, headers={'Authorization': 'Bearer test-token'}).status_code, 200)
        self.assertEqual(self.client.get('/api/telemetry/summary').json()['counts']['api_request'], 1)
        with self.collector.db.get_connection() as conn:
            self.assertNotIn('SECRET BODY', conn.execute('SELECT data FROM otel_events').fetchone()[0])
