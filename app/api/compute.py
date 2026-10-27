"""Computation endpoints: thin adapters from HTTP to the pure domain formulas.

All game-specific limits (MaxLevel, PotentialMax, stat keys) are checked
against config.json at request time rather than hard-coded in Query(le=...),
so a balance change in the game needs no code change here.
"""

import random
from typing import Annotated, Any

from fastapi import APIRouter, Path, Query
from pydantic import BaseModel, ConfigDict, Field

from app.api.deps import GameDataDep
from app.api.errors import invalid, not_found
from app.core.metrics import DAMAGE_CALCULATIONS
from app.data.loader import GameData
from app.data.rules import damage_rules, element_chart
from app.domain.damage import Attack, Combatant, calculate_damage
from app.domain.elements import get_multiplier
from app.domain.stats import exp_for_level, level_for_exp, stat_block

router = APIRouter(prefix="/api/v1", tags=["computation"])

# Only these categories deal damage. Support (power 0) and Heal abilities exist
# in the data but go through different code paths in the game.
DAMAGING_CATEGORIES = ("Physical", "Magical")


def _check_level(data: GameData, level: int) -> None:
    max_level = data.config.game.monster.max_level
    if not 1 <= level <= max_level:
        raise invalid(f"level must be between 1 and {max_level}, got {level}")


def _check_potential(data: GameData, potential: dict[str, int]) -> None:
    cfg = data.config.game.monster
    for stat, value in potential.items():
        if stat not in cfg.stat_keys:
            raise invalid(f"unknown stat '{stat}' in potential; valid: {cfg.stat_keys}")
        if not 0 <= value <= cfg.potential_max:
            raise invalid(f"potential {stat} must be between 0 and {cfg.potential_max}")


def _stats_for(
    data: GameData, species: str, level: int, personality: str | None, potential: dict[str, int]
) -> dict[str, int]:
    if species not in data.monsters:
        raise not_found("monster", species)
    if personality is not None and personality not in data.personalities:
        raise invalid(f"unknown personality '{personality}'", "invalid_reference")
    _check_level(data, level)
    _check_potential(data, potential)
    mon = data.monsters[species]
    mods = data.personalities[personality].stat_mods if personality else None
    return stat_block(
        mon.base_stats, mon.growth, level, data.config.game.monster.stat_keys, potential, mods
    )


# --- stats and experience ---------------------------------------------------

PotentialQuery = Annotated[int, Query(ge=0)]


@router.get("/monsters/{monster_id}/stats", summary="Stat block at a level")
def monster_stats(
    monster_id: str,
    data: GameDataDep,
    level: Annotated[int, Query(description="1 to game.Monster.MaxLevel")],
    personality: str | None = None,
    potential_hp: PotentialQuery = 0,
    potential_mp: PotentialQuery = 0,
    potential_attack: PotentialQuery = 0,
    potential_defense: PotentialQuery = 0,
    potential_magic: PotentialQuery = 0,
    potential_speed: PotentialQuery = 0,
) -> dict[str, Any]:
    potential = {
        "hp": potential_hp,
        "mp": potential_mp,
        "attack": potential_attack,
        "defense": potential_defense,
        "magic": potential_magic,
        "speed": potential_speed,
    }
    # Only pass stats the game actually defines, so a future StatKeys change is respected.
    potential = {k: v for k, v in potential.items() if k in data.config.game.monster.stat_keys}
    stats = _stats_for(data, monster_id, level, personality, potential)
    return {
        "species": monster_id,
        "level": level,
        "personality": personality,
        "potential": potential,
        "stats": stats,
    }


# Declared before /exp/{level} so "level-for" is never parsed as a level.
@router.get("/exp/level-for", summary="Highest level reached with this much EXP")
def level_for(data: GameDataDep, exp: Annotated[float, Query(ge=0)]) -> dict[str, Any]:
    cfg = data.config.game
    level = level_for_exp(exp, cfg.experience.base, cfg.experience.exponent, cfg.monster.max_level)
    return {"exp": exp, "level": level}


@router.get("/exp/{level}", summary="Total EXP required to reach a level")
def exp_for(data: GameDataDep, level: Annotated[int, Path()]) -> dict[str, int]:
    _check_level(data, level)
    cfg = data.config.game
    exp = exp_for_level(level, cfg.experience.base, cfg.experience.exponent, cfg.monster.max_level)
    return {"level": level, "exp": exp}


# --- elements ---------------------------------------------------------------


@router.get("/elements/effectiveness", summary="Multiplier for one attacker/defender pair")
def effectiveness(data: GameDataDep, attack: str, defend: str) -> dict[str, Any]:
    # The game treats unknown elements as neutral; the API rejects them instead,
    # because over HTTP an unknown name is almost always a typo worth surfacing.
    for name in (attack, defend):
        if name not in data.elements.entries:
            raise not_found("element", name)
    return {
        "attack": attack,
        "defend": defend,
        "multiplier": get_multiplier(element_chart(data), attack, defend),
    }


# --- damage -----------------------------------------------------------------


class Side(BaseModel):
    model_config = ConfigDict(extra="forbid")

    species: str
    level: int
    personality: str | None = None
    potential: dict[str, int] = Field(default_factory=dict)
    stages: dict[str, int] = Field(
        default_factory=dict, description="Stat stages; clamped to battle.Stages like the game"
    )
    status: str | None = Field(None, description="Active status effect, e.g. Burn")


class DefenderSide(Side):
    defending: bool = False


class DamageRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "ability": "ab_cinder_spit",
                "attacker": {"species": "mon_placeholder_a", "level": 5},
                "defender": {"species": "mon_placeholder_b", "level": 5},
                "fixed_variance": 1.0,
                "force_hit": True,
                "force_crit": False,
            }
        },
    )

    ability: str
    attacker: Side
    defender: DefenderSide
    seed: int | None = Field(None, description="Seed for hit, crit and variance rolls")
    fixed_variance: float | None = Field(None, gt=0)
    force_crit: bool | None = None
    force_hit: bool | None = None


class DamageResponse(BaseModel):
    damage: int
    crit: bool
    effectiveness: float
    hit: bool
    breakdown: dict[str, Any]


def _combatant(data: GameData, side: Side, defending: bool = False) -> Combatant:
    stats = _stats_for(data, side.species, side.level, side.personality, side.potential)
    for stat in side.stages:
        if stat not in data.config.game.monster.stat_keys:
            raise invalid(f"unknown stat '{stat}' in stages")
    status_mods: dict[str, float] = {}
    if side.status is not None:
        if side.status not in data.status_effects:
            raise invalid(f"unknown status '{side.status}'", "invalid_reference")
        status_mods = dict(data.status_effects[side.status].stat_mods)
    return Combatant(
        stats=stats,
        element=data.monsters[side.species].element,
        stages=side.stages,
        status_mods=status_mods,
        defending=defending,
    )


@router.post("/battle/damage", summary="Damage of one ability hit", response_model=DamageResponse)
def battle_damage(body: DamageRequest, data: GameDataDep) -> DamageResponse:
    ability = data.abilities.get(body.ability)
    if ability is None:
        raise invalid(f"unknown ability '{body.ability}'", "invalid_reference")
    if ability.category not in DAMAGING_CATEGORIES or ability.power <= 0:
        raise invalid(
            f"ability '{body.ability}' ({ability.category}, power {ability.power:g}) "
            "deals no damage; only Physical or Magical abilities with power > 0 can be used",
            "unsupported_ability",
        )
    attacker = _combatant(data, body.attacker)
    defender = _combatant(data, body.defender, body.defender.defending)
    # Unseeded requests draw from OS entropy like a real battle; seeded ones replay exactly.
    rng = random.Random(body.seed)
    result = calculate_damage(
        attacker,
        defender,
        Attack(
            power=ability.power,
            category=ability.category,
            element=ability.element or "Neutral",
            accuracy=ability.accuracy if ability.accuracy is not None else 1.0,
            crit_bonus=ability.crit_bonus or 0.0,
        ),
        damage_rules(data),
        element_chart(data),
        rng.random,
        fixed_variance=body.fixed_variance,
        force_hit=body.force_hit,
        force_crit=body.force_crit,
    )
    outcome = "miss" if not result.hit else "crit" if result.crit else "hit"
    DAMAGE_CALCULATIONS.labels(category=ability.category, outcome=outcome).inc()
    breakdown = {
        "ability": body.ability,
        "attacker_stats": attacker.stats,
        "defender_stats": defender.stats,
        "seed": body.seed,
        **result.breakdown,
    }
    return DamageResponse(
        damage=result.damage,
        crit=result.crit,
        effectiveness=result.effectiveness,
        hit=result.hit,
        breakdown=breakdown,
    )
