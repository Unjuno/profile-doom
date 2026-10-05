# profile-doom

A GitHub-profile rendering experiment.

The repository is split into two layers:

- **GitHub Pages** renders the current visual output.
- **The profile README** will embed that output as its "screen".

Current milestone: prove the full render path before wiring a real DOOM-compatible engine and shared GitHub input.

## Render pipeline

```text
state/state.json
      ↓
scripts/render_profile.py
      ↓
site/doom.gif + site/status.svg
      ↓
GitHub Pages
      ↓
github.com/Unjuno profile README
```

## Pages output

After the Pages workflow succeeds:

- Site: https://unjuno.github.io/profile-doom/
- Animated screen: https://unjuno.github.io/profile-doom/doom.gif
- Status card: https://unjuno.github.io/profile-doom/status.svg

## Next stages

1. Validate animated GIF rendering on the actual GitHub profile.
2. Replace the synthetic boot renderer with a DOOM-compatible runtime using freely redistributable game data.
3. Add a single shared game state.
4. Use GitHub Issues / comments as the controller.
5. Render each accepted input into the next profile frame/replay.

The synthetic animation in the first milestone is intentionally not a fake claim that DOOM is already running. It is only an end-to-end display test.
