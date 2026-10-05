from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
STATE_PATH = ROOT / "state" / "game.json"


def apply_payload(
    state: dict[str, Any],
    payload: dict[str, Any],
    *,
    now: str | None = None,
) -> dict[str, Any]:
    result = dict(state)
    commands = payload.get("commands", [])

    if commands:
        last = commands[-1]
        result["input_count"] = int(result.get("input_count", 0)) + len(commands)
        result["last_input"] = last["command"]
        result["last_actor"] = last["actor"]
        result["last_command_event_id"] = int(last["id"])

        if last.get("source") == "issue":
            result["last_input_issue_number"] = max(
                int(result.get("last_input_issue_number", 0)),
                int(last["issue_number"]),
            )
        else:
            result["last_command_comment_id"] = int(last["id"])

    result["last_comment_id"] = int(
        payload.get("max_seen_comment_id", result.get("last_comment_id", 0))
    )
    result["updated_at"] = now or datetime.now(timezone.utc).isoformat()
    result["runtime"] = "Chocolate Doom + Freedoom"
    result["mode"] = "shared"
    return result


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: update_game_state.py <commands.json>")

    payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(state, dict):
        raise ValueError("payload and game state must be JSON objects")

    result = apply_payload(state, payload)
    STATE_PATH.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
