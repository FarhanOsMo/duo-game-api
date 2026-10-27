# Reflection

This project turned the course's ideas into one working system, and building it changed how I think about each of them.

**Pipeline stages and quality gates.** The CI pipeline is ordered so cheap, fast checks fail first: lint, strict typing, data validation and the manifest check run before tests, and the image is only built once code and dependencies pass. Each stage answers one question, so a red build says exactly what is wrong. The release workflow reuses the CI workflow rather than copying it, so a tag can never skip a gate.

**Shift-left security.** gitleaks runs in a pre-commit hook and again over the full history in CI, pip-audit checks dependencies, and Trivy scans the built image before it can be published. The Trivy run taught me that policy matters as much as tooling: the Debian base image carried 44 high or critical CVEs with no available fix, so the gate fails only on fixable findings while still printing everything.

**Repeatability and idempotent provisioning.** One command starts the whole stack, and the bootstrap scripts can run any number of times without changing an existing `.env` or breaking a running stack. Grafana's datasource and dashboard are provisioned from files, so a fresh machine produces the identical environment with no manual clicking.

**Container best practices.** The image is multi-stage, pinned by digest, runs as a fixed non-root user, has a healthcheck, and runs with a read-only filesystem and all Linux capabilities dropped. The data is baked in, so one image is exactly one code version plus one data version.

**Observability and alerting on symptoms.** Alerts fire on what a user would notice (the API being down, a rising 5xx ratio, slow p95 latency) rather than on causes like CPU. Because alert rules are code, they have unit tests that prove they fire and stay quiet when they should. The load test showed why measuring beats guessing: p95 was under 5 ms at light load but about 97 ms at 280 requests per second, because a single worker was queueing requests.

**GitOps and environment promotion.** The repository is the source of truth for code, data, dashboards, alerts and environment configuration. The release pipeline builds once and promotes the same image digest from staging to a production environment that requires human approval.

**Rollback.** Because the service is stateless and every release is an immutable, versioned image with its data manifest attached, rolling back is redeploying the previous tag, and a bad data change is a `git revert`.

## Improvement plan (none of this is implemented yet)

1. **Automate the Studio export.** The manual copy is the biggest source of friction and risk. A Studio plugin could post the export to a local receiver that opens the pull request automatically.
2. **Provision real infrastructure with Terraform.** It is the prerequisite for everything below, and it makes the cluster itself reviewable and reproducible.
3. **Deploy to managed Kubernetes with Argo CD or Flux.** This replaces Compose rehearsals with true GitOps reconciliation, and `/health` and `/ready` already map to probes.
4. **Define SLOs with error budgets.** The latency and error metrics exist; turning them into SLOs gives the team an objective rule for when to slow releases.
5. **Canary releases.** With SLOs in place, Argo Rollouts can shift traffic gradually and roll back automatically on the same signals.
6. **Signed images and SBOMs.** Cosign signatures and an SBOM per release extend supply-chain trust past scanning.
7. **OpenTelemetry tracing.** It becomes valuable once there is more than one service to follow a request across.
