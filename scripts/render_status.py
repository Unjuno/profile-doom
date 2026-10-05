from __future__ import annotations

import json
from datetime import datetime, timezone
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
STATE = ROOT / "state" / "game.json"
SITE.mkdir(parents=True, exist_ok=True)

state = json.loads(STATE.read_text(encoding="utf-8"))
generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
last_actor = str(state.get("last_actor", "none"))
last_input = str(state.get("last_input", "none"))
count = int(state.get("input_count", 0))

svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="640" height="88" viewBox="0 0 640 88">
  <rect width="640" height="88" rx="6" fill="#0d1117"/>
  <rect x="0.5" y="0.5" width="639" height="87" rx="5.5" fill="none" stroke="#30363d"/>
  <circle cx="22" cy="24" r="5" fill="#3fb950"/>
  <text x="36" y="29" fill="#f0f6fc" font-family="ui-monospace,monospace" font-size="15">profile-doom</text>
  <text x="532" y="29" fill="#8b949e" font-family="ui-monospace,monospace" font-size="12">active</text>
  <text x="18" y="55" fill="#c9d1d9" font-family="ui-monospace,monospace" font-size="12">last: @{escape(last_actor)} → {escape(last_input)}   inputs: {count}</text>
  <text x="18" y="75" fill="#8b949e" font-family="ui-monospace,monospace" font-size="11">Chocolate Doom + Freedoom · GitHub Actions · {generated}</text>
</svg>
"""
(SITE / "status.svg").write_text(svg, encoding="utf-8")
