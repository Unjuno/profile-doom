"""Render truthful, theme-aware snapshots for the GitHub profile.

Only persisted game metadata is labelled as a snapshot. A generated image is
not a heartbeat, proof of successful input, or a live service-status monitor.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from html import escape
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PALETTES = {
    "light": ("#ffffff", "#d1d9e0", "#1f2328", "#59636e"),
    "dark": ("#0d1117", "#3d444d", "#f0f6fc", "#9198a1"),
}


def clipped(value: str, limit: int) -> str:
    return value if len(value) <= limit else value[:limit - 1] + "…"


def saved_time(value: Any) -> str:
    if not value:
        return "No saved input yet"
    try:
        stamp = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if stamp.tzinfo is None:
            return "Save time unavailable"
        return stamp.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    except (TypeError, ValueError, OverflowError):
        return "Save time unavailable"


def render_status(state: dict[str, Any], theme: str, compact: bool = False) -> str:
    if theme not in PALETTES:
        raise ValueError("theme must be light or dark")
    count = state.get("input_count", 0)
    if type(count) is not int or count < 0:
        raise ValueError("input_count must be a nonnegative integer")
    actor = str(state.get("last_actor") or "none")
    command = str(state.get("last_input") or "none")
    stamp = saved_time(state.get("updated_at"))
    bg, border, primary, secondary = PALETTES[theme]
    description = escape(f"Shared save snapshot. {count} recorded inputs. Last input: "
                         f"{command} by @{actor}. {stamp}. Not a live stream.")
    width, height = (320, 104) if compact else (640, 88)
    left, right = 14, width - 14
    ys = (26, 57, 88) if compact else (24, 49, 74)
    actor_width = 176 if compact else 390
    input_x = 200 if compact else 464
    actor_limit = 17 if compact else 24
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">
  <title id="title">Shared session snapshot</title>
  <desc id="desc">{description}</desc>
  <defs>
    <clipPath id="actor-area"><rect x="{left}" y="{ys[1]-18}" width="{actor_width}" height="24"/></clipPath>
    <clipPath id="input-area"><rect x="{input_x}" y="{ys[1]-18}" width="{right-input_x}" height="24"/></clipPath>
  </defs>
  <rect x="0.5" y="0.5" width="{width-1}" height="{height-1}" rx="6" fill="{bg}" stroke="{border}"/>
  <g font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,Arial,sans-serif">
    <text x="{left}" y="{ys[0]}" fill="{primary}" font-size="15" font-weight="600">Snapshot</text>
    <text x="{right}" y="{ys[0]}" text-anchor="end" fill="{secondary}" font-size="14">{escape(clipped(str(count), 12))} inputs</text>
    <text x="{left}" y="{ys[1]}" fill="{primary}" font-size="14" clip-path="url(#actor-area)">@{escape(clipped(actor, actor_limit))}</text>
    <text x="{right}" y="{ys[1]}" text-anchor="end" fill="{primary}" font-size="14" clip-path="url(#input-area)">{escape(clipped(command, 15))}</text>
    <text x="{left}" y="{ys[2]}" fill="{secondary}" font-size="14">{escape(stamp)}</text>
  </g>
</svg>
'''


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", type=Path, default=ROOT / "state/game.json")
    parser.add_argument("--output", type=Path, default=ROOT / "site")
    args = parser.parse_args()
    state = json.loads(args.state.read_text(encoding="utf-8"))
    if not isinstance(state, dict):
        raise ValueError("game state must be a JSON object")
    outputs = {theme: render_status(state, theme) for theme in PALETTES}
    args.output.mkdir(parents=True, exist_ok=True)
    for theme, svg in outputs.items():
        # Versioned layout names bypass the old layout's Camo URL.
        for filename in (f"status-v3-{theme}.svg", f"status-v2-{theme}.svg", f"status-{theme}.svg"):
            (args.output / filename).write_text(svg, encoding="utf-8")
        (args.output / f"status-v3-mobile-{theme}.svg").write_text(
            render_status(state, theme, compact=True), encoding="utf-8")
    (args.output / "status.svg").write_text(outputs["dark"], encoding="utf-8")
    gif = args.output / "doom.gif"
    if gif.is_file():
        # A real captured frame, not a placeholder, for reduced-motion viewers.
        from PIL import Image
        with Image.open(gif) as image:
            image.seek(image.n_frames - 1)
            image.convert("RGB").save(args.output / "doom-still.png")
        # One image keeps the visual frame and its snapshot metadata together.
        from render_panel import render_panels
        render_panels(gif, state, args.output)


if __name__ == "__main__":
    main()
