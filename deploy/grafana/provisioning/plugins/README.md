# Grafana plugins

Intentionally empty: the dashboard uses only Grafana's built-in Prometheus
datasource and core panels, so no plugins are provisioned.

This folder exists because Grafana logs an error at startup when the
`provisioning/plugins` directory is missing. Grafana only reads `.yaml` and
`.yml` files here, so this README is ignored.
