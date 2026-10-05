from __future__ import annotations

import json
import math
from pathlib import Path
from datetime import datetime, timezone

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
STATE_PATH = ROOT / "state" / "state.json"
SITE = ROOT / "site"
SITE.mkdir(parents=True, exist_ok=True)

W, H = 640, 360
FRAMES = 24
DURATION_MS = 80


def font(size: int):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    ]
    for p in candidates:
        if Path(p).exists():
            return ImageFont.truetype(p, size=size)
    return ImageFont.load_default()


F_BIG = font(30)
F_MED = font(18)
F_SMALL = font(13)


def draw_corridor(draw: ImageDraw.ImageDraw, phase: float) -> None:
    horizon = 155
    center_x = W // 2

    # Dark synthetic "game viewport"; deliberately original geometry, not DOOM assets.
    draw.rectangle((0, 0, W, 260), fill=(10, 12, 14))
    draw.rectangle((0, horizon, W, 260), fill=(22, 20, 18))

    for i in range(7):
        z = ((i / 7.0) + phase) % 1.0
        scale = 0.14 + z * 0.86
        half_w = int(48 + 250 * scale)
        floor_y = int(horizon + 102 * scale)
        ceil_y = int(horizon - 72 * scale)
        shade = int(45 + 90 * scale)

        draw.line((center_x - half_w, floor_y, center_x + half_w, floor_y),
                  fill=(shade, shade, shade), width=2)
        draw.line((center_x - half_w, ceil_y, center_x + half_w, ceil_y),
                  fill=(shade, shade, shade), width=2)

    draw.line((0, 260, center_x - 55, horizon), fill=(110, 110, 110), width=2)
    draw.line((W, 260, center_x + 55, horizon), fill=(110, 110, 110), width=2)
    draw.line((0, 0, center_x - 55, horizon), fill=(65, 65, 65), width=2)
    draw.line((W, 0, center_x + 55, horizon), fill=(65, 65, 65), width=2)

    # Moving reticle proves animation without copyrighted game imagery.
    bob = int(3 * math.sin(phase * math.tau))
    cx, cy = center_x, 150 + bob
    draw.line((cx - 9, cy, cx + 9, cy), fill=(210, 210, 210), width=1)
    draw.line((cx, cy - 9, cx, cy + 9), fill=(210, 210, 210), width=1)


def main() -> None:
    state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    frames: list[Image.Image] = []

    for idx in range(FRAMES):
        phase = idx / FRAMES
        im = Image.new("RGB", (W, H), (13, 17, 23))
        d = ImageDraw.Draw(im)

        draw_corridor(d, phase)

        # HUD-like diagnostic strip.
        d.rectangle((0, 260, W, H), fill=(20, 24, 30))
        d.line((0, 260, W, 260), fill=(70, 78, 88), width=1)

        title = "PROFILE-DOOM // DISPLAY PIPELINE"
        d.text((18, 276), title, font=F_MED, fill=(230, 235, 240))
        d.text((18, 306), f"MODE {state['mode']}   MAP {state['map']}   INPUTS {state['input_count']}",
               font=F_SMALL, fill=(180, 188, 198))
        d.text((18, 329), "BOOT RENDER — REAL GAME RUNTIME NOT CONNECTED YET",
               font=F_SMALL, fill=(160, 168, 178))

        pulse = 150 + int(90 * (0.5 + 0.5 * math.sin(phase * math.tau)))
        d.rectangle((600, 317, 610, 327), fill=(pulse, pulse, pulse))

        frames.append(im)

    out = SITE / "doom.gif"
    frames[0].save(
        out,
        save_all=True,
        append_images=frames[1:],
        duration=DURATION_MS,
        loop=0,
        optimize=True,
    )

    status = f"""<svg xmlns="http://www.w3.org/2000/svg" width="640" height="76" viewBox="0 0 640 76">
  <rect width="640" height="76" rx="8" fill="#0d1117"/>
  <rect x="0.5" y="0.5" width="639" height="75" rx="7.5" fill="none" stroke="#30363d"/>
  <text x="18" y="27" fill="#f0f6fc" font-family="monospace" font-size="15">profile-doom / {state['mode']}</text>
  <text x="18" y="51" fill="#8b949e" font-family="monospace" font-size="12">last input: {state['last_input']} · inputs: {state['input_count']} · generated: {generated}</text>
</svg>
"""
    (SITE / "status.svg").write_text(status, encoding="utf-8")


if __name__ == "__main__":
    main()
