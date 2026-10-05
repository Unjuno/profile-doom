from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
SITE.mkdir(parents=True, exist_ok=True)

generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="640" height="76" viewBox="0 0 640 76">
  <rect width="640" height="76" rx="8" fill="#0d1117"/>
  <rect x="0.5" y="0.5" width="639" height="75" rx="7.5" fill="none" stroke="#30363d"/>
  <circle cx="22" cy="25" r="5" fill="#3fb950"/>
  <text x="36" y="30" fill="#f0f6fc" font-family="monospace" font-size="15">profile-doom / runtime</text>
  <text x="18" y="54" fill="#8b949e" font-family="monospace" font-size="12">Chocolate Doom + Freedoom · rendered on GitHub Actions · {generated}</text>
</svg>
"""
(SITE / "status.svg").write_text(svg, encoding="utf-8")
