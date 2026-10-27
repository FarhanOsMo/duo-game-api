# ADR 0008: A manual Studio export step instead of live sync

- **Status:** Accepted
- **Date:** 2026-10-27

## Context

The data originates in Roblox Studio ModuleScripts. Live Roblox servers cannot reach `localhost`, and Luau in Studio cannot write files to disk.

## Decision

Keep a deliberate, human-triggered export: run `tools/export_game_data.lua` in Studio, copy the Output window, and run `scripts/import_studio_export.py`, which parses all eleven files from one paste, verifies each against the exporter's own character counts, and refuses to write anything if the copy is incomplete. The change then goes through a pull request.

## Consequences

The API never depends on Studio being open and can never change the game. Every data change is intentional and reviewed. The cost is a manual step and the possibility of the API lagging the game; `/api/v1/meta` shows which data version is live. Automating the export (a Studio plugin posting to a local receiver that opens the pull request) is the first item on the improvement plan.
