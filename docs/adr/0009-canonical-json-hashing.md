# ADR 0009: Canonical-JSON hashing for the data version

- **Status:** Accepted
- **Date:** 2026-10-27

## Context

The data version must change when the data's meaning changes and only then. Data arrives by copy and paste, which can alter indentation, trailing newlines and line endings without changing any value.

## Decision

Hash canonical JSON: parse each file, re-serialise with sorted keys and fixed separators, hash per file, then hash the sorted list of (file name, file hash) pairs. Write the result to `data/manifest.json` with no timestamp, and fail CI if the committed manifest differs from a fresh build.

## Consequences

Whitespace, key order and CRLF/LF noise never produce a new version (tested), while any value change does. Because the manifest is a pure function of the data, CI can regenerate and compare it. The data version shown by the API, the metric label and the release asset all agree. A change from `1` to `1.0` would count as a change, which is acceptable because the exporter writes whole numbers consistently.
