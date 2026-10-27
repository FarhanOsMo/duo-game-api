"""Behaviour of the pure formulas beyond the golden values."""

import random
from collections.abc import Callable
from typing import Any

import pytest

from app.domain.damage import Attack, Combatant, DamageRules, calculate_damage
from app.domain.elements import ElementChart, effectiveness_matrix, get_multiplier
from app.domain.stats import (
    StageRules,
    exp_for_level,
    level_for_exp,
    stage_multiplier,
    stat_at_level,
)

STAGES = StageRules(min=-3, max=3, step=0.25)
RULES = DamageRules(
    attack_weight=0.9,
    defense_weight=0.35,
    power_scale=30,
    crit_chance=0.0625,
    crit_multiplier=1.5,
    defend_multiplier=0.5,
    magic_defense_blend=0.5,
    variance=(0.85, 1.0),
    stages=STAGES,
)
CHART = ElementChart(
    strong_against={"Fire": ["Nature"], "Water": ["Fire"], "Nature": [], "Neutral": []},
    strong=1.5,
    resisted=0.67,
    neutral=1.0,
)
STATS = {"hp": 40, "mp": 15, "attack": 20, "defense": 12, "magic": 15, "speed": 14}


class ScriptedRng:
    """Returns pre-set rolls in order, so tests can assert the RNG call order."""

    def __init__(self, *rolls: float) -> None:
        self.rolls = list(rolls)
        self.calls = 0

    def __call__(self) -> float:
        self.calls += 1
        return self.rolls.pop(0)


def _hit(attack: Attack, rng: Callable[[], float], **kwargs: Any):
    return calculate_damage(
        Combatant(STATS, "Fire"), Combatant(STATS, "Nature"), attack, RULES, CHART, rng, **kwargs
    )


# --- stats and experience -------------------------------------------------


def test_stat_floors_instead_of_banker_rounding() -> None:
    # 10 * (1 + 0.35 * 1) = 13.5: Lua's math.floor gives 13, Python's round() would give 14.
    assert stat_at_level(10, 0.35, 2) == 13


def test_stat_is_at_least_one() -> None:
    assert stat_at_level(1, 0, 1, personality_mult=0.5) == 1


def test_potential_adds_level_scaled_bonus() -> None:
    assert stat_at_level(10, 0, 25, potential=15) == 10 + 15


def test_exp_for_level_clamps_out_of_range_levels() -> None:
    assert exp_for_level(0, 12, 2.25, 50) == 0
    assert exp_for_level(99, 12, 2.25, 50) == exp_for_level(50, 12, 2.25, 50)


@pytest.mark.parametrize("level", [1, 2, 5, 17, 49, 50])
def test_level_for_exp_inverts_exp_for_level(level: int) -> None:
    exp = exp_for_level(level, 12, 2.25, 50)
    assert level_for_exp(exp, 12, 2.25, 50) == level
    if level > 1:
        assert level_for_exp(exp - 1, 12, 2.25, 50) == level - 1


def test_level_for_exp_caps_at_max_level() -> None:
    assert level_for_exp(10**9, 12, 2.25, 50) == 50


def test_stage_multiplier_clamps() -> None:
    assert stage_multiplier(10, STAGES) == stage_multiplier(3, STAGES)
    assert stage_multiplier(-10, STAGES) == stage_multiplier(-3, STAGES)


# --- elements ---------------------------------------------------------------


def test_unknown_element_is_neutral() -> None:
    assert get_multiplier(CHART, "Plasma", "Fire") == 1.0
    assert get_multiplier(CHART, "Fire", "Plasma") == 1.0


def test_light_and_dark_hit_hard_even_when_resisted() -> None:
    # Synthetic one-way chart: only the special case can make Light -> Dark strong.
    chart = ElementChart({"Light": [], "Dark": ["Light"], "Fire": ["Ice"], "Ice": []}, 1.5, 0.67, 1)
    assert get_multiplier(chart, "Light", "Dark") == 1.5
    assert get_multiplier(chart, "Ice", "Fire") == 0.67


def test_matrix_covers_every_pair() -> None:
    matrix = effectiveness_matrix(CHART)
    assert set(matrix) == set(CHART.strong_against)
    assert matrix["Fire"]["Nature"] == 1.5
    assert matrix["Fire"]["Water"] == 0.67


# --- damage -----------------------------------------------------------------


def test_rng_order_is_hit_then_crit_then_variance() -> None:
    # hit roll 0.5 (<= 0.95 hits), crit roll 0.01 (< 0.0625 crits), variance roll 0.0 -> 0.85.
    rng = ScriptedRng(0.5, 0.01, 0.0)
    result = _hit(Attack(30, "Physical", "Fire", accuracy=0.95), rng)
    assert rng.calls == 3
    assert result.hit
    assert result.crit
    assert result.breakdown["variance"] == pytest.approx(0.85)


def test_miss_consumes_one_roll_and_deals_no_damage() -> None:
    rng = ScriptedRng(0.99)
    result = _hit(Attack(30, "Physical", accuracy=0.95), rng)
    assert rng.calls == 1
    assert (result.damage, result.hit, result.crit, result.effectiveness) == (0, False, False, 1.0)


def test_forced_outcomes_do_not_consume_rolls() -> None:
    rng = ScriptedRng()
    _hit(Attack(30, "Physical"), rng, force_hit=True, force_crit=False, fixed_variance=1.0)
    assert rng.calls == 0


def test_crit_ignores_raised_defense_stages() -> None:
    defender = Combatant(STATS, "Nature", stages={"defense": 2})
    attack = Attack(40, "Physical")
    normal = calculate_damage(
        Combatant(STATS), defender, attack, RULES, CHART, ScriptedRng(),
        force_hit=True, force_crit=False, fixed_variance=1.0,
    )  # fmt: skip
    crit = calculate_damage(
        Combatant(STATS), defender, attack, RULES, CHART, ScriptedRng(),
        force_hit=True, force_crit=True, fixed_variance=1.0,
    )  # fmt: skip
    assert crit.breakdown["defense_stat"] == pytest.approx(STATS["defense"])
    assert normal.breakdown["defense_stat"] == pytest.approx(STATS["defense"] * 1.5)


def test_defending_halves_and_burn_weakens() -> None:
    fixed: dict[str, Any] = {"force_hit": True, "force_crit": False, "fixed_variance": 1.0}
    attack = Attack(60, "Physical")
    plain = calculate_damage(
        Combatant(STATS), Combatant(STATS), attack, RULES, CHART, ScriptedRng(), **fixed
    )
    guarded = calculate_damage(
        Combatant(STATS), Combatant(STATS, defending=True), attack, RULES, CHART, ScriptedRng(),
        **fixed,
    )  # fmt: skip
    burned = calculate_damage(
        Combatant(STATS, status_mods={"attack": 0.8}), Combatant(STATS), attack, RULES, CHART,
        ScriptedRng(), **fixed,
    )  # fmt: skip
    assert guarded.breakdown["raw"] == pytest.approx(plain.breakdown["raw"] * 0.5)
    assert burned.breakdown["attack_stat"] == pytest.approx(STATS["attack"] * 0.8)


def test_weak_attacker_still_scratches() -> None:
    weak = Combatant({**STATS, "attack": 1})
    tank = Combatant({**STATS, "defense": 999})
    result = calculate_damage(
        weak, tank, Attack(30, "Physical"), RULES, CHART, ScriptedRng(),
        force_hit=True, force_crit=False, fixed_variance=1.0,
    )  # fmt: skip
    assert result.breakdown["base"] == pytest.approx(30 / 30)


def test_same_seed_same_result() -> None:
    def run(seed: int):
        return _hit(Attack(30, "Physical", accuracy=0.9), random.Random(seed).random)

    assert run(42) == run(42)
