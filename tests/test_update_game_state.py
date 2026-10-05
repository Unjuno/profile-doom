"""Regression tests for persistent command bookkeeping."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "update_game_state.py"


def load_module():
    spec = importlib.util.spec_from_file_location("update_game_state", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class GameStateUpdateTests(unittest.TestCase):
    def test_one_shot_issue_records_deduplication_marker_without_advancing_comment_cursor(self):
        module = load_module()
        self.assertTrue(callable(getattr(module, "apply_payload", None)), "missing apply_payload")
        state = {
            "input_count": 4,
            "last_comment_id": 700,
            "last_input_issue_number": 0,
        }
        payload = {
            "max_seen_comment_id": 700,
            "commands": [{
                "id": 9001,
                "command": "/fire",
                "actor": "octocat",
                "source": "issue",
                "issue_number": 42,
            }],
        }
        result = module.apply_payload(state, payload, now="2026-10-05T14:00:00+00:00")
        self.assertEqual(result["input_count"], 5)
        self.assertEqual(result["last_input"], "/fire")
        self.assertEqual(result["last_actor"], "octocat")
        self.assertEqual(result["last_input_issue_number"], 42)
        self.assertEqual(result["last_comment_id"], 700)
        self.assertEqual(result["updated_at"], "2026-10-05T14:00:00+00:00")

    def test_comment_command_keeps_existing_issue_marker(self):
        module = load_module()
        state = {
            "input_count": 5,
            "last_comment_id": 700,
            "last_input_issue_number": 42,
        }
        payload = {
            "max_seen_comment_id": 701,
            "commands": [{
                "id": 701,
                "command": "/left",
                "actor": "octocat",
            }],
        }
        result = module.apply_payload(state, payload, now="2026-10-05T14:01:00+00:00")
        self.assertEqual(result["last_comment_id"], 701)
        self.assertEqual(result["last_input_issue_number"], 42)
        self.assertEqual(result["last_command_comment_id"], 701)


if __name__ == "__main__":
    unittest.main()
