# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [1.0.0] - 2026-10-27

### Added

- Read-only API for the Lanternfall game's exported data: monsters, abilities,
  items, elements (with the full effectiveness matrix), personalities, config.
- Re-implemented game formulas: stats at a level, EXP curve, element
  effectiveness and seeded single-hit damage, verified against golden values.
- Fail-fast validation of all eleven data files with cross-file reference
  checks, `scripts/validate_data.py`, and broken-data fixtures for each rule.
- Canonical-JSON data manifest and a one-paste Studio import script.
- Operational endpoints `/health`, `/ready`, `/metrics` and `/api/v1/meta`,
  structured JSON logs with request ids, consistent error bodies.
- Multi-stage, non-root Docker image; Compose stack with Prometheus and
  Grafana; dev, staging and prod-like overrides.
- Prometheus alert rules with promtool unit tests; provisioned Grafana
  dashboard.
- GitHub Actions CI (quality, security, image scan, smoke test) and a release
  pipeline publishing to GHCR with staging and an approval-gated production.
- Locust load test, traffic generator, bootstrap scripts, ADRs and docs.
