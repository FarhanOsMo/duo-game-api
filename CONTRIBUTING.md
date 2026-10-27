# Contributing

This repository is the single source of truth for the Duo Game Data API: code,
game data, dashboards, alert rules and environment configuration all change
the same way, through a pull request that passes CI. Nothing is changed by
hand on a running system.

## Branching: trunk-based development

- `main` is always releasable and is protected (see below).
- Work happens on short-lived branches cut from `main`, merged within a day or
  two. Long-lived branches drift from `main` and make merges risky.
- Branch names describe the change: `feat/item-endpoint-filters`,
  `fix/stage-clamp`, `data/balance-pass-ember-pepper`, `ci/cache-trivy-db`.
- Releases are tags on `main` (`v1.2.0`), not release branches.

## Commit messages: Conventional Commits

```
<type>(<scope>): <summary in the imperative>
```

Types used here: `feat`, `fix`, `docs`, `test`, `refactor`, `ci`, `build`,
`chore`. Examples:

```
feat(api): add rarity filter to /monsters
fix(domain): clamp stat stages before computing the multiplier
chore(data): import balance pass from Studio export
```

The type makes the history scannable and maps directly to the changelog.

## Changing game data

Game data is never edited by hand. Export it from Roblox Studio and import it
with one command; see [docs/DATA_SYNC.md](docs/DATA_SYNC.md). Commit the data
files together with the regenerated `data/manifest.json`.

## Before you open a pull request

```bash
pip install -r requirements-dev.txt
pre-commit install          # once: runs lint, secret scan and data checks on every commit
make check                  # or run the commands below
```

Without `make`:

```bash
ruff check . && ruff format --check .
mypy app scripts tests
python scripts/validate_data.py
python scripts/build_manifest.py --check
pytest --cov
```

## Required status checks

Pull requests into `main` must pass every CI job before merging:

| Check | What it gates |
|---|---|
| `Lint, types, data and tests` | ruff, mypy strict, data validation, manifest freshness, tests with the coverage threshold |
| `Dependency audit and secret scan` | pip-audit, gitleaks over the full history |
| `Lint workflows (actionlint)` | GitHub Actions syntax and shell scripts |
| `Build, scan and smoke test image` | Docker build, Trivy (fixable HIGH/CRITICAL), Compose smoke test |

While the project has a single maintainer, GitHub does not allow approving your own
pull request, so the required approval count is 0. Raise it to 1, with code owner
review, as soon as a second maintainer joins.

## Branch protection (repository settings)

Settings > Branches > Add branch ruleset (or classic rule) for `main`:

1. Require a pull request before merging (0 approvals while solo; 1 with code owner
   review once there is a second maintainer). Require conversations to be resolved.
2. Require status checks to pass: select the four checks above. Require
   branches to be up to date before merging.
3. Block force pushes and block deletions.
