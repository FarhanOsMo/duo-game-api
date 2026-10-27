from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.api.conftest import assert_error

STATS = "/api/v1/monsters/mon_placeholder_a/stats"
DAMAGE = "/api/v1/battle/damage"


def _damage_body(**overrides: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "ability": "ab_cinder_spit",
        "attacker": {"species": "mon_placeholder_a", "level": 5},
        "defender": {"species": "mon_placeholder_b", "level": 5},
    }
    body.update(overrides)
    return body


GOLDEN = {"fixed_variance": 1.0, "force_hit": True, "force_crit": False}


# --- stats ------------------------------------------------------------------


def test_stats_golden_values(client: TestClient) -> None:
    body = client.get(f"{STATS}?level=5").json()
    assert body["stats"] == {
        "hp": 46, "mp": 15, "attack": 19, "defense": 11, "magic": 14, "speed": 15
    }  # fmt: skip
    brave = client.get(f"{STATS}?level=5&personality=Brave").json()["stats"]
    assert (brave["attack"], brave["speed"]) == (20, 15)


def test_stats_with_potential(client: TestClient) -> None:
    base = client.get(f"{STATS}?level=25").json()["stats"]
    boosted = client.get(f"{STATS}?level=25&potential_attack=15").json()
    assert boosted["stats"]["attack"] == base["attack"] + 15
    assert boosted["potential"]["attack"] == 15


@pytest.mark.parametrize(
    "query",
    ["level=0", "level=51", "level=5&potential_hp=16", "level=5&potential_hp=-1", ""],
)
def test_stats_rejects_out_of_range_input(client: TestClient, query: str) -> None:
    assert_error(client.get(f"{STATS}?{query}"), 422, "validation_error")


def test_stats_unknown_personality_and_monster(client: TestClient) -> None:
    assert_error(client.get(f"{STATS}?level=5&personality=Grumpy"), 422, "invalid_reference")
    assert_error(client.get("/api/v1/monsters/mon_x/stats?level=5"), 404, "not_found")


# --- experience -------------------------------------------------------------


def test_exp_endpoints(client: TestClient) -> None:
    assert client.get("/api/v1/exp/2").json() == {"level": 2, "exp": 12}
    assert client.get("/api/v1/exp/5").json() == {"level": 5, "exp": 271}
    assert client.get("/api/v1/exp/level-for?exp=271").json()["level"] == 5
    assert client.get("/api/v1/exp/level-for?exp=270").json()["level"] == 4
    assert_error(client.get("/api/v1/exp/0"), 422, "validation_error")
    assert_error(client.get("/api/v1/exp/level-for?exp=-1"), 422, "validation_error")


# --- elements ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("attack", "defend", "multiplier"),
    [("Fire", "Water", 0.67), ("Water", "Fire", 1.5), ("Light", "Dark", 1.5)],
)
def test_effectiveness(client: TestClient, attack: str, defend: str, multiplier: float) -> None:
    url = f"/api/v1/elements/effectiveness?attack={attack}&defend={defend}"
    assert client.get(url).json()["multiplier"] == multiplier


def test_effectiveness_unknown_element(client: TestClient) -> None:
    url = "/api/v1/elements/effectiveness?attack=Plasma&defend=Fire"
    assert_error(client.get(url), 404, "not_found")


# --- damage -----------------------------------------------------------------


def test_damage_golden_value(client: TestClient) -> None:
    body = client.post(DAMAGE, json=_damage_body(**GOLDEN)).json()
    assert body["damage"] == 6
    assert (body["hit"], body["crit"], body["effectiveness"]) == (True, False, 0.67)
    assert body["breakdown"]["defense_stat"] == pytest.approx(15.5)


def test_damage_same_seed_same_result(client: TestClient) -> None:
    first = client.post(DAMAGE, json=_damage_body(seed=1234)).json()
    second = client.post(DAMAGE, json=_damage_body(seed=1234)).json()
    assert first == second


def test_damage_forced_miss(client: TestClient) -> None:
    body = client.post(DAMAGE, json=_damage_body(force_hit=False)).json()
    assert (body["damage"], body["hit"], body["crit"]) == (0, False, False)


def test_damage_with_status_stages_and_defending(client: TestClient) -> None:
    plain = client.post(DAMAGE, json=_damage_body(ability="ab_ram", **GOLDEN)).json()
    burned = _damage_body(ability="ab_ram", **GOLDEN)
    burned["attacker"]["status"] = "Burn"
    burned_body = client.post(DAMAGE, json=burned).json()
    assert burned_body["breakdown"]["attack_stat"] == pytest.approx(
        plain["breakdown"]["attack_stat"] * 0.8
    )
    guarded = _damage_body(**GOLDEN)
    guarded["defender"]["defending"] = True
    guarded["attacker"]["stages"] = {"magic": 2}
    guarded_body = client.post(DAMAGE, json=guarded).json()
    assert guarded_body["breakdown"]["defend_multiplier"] == 0.5


def test_damage_increments_metric(client: TestClient) -> None:
    def count() -> float:
        for line in client.get("/metrics").text.splitlines():
            if line.startswith('damage_calculations_total{category="Magical",outcome="hit"}'):
                return float(line.rsplit(" ", 1)[1])
        return 0.0

    before = count()
    client.post(DAMAGE, json=_damage_body(**GOLDEN))
    assert count() == before + 1


@pytest.mark.parametrize(
    "ability", ["ab_harden", "ess_ab_soothing_rain", "ess_ab_verdant_sense"]
)  # support (power 0), heal, field ability
def test_damage_rejects_non_damaging_abilities(client: TestClient, ability: str) -> None:
    assert_error(
        client.post(DAMAGE, json=_damage_body(ability=ability)), 422, "unsupported_ability"
    )


@pytest.mark.parametrize(
    ("change", "code"),
    [
        ({"ability": "ab_missing"}, "invalid_reference"),
        ({"attacker": {"species": "mon_placeholder_a", "level": 5, "status": "Freeze"}},
         "invalid_reference"),
        ({"attacker": {"species": "mon_placeholder_a", "level": 5, "stages": {"luck": 1}}},
         "validation_error"),
        ({"attacker": {"species": "mon_placeholder_a", "level": 99}}, "validation_error"),
        ({"unexpected": True}, "validation_error"),
        ({"fixed_variance": 0}, "validation_error"),
    ],
)  # fmt: skip
def test_damage_rejects_bad_requests(client: TestClient, change: dict[str, Any], code: str) -> None:
    assert_error(client.post(DAMAGE, json=_damage_body(**change)), 422, code)


def test_damage_unknown_species_is_404(client: TestClient) -> None:
    body = _damage_body()
    body["defender"]["species"] = "mon_missing"
    assert_error(client.post(DAMAGE, json=body), 404, "not_found")
