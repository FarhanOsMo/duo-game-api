"""Send a realistic, seeded mix of requests so the Grafana dashboard has data.

The mix mirrors how designers and tools would use the API: mostly reads,
a steady share of stat and damage calculations, and a few bad requests
(unknown ids, out-of-range levels) so the 4xx panels are not empty. The seed
makes the exact sequence reproducible. Uses only the standard library so it
runs anywhere Python does.

Usage: python scripts/generate_traffic.py [--base-url URL] [--duration SECONDS] [--rps N]
"""

import argparse
import json
import random
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from collections.abc import Callable

Request = tuple[str, str, dict[str, object] | None]


def _catalog(base: str) -> tuple[list[str], list[str], list[str]]:
    def ids(path: str) -> list[str]:
        with urllib.request.urlopen(f"{base}/api/v1/{path}", timeout=5) as resp:
            return [item["id"] for item in json.load(resp)["items"]]

    monsters = ids("monsters")
    abilities = [
        a["id"]
        for a in json.load(urllib.request.urlopen(f"{base}/api/v1/abilities", timeout=5))["items"]
        if a.get("category") in ("Physical", "Magical") and a.get("power", 0) > 0
    ]
    return monsters, abilities, ids("personalities")


def build_mix(rng: random.Random, base: str) -> list[tuple[int, Callable[[], Request]]]:
    monsters, abilities, personalities = _catalog(base)

    def side() -> dict[str, object]:
        return {"species": rng.choice(monsters), "level": rng.randint(1, 50)}

    return [
        (25, lambda: ("GET", f"/api/v1/monsters/{rng.choice(monsters)}", None)),
        (10, lambda: ("GET", "/api/v1/monsters", None)),
        (8, lambda: ("GET", "/api/v1/abilities", None)),
        (6, lambda: ("GET", "/api/v1/elements", None)),
        (5, lambda: ("GET", "/api/v1/items?category=Treat", None)),
        (
            20,
            lambda: (
                "GET",
                f"/api/v1/monsters/{rng.choice(monsters)}/stats?level={rng.randint(1, 50)}"
                f"&personality={rng.choice(personalities)}",
                None,
            ),
        ),
        (
            15,
            lambda: (
                "POST",
                "/api/v1/battle/damage",
                {"ability": rng.choice(abilities), "attacker": side(), "defender": side()},
            ),
        ),
        (5, lambda: ("GET", f"/api/v1/exp/{rng.randint(1, 50)}", None)),
        (3, lambda: ("GET", "/api/v1/monsters/mon_does_not_exist", None)),
        (3, lambda: ("GET", f"/api/v1/monsters/{rng.choice(monsters)}/stats?level=99", None)),
    ]


def send(base: str, method: str, path: str, body: dict[str, object] | None) -> int:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(f"{base}{path}", data=data, method=method)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return int(resp.status)
    except urllib.error.HTTPError as exc:
        return exc.code


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate dashboard traffic")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--duration", type=float, default=60, help="seconds to run")
    parser.add_argument("--rps", type=float, default=20, help="target requests per second")
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()

    rng = random.Random(args.seed)
    try:
        mix = build_mix(rng, args.base_url)
    except urllib.error.URLError as exc:
        print(f"FAIL cannot reach {args.base_url}: {exc.reason}", file=sys.stderr)
        return 1
    weights = [w for w, _ in mix]
    makers = [m for _, m in mix]

    statuses: Counter[int] = Counter()
    deadline = time.monotonic() + args.duration
    interval = 1 / args.rps
    while time.monotonic() < deadline:
        started = time.monotonic()
        method, path, body = rng.choices(makers, weights)[0]()
        statuses[send(args.base_url, method, path, body)] += 1
        time.sleep(max(0.0, interval - (time.monotonic() - started)))

    total = sum(statuses.values())
    summary = ", ".join(f"{code}: {n}" for code, n in sorted(statuses.items()))
    print(f"Sent {total} requests in {args.duration:g}s ({summary})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
