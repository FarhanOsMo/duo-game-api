# ADR 0006: Trivy and gitleaks as CI gates

- **Status:** Accepted
- **Date:** 2026-10-27

## Context

A public portfolio repo must never leak a secret, and a container image is only as safe as its base image and dependencies. Security found after release is expensive.

## Decision

Run gitleaks over the full git history (CI and pre-commit), pip-audit over pinned dependencies, and Trivy over the built image before it can be published. Trivy fails the build on HIGH or CRITICAL findings that have a fix available. Third-party actions are pinned to commit SHAs, workflow permissions are least privilege, and Dependabot proposes upgrades.

## Consequences

Problems are caught at commit or pull-request time instead of in production. The fixable-only policy keeps the gate actionable: at the time of writing the Debian base image carried 44 HIGH/CRITICAL CVEs with no fixed package, which would otherwise block every build while nothing in this repo could resolve them. They remain visible in the CI log, and a minimal base image is on the improvement plan.
