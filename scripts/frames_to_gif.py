from __future__ import annotations

import sys
from pathlib import Path
from PIL import Image


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: frames_to_gif.py <frames-dir> <output.gif>")

    frames_dir = Path(sys.argv[1])
    output = Path(sys.argv[2])

    paths = sorted(frames_dir.glob("frame-*.png"))
    if not paths:
        raise SystemExit("no frames found")

    frames: list[Image.Image] = []
    for path in paths:
        image = Image.open(path).convert("RGB")
        # Keep the authentic 4:3 game surface but reduce GIF weight.
        image = image.resize((480, 360), Image.Resampling.NEAREST)
        frames.append(image)

    output.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(
        output,
        save_all=True,
        append_images=frames[1:],
        duration=100,
        loop=0,
        optimize=True,
    )


if __name__ == "__main__":
    main()
