# profile-doom

A shared DOOM-compatible game whose display is rendered by GitHub Actions for use inside a GitHub profile README.

The game runtime is **Chocolate Doom + Freedoom**. The commercial DOOM WAD is not stored in this repository.

## Live

- Display: https://unjuno.github.io/profile-doom/
- GIF: https://unjuno.github.io/profile-doom/doom.gif
- Controller: https://github.com/Unjuno/profile-doom/issues/1

## Play

Open the controller issue and post exactly one command per comment:

```text
/forward
/back
/left
/right
/fire
/use
```

Every accepted command is applied to the same persistent game save.

## Architecture

```text
GitHub Issue #1 comment
        ↓
collect_commands.py
        ↓
Chocolate Doom + Freedoom
        ↓
persistent doomsav0.dsg
        ↓
Xvfb + ffmpeg
        ↓
animated GIF
        ↓
GitHub Pages
        ↓
GitHub profile README
```

GitHub is used as the whole control plane:

- **Issue comments** — input
- **Actions** — execution
- **repository state** — persistent save
- **Pages** — rendered display
- **profile README** — final screen

## Verified behavior

The pipeline has been tested across consecutive commands:

1. a first command created and persisted a real Chocolate Doom save;
2. a second workflow loaded that save, applied the next command, produced a new save, rendered a new GIF, and deployed it.

The game therefore continues from shared state rather than restarting for every input.

## Files

```text
.github/workflows/
  pages.yml       current-state render/deploy
  play.yml        Issue-driven shared game loop

scripts/
  capture_doom.sh
  collect_commands.py
  frames_to_gif.py
  render_status.py
  update_game_state.py

state/
  game.json
  save/doomsav0.dsg

site/
  index.html
  doom.gif        generated during Actions
  status.svg      generated during Actions
```
