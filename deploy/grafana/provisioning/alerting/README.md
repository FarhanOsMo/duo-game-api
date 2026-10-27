# Grafana alerting

Intentionally empty. Alert rules live in Prometheus
(`deploy/prometheus/alerts.yml`, unit-tested by `deploy/prometheus/tests/`),
so there is a single source of truth for alerting. Grafana only visualises.

This folder exists because Grafana logs an error at startup when the
`provisioning/alerting` directory is missing. Grafana only reads `.yaml` and
`.yml` files here, so this README is ignored.
