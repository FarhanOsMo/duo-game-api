"""Prometheus metrics, exposed at GET /metrics for Prometheus to scrape.

Pull-based scraping means the API needs no knowledge of where metrics go: no
agent, no credentials, no outbound network. Labels use the route template
(/api/v1/monsters/{monster_id}) rather than the raw path so cardinality stays
bounded no matter what ids clients send.

Metrics are module-level singletons because prometheus_client registers them
in a process-wide registry; creating them per app instance would fail on the
second instance (as tests do).
"""

from prometheus_client import Counter, Gauge, Histogram

REQUESTS = Counter(
    "http_requests_total",
    "HTTP requests handled, by method, route template and status code.",
    ["method", "route", "status"],
)
LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds, by method, route template and status code.",
    ["method", "route", "status"],
    # Tuned for a sub-10ms in-memory API: fine buckets low, a few for slow outliers.
    buckets=(0.001, 0.0025, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5),
)
IN_FLIGHT = Gauge("http_requests_in_flight", "HTTP requests currently being handled.")
DAMAGE_CALCULATIONS = Counter(
    "damage_calculations_total",
    "Damage calculations served, by ability category and outcome (hit, crit, miss).",
    ["category", "outcome"],
)
DATA_VERSION = Gauge(
    "data_version_info",
    "Always 1; labels identify the game data and build this process is serving.",
    ["data_version", "app_version", "git_sha"],
)
