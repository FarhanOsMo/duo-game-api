"""Appendix B golden values, computed by hand and checked against the real data.

These are the parity contract with the game's Luau. A failure here means the
Python formulas have drifted from the game: fix the code, never the expected value.
"""

import pytest

from app.data.loader import GameData
from app.data.rules import damage_rules, element_chart, stage_rules
from app.domain.damage import Attack, Combatant, calculate_damage
from app.domain.elements import get_multiplier
from app.domain.stats import exp_for_level, stage_multiplier, stat_block


def _stats(data: GameData, species: str, level: int, personality: str | None = None):
    mon = data.monsters[species]
    mods = data.personalities[personality].stat_mods if personality else None
    return stat_block(
        mon.base_stats,
        mon.growth,
        level,
        data.config.game.monster.stat_keys,
        personality_mods=mods,
    )


def test_placeholder_a_level_5(game_data: GameData) -> None:
    assert _stats(game_data, "mon_placeholder_a", 5) == {
        "hp": 46, "mp": 15, "attack": 19, "defense": 11, "magic": 14, "speed": 15
    }  # fmt: skip


def test_placeholder_a_level_5_brave(game_data: GameData) -> None:
    stats = _stats(game_data, "mon_placeholder_a", 5, "Brave")
    assert stats["attack"] == 20
    assert stats["speed"] == 15
    assert (stats["hp"], stats["defense"], stats["magic"]) == (46, 11, 14)


def test_placeholder_b_level_5(game_data: GameData) -> None:
    assert _stats(game_data, "mon_placeholder_b", 5) == {
        "hp": 53, "mp": 21, "attack": 12, "defense": 14, "magic": 17, "speed": 11
    }  # fmt: skip


@pytest.mark.parametrize(("level", "expected"), [(2, 12), (5, 271)])
def test_exp_for_level(game_data: GameData, level: int, expected: int) -> None:
    exp = game_data.config.game.experience
    max_level = game_data.config.game.monster.max_level
    assert exp_for_level(level, exp.base, exp.exponent, max_level) == expected


@pytest.mark.parametrize(
    ("attack", "defend", "expected"),
    [
        ("Fire", "Water", 0.67),
        ("Water", "Fire", 1.5),
        ("Fire", "Nature", 1.5),
        ("Light", "Dark", 1.5),
        ("Dark", "Light", 1.5),
        *[("Neutral", other, 1.0) for other in ("Fire", "Water", "Dark", "Neutral")],
    ],
)
def test_element_multipliers(
    game_data: GameData, attack: str, defend: str, expected: float
) -> None:
    assert get_multiplier(element_chart(game_data), attack, defend) == expected


@pytest.mark.parametrize(
    ("stage", "expected"), [(1, 1.25), (3, 1.75), (-1, 0.8), (-3, 1 / 1.75), (0, 1.0)]
)
def test_stage_multipliers(game_data: GameData, stage: int, expected: float) -> None:
    assert stage_multiplier(stage, stage_rules(game_data)) == pytest.approx(expected)


def test_cinder_spit_damage(game_data: GameData) -> None:
    ability = game_data.abilities["ab_cinder_spit"]
    assert ability.power is not None
    assert ability.category is not None
    result = calculate_damage(
        Combatant(stats=_stats(game_data, "mon_placeholder_a", 5), element="Fire"),
        Combatant(stats=_stats(game_data, "mon_placeholder_b", 5), element="Water"),
        Attack(
            power=ability.power, category=ability.category, element=ability.element or "Neutral"
        ),
        damage_rules(game_data),
        element_chart(game_data),
        rng=lambda: pytest.fail("no random roll expected when every outcome is fixed"),
        fixed_variance=1.0,
        force_hit=True,
        force_crit=False,
    )
    assert result.breakdown["defense_stat"] == pytest.approx(15.5)
    assert result.breakdown["base"] == pytest.approx(9.5667, abs=1e-4)
    assert result.breakdown["raw"] == pytest.approx(6.41, abs=1e-2)
    assert result.damage == 6
    assert (result.hit, result.crit, result.effectiveness) == (True, False, 0.67)
