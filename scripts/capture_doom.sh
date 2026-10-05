#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNTIME="$ROOT/runtime"
SITE="$ROOT/site"
COMMANDS_FILE="${COMMANDS_FILE:-}"

mkdir -p "$RUNTIME/frames" "$RUNTIME/save" "$RUNTIME/config" "$SITE"
rm -f "$RUNTIME/frames"/*.png "$SITE/doom.gif" "$RUNTIME/doom.log"

if compgen -G "$ROOT/state/save/*" >/dev/null; then
  cp -a "$ROOT/state/save/." "$RUNTIME/save/"
fi

export DISPLAY=:99
export SDL_VIDEODRIVER=x11
export SDL_RENDER_DRIVER=software
export XDG_RUNTIME_DIR="$RUNTIME/xdg"
mkdir -p "$XDG_RUNTIME_DIR"
chmod 700 "$XDG_RUNTIME_DIR"

Xvfb "$DISPLAY" -screen 0 640x480x24 -nolisten tcp >"$RUNTIME/xvfb.log" 2>&1 &
XVFB_PID=$!
trap 'kill "${DOOM_PID:-}" "${XVFB_PID:-}" 2>/dev/null || true' EXIT
sleep 1

IWAD="$(dpkg -L freedoom | grep -E '/freedoom1\.wad$' | head -n 1 || true)"
if [[ -z "$IWAD" ]]; then
  IWAD="$(dpkg -L freedoom | grep -E '/freedoom2\.wad$' | head -n 1 || true)"
fi
if [[ -z "$IWAD" || ! -f "$IWAD" ]]; then
  echo "Could not locate a Freedoom IWAD" >&2
  exit 1
fi

HAD_SAVE=0
START_ARGS=(-warp 1 1 -skill 2)
if compgen -G "$RUNTIME/save/*.dsg" >/dev/null; then
  HAD_SAVE=1
  START_ARGS=(-loadgame 0)
fi

echo "IWAD: $IWAD"
echo "Persistent save present: $HAD_SAVE"

chocolate-doom \
  -iwad "$IWAD" \
  "${START_ARGS[@]}" \
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

WINDOW=""
for _ in $(seq 1 60); do
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
  exit 1
fi

xdotool windowmove "$WINDOW" 0 0 || true
xdotool windowsize "$WINDOW" 640 480 || true
xdotool windowfocus "$WINDOW" || true
sleep 1

apply_command() {
  local command="$1"
  case "$command" in
    /forward)
      xdotool keydown --window "$WINDOW" Up
      sleep 0.9
      xdotool keyup --window "$WINDOW" Up
      ;;
    /back)
      xdotool keydown --window "$WINDOW" Down
      sleep 0.65
      xdotool keyup --window "$WINDOW" Down
      ;;
    /left)
      xdotool keydown --window "$WINDOW" Left
      sleep 0.55
      xdotool keyup --window "$WINDOW" Left
      ;;
    /right)
      xdotool keydown --window "$WINDOW" Right
      sleep 0.55
      xdotool keyup --window "$WINDOW" Right
      ;;
    /fire)
      xdotool keydown --window "$WINDOW" ctrl
      sleep 0.35
      xdotool keyup --window "$WINDOW" ctrl
      ;;
    /use)
      xdotool key --window "$WINDOW" space
      sleep 0.35
      ;;
    *)
      echo "Ignoring unsupported command: $command" >&2
      ;;
  esac
}

COMMAND_COUNT=0
if [[ -n "$COMMANDS_FILE" && -f "$COMMANDS_FILE" ]]; then
  COMMAND_COUNT="$(python3 - "$COMMANDS_FILE" <<'PY'
import json, sys
p=json.load(open(sys.argv[1], encoding="utf-8"))
print(len(p.get("commands", [])))
PY
)"
fi

ffmpeg -hide_banner -loglevel warning -y \
  -f x11grab \
  -draw_mouse 0 \
  -framerate 10 \
  -video_size 640x480 \
  -i "$DISPLAY+0,0" \
  -t 5 \
  "$RUNTIME/frames/frame-%03d.png" &
FFMPEG_PID=$!

sleep 0.5

if [[ "$COMMAND_COUNT" -gt 0 ]]; then
  while IFS=$'\t' read -r command actor comment_id; do
    echo "Applying $command from @$actor (#$comment_id)"
    apply_command "$command" || true
    sleep 0.15
  done < <(python3 - "$COMMANDS_FILE" <<'PY'
import json, sys
p=json.load(open(sys.argv[1], encoding="utf-8"))
for item in p.get("commands", []):
    print(f"{item['command']}\t{item['actor']}\t{item['id']}")
PY
)
else
  # No synthetic motion: this is an authentic idle game capture.
  echo "No commands supplied; capturing current game state."
fi

wait "$FFMPEG_PID"

FRAME_COUNT="$(find "$RUNTIME/frames" -maxdepth 1 -name 'frame-*.png' | wc -l)"
if [[ "$FRAME_COUNT" -lt 20 ]]; then
  echo "Too few captured frames: $FRAME_COUNT" >&2
  exit 1
fi

python3 "$ROOT/scripts/frames_to_gif.py" "$RUNTIME/frames" "$SITE/doom.gif"

if [[ "$COMMAND_COUNT" -gt 0 ]]; then
  # Persist slot 0. New slots require a description; existing slots retain theirs.
  xdotool key --window "$WINDOW" F2 || true
  sleep 0.35
  xdotool key --window "$WINDOW" Return || true
  sleep 0.25
  if [[ "$HAD_SAVE" -eq 0 ]]; then
    xdotool type --window "$WINDOW" --delay 40 "PROFILE" || true
    xdotool key --window "$WINDOW" Return || true
  else
    xdotool key --window "$WINDOW" Return || true
  fi
  sleep 1

  mkdir -p "$ROOT/state/save"
  SAVE_FILE="$(find "$RUNTIME/save" -maxdepth 1 -type f -name '*.dsg' | head -n 1 || true)"
  if [[ -z "$SAVE_FILE" ]]; then
    echo "Game command succeeded but no save file was produced" >&2
    find "$RUNTIME/save" -maxdepth 1 -type f -print >&2 || true
    exit 1
  fi
  cp "$SAVE_FILE" "$ROOT/state/save/doomsav0.dsg"
  echo "Persisted save: $SAVE_FILE"
fi

test -s "$SITE/doom.gif"
echo "Generated $SITE/doom.gif ($(stat -c%s "$SITE/doom.gif") bytes)"
