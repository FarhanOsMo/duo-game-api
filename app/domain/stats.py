"""Stat, stage and experience formulas (mirrors the game's Luau).

Rounding uses math.floor everywhere, matching Lua. Python's round() is banker's
rounding (round(2.5) == 2) and would silently disagree with the game on exact
halves, so it is never used for game numbers.
"""

import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class StageRules:
    min: int
    max: int
    step: float


def stat_at_level(
    base: float, growth: float, level: int, potential: int = 0, personality_mult: float = 1.0
) -> int:
    # Operation order matches the Luau line exactly so floating-point results agree
    # bit for bit: potential * level is computed before the division by 25.
    value = base * (1 + growth * (level - 1)) + potential * level / 25
    return max(1, math.floor(value * personality_mult))


def stat_block(
    base_stats: Mapping[str, float],
    growth: Mapping[str, float],
    level: int,
    stat_keys: Iterable[str],
    potentials: Mapping[str, int] | None = None,
    personality_mods: Mapping[str, float] | None = None,
) -> dict[str, int]:
    potentials = potentials or {}
    personality_mods = personality_mods or {}
    return {
        key: stat_at_level(
            base_stats[key],
            growth[key],
            level,
            potentials.get(key, 0),
            personality_mods.get(key, 1.0),
        )
        for key in stat_keys
    }


def stage_multiplier(stage: int, rules: StageRules) -> float:
    stage = max(rules.min, min(rules.max, stage))
    if stage >= 0:
        return 1 + stage * rules.step
    # Negative stages divide instead of subtract, so -1 then +1 returns to exactly 1.0.
    return 1 / (1 + (-stage) * rules.step)


def exp_for_level(level: int, base: float, exponent: float, max_level: int) -> int:
    clamped = max(1, min(max_level, level))
    # math.pow is Lua's ^ for a non-negative base and is typed float, unlike int ** float.
    return math.floor(base * math.pow(clamped - 1, exponent))


def level_for_exp(exp: float, base: float, exponent: float, max_level: int) -> int:
    level = 1
    # A linear scan over at most MaxLevel entries is clearer than a closed-form
    # inverse and cannot disagree with exp_for_level at the boundaries.
    for candidate in range(1, max_level + 1):
        if exp >= exp_for_level(candidate, base, exponent, max_level):
            level = candidate
        else:
            break
    return level
