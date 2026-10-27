"""Single-hit damage calculation (mirrors the game's Luau damage function).

Randomness is injected as a zero-argument function returning a float in
[0, 1), the same contract as Lua's math.random(). Callers pass a seeded
random.Random(seed).random, so any result can be reproduced exactly from its
inputs: a designer can share a request and get the same crit and variance.

RNG call order is fixed and must match the game: hit roll, then crit roll,
then variance roll. A forced outcome (force_hit, force_crit, fixed_variance)
replaces its roll and does not consume a random number.
"""

import math
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

from app.domain.elements import ElementChart, get_multiplier
from app.domain.stats import StageRules, stage_multiplier

MAGICAL = "Magical"


@dataclass(frozen=True)
class DamageRules:
    attack_weight: float
    defense_weight: float
    power_scale: float
    crit_chance: float
    crit_multiplier: float
    defend_multiplier: float
    magic_defense_blend: float
    variance: tuple[float, float]
    stages: StageRules


@dataclass(frozen=True)
class Combatant:
    stats: Mapping[str, int]
    element: str = "Neutral"
    stages: Mapping[str, int] = field(default_factory=dict)
    status_mods: Mapping[str, float] = field(default_factory=dict)
    defending: bool = False


@dataclass(frozen=True)
class Attack:
    power: float
    category: str
    element: str = "Neutral"
    accuracy: float = 1.0
    crit_bonus: float = 0.0


@dataclass(frozen=True)
class DamageResult:
    damage: int
    crit: bool
    effectiveness: float
    hit: bool
    breakdown: dict[str, Any]


def effective_stat(combatant: Combatant, stat: str, stages: StageRules) -> float:
    value = combatant.stats[stat] * stage_multiplier(combatant.stages.get(stat, 0), stages)
    return value * combatant.status_mods.get(stat, 1.0)


def calculate_damage(
    attacker: Combatant,
    defender: Combatant,
    attack: Attack,
    rules: DamageRules,
    chart: ElementChart,
    rng: Callable[[], float],
    *,
    fixed_variance: float | None = None,
    force_hit: bool | None = None,
    force_crit: bool | None = None,
) -> DamageResult:
    hit = force_hit if force_hit is not None else rng() <= attack.accuracy
    if not hit:
        return DamageResult(0, False, 1.0, False, {"reason": "missed"})

    crit = force_crit if force_crit is not None else rng() < rules.crit_chance + attack.crit_bonus

    magical = attack.category == MAGICAL
    attack_stat = effective_stat(attacker, "magic" if magical else "attack", rules.stages)
    defense = effective_stat(defender, "defense", rules.stages)
    if magical:
        blend = rules.magic_defense_blend
        defense = defense * (1 - blend) + effective_stat(defender, "magic", rules.stages) * blend

    defense_stage = defender.stages.get("defense", 0)
    if crit and defense_stage > 0:
        # A critical hit ignores the defender's raised Defense stages.
        defense = defense / stage_multiplier(defense_stage, rules.stages)

    scale = attack.power / rules.power_scale
    base = scale * (attack_stat * rules.attack_weight - defense * rules.defense_weight)
    # Floor at power / PowerScale so a weak attacker still scratches a tank.
    base = max(base, scale)

    low, high = rules.variance
    variance = fixed_variance if fixed_variance is not None else low + rng() * (high - low)
    effectiveness = get_multiplier(chart, attack.element, defender.element)

    raw = base * variance * effectiveness
    if crit:
        raw *= rules.crit_multiplier
    if defender.defending:
        raw *= rules.defend_multiplier
    # Lua's math.floor(x + 0.5): round half up, never banker's rounding.
    damage = max(1, math.floor(raw + 0.5))

    breakdown = {
        "magical": magical,
        "attack_stat": attack_stat,
        "defense_stat": defense,
        "base": base,
        "variance": variance,
        "effectiveness": effectiveness,
        "crit_multiplier": rules.crit_multiplier if crit else 1.0,
        "defend_multiplier": rules.defend_multiplier if defender.defending else 1.0,
        "raw": raw,
    }
    return DamageResult(damage, crit, effectiveness, True, breakdown)
