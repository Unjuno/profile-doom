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
last_actor = escape(str(state.get("last_actor", "none")))
last_input = escape(str(state.get("last_input", "none")))
count = int(state.get("input_count", 0))


def render(bg: str, border: str, primary: str, secondary: str, path: str) -> None:
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="640" height="88" viewBox="0 0 640 88">
  <rect width="640" height="88" rx="6" fill="{bg}"/>
  <rect x="0.5" y="0.5" width="639" height="87" rx="5.5" fill="none" stroke="{border}"/>
  <circle cx="22" cy="24" r="5" fill="#1f883d"/>
  <text x="36" y="29" fill="{primary}" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,Arial,sans-serif" font-size="15" font-weight="600">profile-doom</text>
  <text x="578" y="29" text-anchor="end" fill="{secondary}" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,Arial,sans-serif" font-size="12">active</text>
  <text x="18" y="55" fill="{primary}" font-family="ui-monospace,SFMono-Regular,Menlo,Consolas,monospace" font-size="12">last: @{last_actor} → {last_input}   inputs: {count}</text>
  <text x="18" y="75" fill="{secondary}" font-family="ui-monospace,SFMono-Regular,Menlo,Consolas,monospace" font-size="11">Chocolate Doom + Freedoom · GitHub Actions · {generated}</text>
</svg>
"""
    (SITE / path).write_text(svg, encoding="utf-8")


render("#0d1117", "#30363d", "#f0f6fc", "#8b949e", "status-dark.svg")
render("#ffffff", "#d0d7de", "#1f2328", "#656d76", "status-light.svg")

# Default for direct links and the Pages preview.
(SITE / "status.svg").write_text(
    (SITE / "status-dark.svg").read_text(encoding="utf-8"),
    encoding="utf-8",
)
