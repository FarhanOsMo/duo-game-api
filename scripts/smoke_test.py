"""Smoke test a running deployment: is it up, ready, correct and observable?

Used by CI after `docker compose up`, by the bootstrap scripts, and by hand.
It waits for readiness (containers take a few seconds to start), then checks
one known computation against the golden value so a deployment that is "up"
but serving wrong numbers still fails.

Usage: python scripts/smoke_test.py [--base-url URL] [--timeout SECONDS]
Exit code 0 when every check passes, 1 otherwise. Standard library only.
"""

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from typing import Any


def _get(url: str) -> tuple[int, str]:
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            return int(resp.status), resp.read().decode()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode()


def _post_json(url: str, body: dict[str, Any]) -> tuple[int, Any]:
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=5) as resp:
        return int(resp.status), json.load(resp)


def wait_until_ready(base: str, timeout: float) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            if _get(f"{base}/ready")[0] == 200:
                return True
        except (urllib.error.URLError, ConnectionError, TimeoutError):
            pass
        time.sleep(1)
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke test a running API")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--timeout", type=float, default=60, help="seconds to wait for /ready")
    args = parser.parse_args()
    base = args.base_url.rstrip("/")

    if not wait_until_ready(base, args.timeout):
        print(f"FAIL {base}/ready did not return 200 within {args.timeout:g}s", file=sys.stderr)
        return 1

    failures: list[str] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        print(f"{'PASS' if ok else 'FAIL'} {name}{f' ({detail})' if detail else ''}")
        if not ok:
            failures.append(name)

    status, body = _get(f"{base}/health")
    check("GET /health", status == 200 and json.loads(body) == {"status": "ok"}, str(status))

    status, body = _get(f"{base}/ready")
    check("GET /ready", status == 200, json.loads(body).get("data_version", ""))

    status, body = _get(f"{base}/api/v1/monsters")
    check("GET /api/v1/monsters", status == 200 and json.loads(body)["count"] > 0, str(status))

    # Golden value from the test suite: Cinder Spit, L5 vs L5, fixed rolls -> 6.
    status, result = _post_json(
        f"{base}/api/v1/battle/damage",
        {
            "ability": "ab_cinder_spit",
            "attacker": {"species": "mon_placeholder_a", "level": 5},
            "defender": {"species": "mon_placeholder_b", "level": 5},
            "fixed_variance": 1.0,
            "force_hit": True,
            "force_crit": False,
        },
    )
    check("POST /api/v1/battle/damage", status == 200 and result["damage"] == 6, str(result))

    status, body = _get(f"{base}/metrics")
    check(
        "GET /metrics",
        status == 200 and "http_requests_total" in body and "data_version_info" in body,
        str(status),
    )

    if failures:
        print(f"{len(failures)} smoke check(s) failed", file=sys.stderr)
        return 1
    print("All smoke checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
