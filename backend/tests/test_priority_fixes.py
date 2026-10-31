import json
import unittest
import tempfile
from app.services.db_manager import DatabaseManager
from unittest.mock import Mock

from fastapi.testclient import TestClient
from app.main import app
from app.api.analysis import get_analyzer, get_collector
from app.services.prompt_turns import build_turns, summarize_turns


def row(kind, timestamp, content, usage=None):
    entry = {"type": kind, "message": {"content": content}, "sessionId": "s", "timestamp": timestamp}
    usage = usage or (0, 0, 0, 0)
    return dict(session_id="s", timestamp=timestamp, entry_type=kind, message_json=json.dumps(entry),
                input_tokens=usage[0], output_tokens=usage[1], cache_creation_tokens=usage[2], cache_read_tokens=usage[3])


class AttributionTests(unittest.TestCase):
    def test_totals_and_unknown_cost(self):
        rows = [row("user", "2026-01-01T00:00:00Z", "work"),
                row("assistant", "2026-01-01T00:00:01Z", [], (10, 20, 30, 40))]
        turns, missing = build_turns(rows)
        summary = summarize_turns(turns, missing)
        self.assertEqual(turns[0]["total_tokens"], 100)
        self.assertIsNone(turns[0]["estimated_cost_usd"])
        self.assertEqual(summary["total_tokens"], 100)
        self.assertEqual(summary["attributed_tokens"], 100)
        self.assertEqual(summary["attribution_coverage_pct"], 100)
        self.assertIsNone(summary["total_cost_usd"])

    def test_empty_and_unattributed(self):
        turns, missing = build_turns([])
        self.assertIsNone(summarize_turns(turns, missing)["attribution_coverage_pct"])
        turns, missing = build_turns([row("assistant", "2026-01-01T00:00:00Z", [], (1, 2, 3, 4))])
        summary = summarize_turns(turns, missing)
        self.assertEqual(summary["unattributed_tokens"], 10)
        self.assertEqual(summary["attribution_coverage_pct"], 0)


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.analyzer = Mock()
        self.collector = Mock()
        self.collector.db = DatabaseManager(self.tmp.name + "/test.db")
        self.collector.db.get_entries_by_date_range = Mock(return_value=[{"type": "user", "message": {"content": "private prompt"}}])
        self.collector.get_analysis_data_optimized.return_value = {"sample_messages": ["private prompt"], "stats": {}}
        app.dependency_overrides[get_analyzer] = lambda: self.analyzer
        app.dependency_overrides[get_collector] = lambda: self.collector
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()
        self.tmp.cleanup()

    def test_retired_fabricated_metrics(self):
        for path in ("performance", "token-reflection"):
            self.assertEqual(self.client.get('/api/analysis/' + path).status_code, 410)

    def test_consent_and_json_body(self):
        path = '/api/analysis/improve-prompt'
        self.assertEqual(self.client.post(path, json={"prompt": "private prompt", "consent": False}).status_code, 400)
        self.assertEqual(self.client.post(path, params={"prompt": "private prompt"}).status_code, 422)
        self.analyzer.suggest_prompt_improvements.assert_not_called()
        self.analyzer.suggest_prompt_improvements.return_value = {"original_prompt": "private prompt", "improved_prompt": "updated", "best_practice_references": []}
        response = self.client.post(path, json={"prompt": "private prompt", "consent": True})
        self.assertEqual(response.status_code, 200)
        self.analyzer.suggest_prompt_improvements.assert_called_once_with("private prompt")

    def test_insights_preview_is_limited_and_reused(self):
        turn = {"prompt": "x" * 400, "total_tokens": 10, "output_tokens": 1,
                "cache_read_tokens": 2, "tool_use_count": 1, "duration_seconds": 5,
                "session_id": "sensitive-id", "project_path": "/public", "is_command": False, "input_tokens": 5, "cache_creation_tokens": 2, "estimated_cost_usd": None}
        self.collector.get_prompt_turns.return_value = {"turns": [turn], "summary": {"top_prompts": [turn], "total_tokens": 10}}
        preview = self.client.get('/api/analysis/prompt-tokens/insights/preview').json()
        self.assertEqual(len(preview["turns"][0]["prompt"]), 300)
        self.assertNotIn("session_id", preview["turns"][0])
        self.assertNotIn("top_prompts", preview["summary"])
        self.analyzer.analyze_prompt_token_patterns.return_value = {"period_days": 7, "analyzed_prompts": 1,
            "high_cost_patterns": [], "efficiency_observations": [], "improvement_suggestions": [],
            "example_rewrites": [], "reflection": ""}
        self.assertEqual(self.client.post('/api/analysis/prompt-tokens/insights', json={**preview, "consent": True}).status_code, 200)
        self.analyzer.analyze_prompt_token_patterns.assert_called_once_with(preview["summary"], preview["turns"], 7)

    def test_preview_and_malformed_response(self):
        response = self.client.get('/api/analysis/best-practices/preview')
        self.assertEqual(response.json(), {"prompt_excerpts": ["private prompt"]})
        self.analyzer.check_best_practices.return_value = {"score": 60}
        response = self.client.post('/api/analysis/best-practices', json={"consent": True, **response.json()})
        self.assertEqual(response.status_code, 502)


if __name__ == '__main__':
    unittest.main()
