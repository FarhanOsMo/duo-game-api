"""Builds the domain's rule objects from loaded game data.

The domain package never imports the data layer; this adapter is the one place
that knows how config.json and elements.json map onto formula parameters.
"""

from app.data.loader import GameData
from app.domain.damage import DamageRules
from app.domain.elements import ElementChart
from app.domain.stats import StageRules


def stage_rules(data: GameData) -> StageRules:
    stages = data.config.battle.stages
    return StageRules(min=stages.min, max=stages.max, step=stages.step)


def damage_rules(data: GameData) -> DamageRules:
    dmg = data.config.battle.damage
    return DamageRules(
        attack_weight=dmg.attack_weight,
        defense_weight=dmg.defense_weight,
        power_scale=dmg.power_scale,
        crit_chance=dmg.crit_chance,
        crit_multiplier=dmg.crit_multiplier,
        defend_multiplier=dmg.defend_multiplier,
        magic_defense_blend=dmg.magic_defense_blend,
        variance=dmg.variance,
        stages=stage_rules(data),
    )


def element_chart(data: GameData) -> ElementChart:
    elements = data.elements
    return ElementChart(
        strong_against={name: e.strong_against for name, e in elements.entries.items()},
        strong=elements.multipliers.strong,
        resisted=elements.multipliers.resisted,
        neutral=elements.multipliers.neutral,
    )
