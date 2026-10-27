# ADR 0002: Stateless service with no database

- **Status:** Accepted
- **Date:** 2026-10-27

## Context

All game data is exported from Roblox Studio as eleven JSON files totalling about 25 KB. The API never writes anything. A database would add a server to run, migrations, credentials, backups and a cost line, none of which serves a read-only workload this small.

## Decision

Load the data into immutable in-memory models at startup. Keep no state between requests.

## Consequences

Any number of replicas are interchangeable, so scaling and rolling restarts are trivial and there is nothing to back up. Rollback is redeploying the previous image. The data version is a property of the image, not of a mutable store. If the API ever needed to accept writes (for example telemetry), that would be a separate service with its own storage, not a change to this one.
