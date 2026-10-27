# ADR 0001: Use FastAPI for the HTTP layer

- **Status:** Accepted
- **Date:** 2026-10-27

## Context

The service is a small, read-only JSON API whose value is in its pipeline and correctness, not its web framework. It needs request validation, typed responses, OpenAPI docs for designers and tool builders, and a mature test client.

## Decision

Use FastAPI with Pydantic v2 and Uvicorn.

## Consequences

Request and response validation come from type hints, so invalid input is rejected with a consistent 422 before any formula runs. `/docs` gives designers an interactive console with no extra work. The same Pydantic models validate the game data at startup. FastAPI's async features are unused, since every handler is CPU-bound and in-memory; a single Uvicorn worker saturated at about 280 requests per second in the recorded load test (see README), which is far beyond this tool's needs and scales by adding workers or replicas.
