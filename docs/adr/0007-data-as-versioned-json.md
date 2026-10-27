# ADR 0007: Game data lives in the repo as versioned JSON

- **Status:** Accepted
- **Date:** 2026-10-27

## Context

The game's balance data (monsters, abilities, elements, config) changes often. Content changes cause as many live-service incidents as code changes, so they deserve the same review and validation.

## Decision

Commit the exported JSON files to `data/`, validate them on every pull request (schema plus cross-file references, mirroring the game's boot-time checks), and bake them into the image.

## Consequences

Every data change is a reviewable diff (the exporter sorts keys, so diffs are minimal) with a full history and an easy revert. A broken export fails CI with the file and entry id named, before it can be deployed. One image equals one code version plus one data version, visible at `/api/v1/meta` and in the `data_version_info` metric. A data update requires a new image, which is the price of that traceability.
