from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE_PATH = ROOT / "state" / "game.json"


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: update_game_state.py <commands.json>")

    payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    commands = payload.get("commands", [])

    if commands:
        last = commands[-1]
        state["input_count"] = int(state.get("input_count", 0)) + len(commands)
        state["last_input"] = last["command"]
        state["last_actor"] = last["actor"]
        state["last_command_comment_id"] = int(last["id"])

    state["last_comment_id"] = int(
        payload.get("max_seen_comment_id", state.get("last_comment_id", 0))
    )
    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    state["runtime"] = "Chocolate Doom + Freedoom"
    state["mode"] = "shared"

    STATE_PATH.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
