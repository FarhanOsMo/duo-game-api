"""Locust load test for the Duo Game Data API.

Models the realistic workload: mostly catalogue reads, a steady share of stat
and damage calculations, and a health probe. Each simulated user waits a
little between requests, like a tool or Studio session would.

Run against the local stack (see README "Outcomes or Metrics" for the recorded run):
  locust -f loadtest/locustfile.py --headless --host http://localhost:8000 \
         --users 50 --spawn-rate 10 --run-time 60s --csv loadtest/results/run --only-summary
"""

import random

from locust import HttpUser, between, task

MONSTERS = ["mon_placeholder_a", "mon_placeholder_b", "mon_placeholder_c"]
ATTACKS = ["ab_ram", "ab_cinder_spit", "ab_tide_pulse", "ab_thorn_lash"]
PERSONALITIES = ["Brave", "Curious", "Lazy", "Timid"]


class GameToolUser(HttpUser):
    wait_time = between(0.05, 0.2)

    @task(5)
    def get_monster(self) -> None:
        monster = random.choice(MONSTERS)
        self.client.get(f"/api/v1/monsters/{monster}", name="/api/v1/monsters/{id}")

    @task(2)
    def list_monsters(self) -> None:
        self.client.get("/api/v1/monsters")

    @task(2)
    def elements(self) -> None:
        self.client.get("/api/v1/elements")

    @task(4)
    def stats(self) -> None:
        monster = random.choice(MONSTERS)
        level = random.randint(1, 50)
        personality = random.choice(PERSONALITIES)
        self.client.get(
            f"/api/v1/monsters/{monster}/stats?level={level}&personality={personality}",
            name="/api/v1/monsters/{id}/stats",
        )

    @task(3)
    def damage(self) -> None:
        self.client.post(
            "/api/v1/battle/damage",
            json={
                "ability": random.choice(ATTACKS),
                "attacker": {"species": random.choice(MONSTERS), "level": random.randint(1, 50)},
                "defender": {"species": random.choice(MONSTERS), "level": random.randint(1, 50)},
            },
        )

    @task(1)
    def health(self) -> None:
        self.client.get("/health")
