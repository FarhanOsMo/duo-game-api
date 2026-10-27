## What and why

<!-- One or two sentences: what changes, and the problem it solves. -->

## Type of change

- [ ] Feature (`feat`)
- [ ] Fix (`fix`)
- [ ] Game data import (`chore(data)`)
- [ ] CI, build or infrastructure (`ci`, `build`)
- [ ] Docs or tests only

## Checklist

- [ ] `make check` (or the equivalent commands in CONTRIBUTING.md) passes locally
- [ ] Tests added or updated for behaviour changes
- [ ] If a game formula changed: golden-value tests updated from the game's Luau, not from this code
- [ ] If game data changed: imported with `scripts/import_studio_export.py`, `data/manifest.json` regenerated, no hand edits
- [ ] If dashboards, alerts or Compose files changed: verified against the running stack
- [ ] Docs and `CHANGELOG.md` updated where relevant
- [ ] No secrets, tokens or `.env` files included
