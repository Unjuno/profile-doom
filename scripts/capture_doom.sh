#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNTIME="$ROOT/runtime"
SITE="$ROOT/site"
mkdir -p "$RUNTIME/frames" "$RUNTIME/save" "$RUNTIME/config" "$SITE"
rm -f "$RUNTIME/frames"/*.png "$SITE/doom.gif" "$RUNTIME/doom.log"

export DISPLAY=:99
export SDL_VIDEODRIVER=x11
export SDL_RENDER_DRIVER=software
export XDG_RUNTIME_DIR="$RUNTIME/xdg"
mkdir -p "$XDG_RUNTIME_DIR"
chmod 700 "$XDG_RUNTIME_DIR"

echo "::group::Start virtual display"
Xvfb "$DISPLAY" -screen 0 640x480x24 -nolisten tcp >"$RUNTIME/xvfb.log" 2>&1 &
XVFB_PID=$!
trap 'kill "${DOOM_PID:-}" "${XVFB_PID:-}" 2>/dev/null || true' EXIT
sleep 1
echo "::endgroup::"

IWAD="$(dpkg -L freedoom | grep -E '/freedoom1\.wad$' | head -n 1 || true)"
if [[ -z "$IWAD" ]]; then
  IWAD="$(dpkg -L freedoom | grep -E '/freedoom2\.wad$' | head -n 1 || true)"
fi
if [[ -z "$IWAD" || ! -f "$IWAD" ]]; then
  echo "Could not locate a Freedoom IWAD" >&2
  dpkg -L freedoom >&2
  exit 1
fi

echo "Using IWAD: $IWAD"

echo "::group::Launch Chocolate Doom"
chocolate-doom \
  -iwad "$IWAD" \
  -warp 1 1 \
  -skill 2 \
  -window \
  -geometry 640x480 \
  -nosound \
  -nomouse \
  -nograbmouse \
  -savedir "$RUNTIME/save" \
  -config "$RUNTIME/config/chocolate-doom.cfg" \
  -extraconfig "$RUNTIME/config/chocolate-doom-extra.cfg" \
  >"$RUNTIME/doom.log" 2>&1 &
DOOM_PID=$!
echo "DOOM PID: $DOOM_PID"
echo "::endgroup::"

WINDOW=""
for _ in $(seq 1 40); do
  if ! kill -0 "$DOOM_PID" 2>/dev/null; then
    echo "Chocolate Doom exited before a window appeared" >&2
    cat "$RUNTIME/doom.log" >&2 || true
    exit 1
  fi

  WINDOW="$(xdotool search --pid "$DOOM_PID" 2>/dev/null | head -n 1 || true)"
  [[ -n "$WINDOW" ]] && break
  sleep 0.25
done

if [[ -z "$WINDOW" ]]; then
  echo "Could not find Chocolate Doom X11 window" >&2
  xwininfo -root -tree >&2 || true
  cat "$RUNTIME/doom.log" >&2 || true
  exit 1
fi

echo "Window: $WINDOW"
xdotool windowmove "$WINDOW" 0 0 || true
xdotool windowsize "$WINDOW" 640 480 || true
xdotool windowfocus "$WINDOW" || true
sleep 1

# Generate visible, deterministic-enough activity in the actual game.
(
  sleep 0.6
  xdotool keydown --window "$WINDOW" Up || true
  sleep 1.8
  xdotool keyup --window "$WINDOW" Up || true

  xdotool keydown --window "$WINDOW" Right || true
  sleep 0.7
  xdotool keyup --window "$WINDOW" Right || true

  xdotool keydown --window "$WINDOW" Up || true
  sleep 1.2
  xdotool keyup --window "$WINDOW" Up || true

  xdotool key --window "$WINDOW" ctrl || true
  sleep 0.3
  xdotool key --window "$WINDOW" ctrl || true
) &
INPUT_PID=$!

echo "::group::Capture frames"
ffmpeg -hide_banner -loglevel warning -y \
  -f x11grab \
  -draw_mouse 0 \
  -framerate 10 \
  -video_size 640x480 \
  -i "$DISPLAY+0,0" \
  -t 5 \
  "$RUNTIME/frames/frame-%03d.png"
wait "$INPUT_PID" || true
echo "::endgroup::"

FRAME_COUNT="$(find "$RUNTIME/frames" -maxdepth 1 -name 'frame-*.png' | wc -l)"
echo "Captured frames: $FRAME_COUNT"
if [[ "$FRAME_COUNT" -lt 20 ]]; then
  echo "Too few captured frames" >&2
  exit 1
fi

echo "::group::Encode GIF"
python "$ROOT/scripts/frames_to_gif.py" "$RUNTIME/frames" "$SITE/doom.gif"
echo "::endgroup::"

if [[ ! -s "$SITE/doom.gif" ]]; then
  echo "GIF was not generated" >&2
  exit 1
fi

echo "Generated $SITE/doom.gif ($(stat -c%s "$SITE/doom.gif") bytes)"
