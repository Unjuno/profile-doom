from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
STATE_PATH = ROOT / "state" / "game.json"

COMMANDS = {
    "forward": "/forward",
    "back": "/back",
    "left": "/left",
    "right": "/right",
    "fire": "/fire",
    "use": "/use",
}
TITLE_PREFIX = "runtime/input: "


def parse_issue_event(event: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    last_comment_id = int(state.get("last_comment_id", 0))
    payload: dict[str, Any] = {
        "controller_issue": int(state.get("controller_issue", 1)),
        "previous_comment_id": last_comment_id,
        "max_seen_comment_id": last_comment_id,
        "commands": [],
    }

    if event.get("action") != "opened":
        return payload

    issue = event.get("issue")
    if not isinstance(issue, dict):
        return payload

    try:
        issue_number = int(issue.get("number", 0))
        issue_id = int(issue.get("id", 0))
    except (TypeError, ValueError):
        return payload

    if issue_number <= int(state.get("last_input_issue_number", 0)):
        return payload

    title = str(issue.get("title") or "").strip().lower()
    body = str(issue.get("body") or "").strip().lower()
    if not title.startswith(TITLE_PREFIX):
        return payload

    slug = title[len(TITLE_PREFIX):].strip()
    expected = COMMANDS.get(slug)
    if expected is None or body != expected:
        return payload

    user = issue.get("user")
    actor = str(user.get("login") or "unknown") if isinstance(user, dict) else "unknown"
    payload["commands"] = [{
        "id": issue_id,
        "command": expected,
        "actor": actor,
        "source": "issue",
        "issue_number": issue_number,
    }]
    return payload


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: collect_issue_command.py <event.json> <output.json>")

    event_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])
    event = json.loads(event_path.read_text(encoding="utf-8"))
    state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    if not isinstance(event, dict) or not isinstance(state, dict):
        raise ValueError("event and state must be JSON objects")

    payload = parse_issue_event(event, state)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(len(payload["commands"]))


if __name__ == "__main__":
    main()
