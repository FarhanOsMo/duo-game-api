# ADR 0003: Pure domain functions with injected, seeded randomness

- **Status:** Accepted
- **Date:** 2026-10-27

## Context

The API re-implements the game's Luau formulas, and parity with the game is the entire point. Damage involves three random rolls (hit, crit, variance). If formulas read globals or a hidden random generator, results could not be reproduced or tested exactly.

## Decision

Formulas in `app/domain` are pure functions with no I/O. Every constant arrives as an argument taken from `config.json`, and randomness is injected as a function returning a float in [0, 1), matching Lua's `math.random()`. The API passes `random.Random(seed).random`, and the roll order (hit, then crit, then variance) is fixed and documented.

## Consequences

Golden values from the game are plain unit tests with no mocking. A designer can attach a seed to a bug report and get the identical result. Rounding uses `math.floor(x + 0.5)` exactly as Lua does, never Python's banker's `round()`. A balance change in `config.json` needs no code change; a formula change in the game needs a matching code change here, which the golden-value tests catch.
