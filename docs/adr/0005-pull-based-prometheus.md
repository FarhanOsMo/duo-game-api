# ADR 0005: Pull-based Prometheus metrics

- **Status:** Accepted
- **Date:** 2026-10-27

## Context

The service needs request rate, error rate and latency (the golden signals) plus domain metrics, viewable on a dashboard and alertable, with no paid service.

## Decision

Expose Prometheus metrics at `/metrics` and let Prometheus scrape them. Label requests by route template, not raw path. Alert in Prometheus on symptoms (down, 5xx ratio, p95 latency), with alert rules unit-tested by `promtool`. Grafana only visualises, from a provisioned datasource and a dashboard committed as JSON.

## Consequences

The API needs no credentials, agent or outbound network to be observable. Route-template labels keep cardinality bounded regardless of the ids clients send. Prometheus's `up` metric gives "API down" detection for free, which a push model cannot. Dashboards and alerts are versioned and reviewed like code. There is no Alertmanager yet, so alerts are visible in Prometheus but not routed to anyone; that is listed as future work.
