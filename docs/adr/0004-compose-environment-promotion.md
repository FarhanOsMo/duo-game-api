# ADR 0004: Environment promotion with Compose override files

- **Status:** Accepted
- **Date:** 2026-10-27

## Context

The course goal is a realistic dev, staging, production flow, and the constraint is zero cost, so there is no cloud cluster. Rebuilding the image per environment would mean production runs something that was never tested.

## Decision

Build one image. `docker-compose.yml` is the dev environment; `compose.staging.yml` and `compose.prod.yml` override only the env file (and, for prod, resource limits and a released image reference). Promotion means running the same image digest with a different override.

## Consequences

What was tested is exactly what ships: the release pipeline promotes a GHCR image by digest. Verified locally: the same image reported `dev`, `staging` and `prod` from `/api/v1/meta` with an identical git SHA and data version. The trade-off is that staging and production here are rehearsals on one machine or CI runner; [DEPLOYMENT.md](../DEPLOYMENT.md) describes the same flow on a real cluster.
