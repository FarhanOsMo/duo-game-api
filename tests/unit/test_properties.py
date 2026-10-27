"""Property-style tests: invariants checked over many seeded inputs and the real data.

A seeded generator keeps them deterministic: a failure reproduces on every run
and in CI, unlike unseeded fuzzing.
"""

import random

import pytest

from app.data.loader import GameData
from app.data.rules import damage_rules, element_chart
from app.domain.damage import Attack, Combatant, calculate_damage
from app.domain.stats import stat_block


def test_stats_never_decrease_as_level_rises(game_data: GameData) -> None:
    monster_cfg = game_data.config.game.monster
    for species, mon in game_data.monsters.items():
        for potential in (0, monster_cfg.potential_max):
            for personality in [None, *game_data.personalities]:
                mods = game_data.personalities[personality].stat_mods if personality else None
                pots = dict.fromkeys(monster_cfg.stat_keys, potential)
                previous = None
                for level in range(1, monster_cfg.max_level + 1):
                    stats = stat_block(
                        mon.base_stats, mon.growth, level, monster_cfg.stat_keys, pots, mods
                    )
                    if previous is not None:
                        for key, value in stats.items():
                            assert value >= previous[key], (species, personality, level, key)
                    previous = stats


@pytest.mark.parametrize("seed", range(5))
def test_damage_is_at_least_one_on_every_hit(game_data: GameData, seed: int) -> None:
    rng = random.Random(seed)
    rules = damage_rules(game_data)
    chart = element_chart(game_data)
    keys = game_data.config.game.monster.stat_keys
    attacks = [a for a in game_data.abilities.values() if a.category in ("Physical", "Magical")]
    species = list(game_data.monsters.values())
    for _ in range(200):
        attacker, defender = rng.choice(species), rng.choice(species)
        ability = rng.choice(attacks)
        assert ability.category is not None

        def side(mon, level):
            pots = {k: rng.randint(0, 15) for k in keys}
            stages = {k: rng.randint(-3, 3) for k in keys}
            stats = stat_block(mon.base_stats, mon.growth, level, keys, pots)
            return stats, stages

        a_stats, a_stages = side(attacker, rng.randint(1, 50))
        d_stats, d_stages = side(defender, rng.randint(1, 50))
        result = calculate_damage(
            Combatant(a_stats, attacker.element, a_stages),
            Combatant(d_stats, defender.element, d_stages, defending=rng.random() < 0.5),
            Attack(ability.power, ability.category, ability.element or "Neutral"),
            rules,
            chart,
            rng.random,
            force_hit=True,
        )
        assert result.damage >= 1
