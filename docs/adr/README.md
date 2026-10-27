# Architecture decision records

Short records of the decisions that shape this project: the context, the choice, and what it costs.

| ADR | Decision |
|---|---|
| [0001](0001-fastapi.md) | Use FastAPI for the HTTP layer |
| [0002](0002-stateless-no-database.md) | Stateless service with no database |
| [0003](0003-pure-domain-seeded-rng.md) | Pure domain functions with injected, seeded randomness |
| [0004](0004-compose-environment-promotion.md) | Environment promotion with Compose override files |
| [0005](0005-pull-based-prometheus.md) | Pull-based Prometheus metrics |
| [0006](0006-shift-left-security.md) | Trivy and gitleaks as CI gates |
| [0007](0007-data-as-versioned-json.md) | Game data lives in the repo as versioned JSON |
| [0008](0008-manual-export-instead-of-live-sync.md) | A manual Studio export step instead of live sync |
| [0009](0009-canonical-json-hashing.md) | Canonical-JSON hashing for the data version |
