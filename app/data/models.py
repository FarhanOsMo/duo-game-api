"""Pydantic models mirroring the JSON files exported from Roblox Studio.

Every model ignores unknown fields on purpose. The game owns the data shape;
when a designer adds a field (a new recruitment knob, an animation tag) the
API must keep working and simply not expose it until we choose to.

Field names follow Python conventions. Aliases map them to the exported
spelling: camelCase for entries, PascalCase for top-level wrappers and for
config.json, which is how the game's Luau modules name things.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel, to_pascal


class GameModel(BaseModel):
    """Base for per-entry models (camelCase in the files)."""

    model_config = ConfigDict(
        extra="ignore", frozen=True, alias_generator=to_camel, populate_by_name=True
    )


class ConfigModel(BaseModel):
    """Base for config.json sections (PascalCase in the files)."""

    model_config = ConfigDict(
        extra="ignore", frozen=True, alias_generator=to_pascal, populate_by_name=True
    )


# --- monsters.json ---------------------------------------------------------


class LearnsetEntry(GameModel):
    ability: str
    level: int = Field(ge=1)


class Drop(GameModel):
    item: str
    chance: float = Field(ge=0, le=1)
    min: int = Field(ge=0)
    max: int = Field(ge=0)


class Recruitment(GameModel):
    favorite_treat: str | None = None


class Monster(GameModel):
    display_name: str
    element: str
    family: str
    rarity_tier: str
    base_stats: dict[str, float]
    growth: dict[str, float]
    learnset: list[LearnsetEntry]
    personalities: dict[str, float] = {}
    gender_rates: dict[str, float] = {}
    drops: list[Drop] = []
    essence: str | None = None
    recruitment: Recruitment | None = None


class MonstersFile(ConfigModel):
    entries: dict[str, Monster] = Field(alias="List")


# --- abilities.json --------------------------------------------------------


class AbilityEffect(GameModel):
    type: str
    status: str | None = None
    chance: float | None = None
    stat: str | None = None
    stages: int | None = None


class Ability(GameModel):
    # Field abilities (overworld actions) have no battle fields at all, so
    # everything battle-related is optional rather than invented.
    name: str
    kind: str
    source: str
    description: str = ""
    category: str | None = None
    element: str | None = None
    power: float = 0
    accuracy: float | None = None
    crit_bonus: float | None = None
    mp_cost: int | None = None
    target: str | None = None
    effects: list[AbilityEffect] = []


# --- items.json ------------------------------------------------------------


class Item(GameModel):
    name: str
    category: str
    description: str = ""
    price: int = Field(ge=0)
    rarity: str


class ItemRarity(GameModel):
    name: str
    order: int


class ItemsFile(ConfigModel):
    entries: dict[str, Item] = Field(alias="List")
    flavors: list[str] = []
    rarity: dict[str, ItemRarity]
    sell_ratio: float


# --- elements.json ---------------------------------------------------------


class Element(GameModel):
    name: str
    strong_against: list[str] = []


class ElementMultipliers(ConfigModel):
    strong: float
    resisted: float
    neutral: float


class ElementsFile(ConfigModel):
    entries: dict[str, Element] = Field(alias="List")
    multipliers: ElementMultipliers


# --- personalities.json, status_effects.json, rarities.json, essences.json -


class Personality(GameModel):
    name: str
    description: str = ""
    stat_mods: dict[str, float] = {}


class StatusEffect(GameModel):
    name: str
    stat_mods: dict[str, float] = {}
    tick: float | None = None


class Rarity(GameModel):
    name: str
    order: int


class Essence(GameModel):
    name: str
    species: str
    ability: str
    drop_chance: float = Field(ge=0, le=1)


class EssencesFile(ConfigModel):
    entries: dict[str, Essence] = Field(alias="List")


# --- encounter_tables.json, encounter_areas.json ---------------------------


class EncounterEntry(GameModel):
    species: str
    rarity: str
    level: tuple[int, int]


class EncounterTable(GameModel):
    name: str
    arena: str
    rate: float
    entries: list[EncounterEntry]


class EncounterTablesFile(ConfigModel):
    rarity_weights: dict[str, float]
    tables: dict[str, EncounterTable]


class EncounterArea(GameModel):
    encounter_enabled: bool
    table_id: str | None = None
    base_chance: float | None = None


class EncounterAreasFile(ConfigModel):
    areas: dict[str, EncounterArea]
    default: EncounterArea


# --- config.json -----------------------------------------------------------
# Only the constants the formulas need are modelled; GET /config serves the
# raw file so designers still see every value.


class ExperienceConfig(ConfigModel):
    base: float
    exponent: float


class MonsterConfig(ConfigModel):
    max_level: int = Field(ge=1)
    potential_max: int = Field(ge=0)
    stat_keys: list[str]


class GameConfig(ConfigModel):
    experience: ExperienceConfig
    monster: MonsterConfig


class DamageConfig(ConfigModel):
    attack_weight: float
    crit_chance: float
    crit_multiplier: float
    defend_multiplier: float
    defense_weight: float
    magic_defense_blend: float
    power_scale: float = Field(gt=0)
    variance: tuple[float, float]


class StagesConfig(ConfigModel):
    min: int
    max: int
    step: float


class BattleConfig(ConfigModel):
    damage: DamageConfig
    stages: StagesConfig


class ConfigFile(BaseModel):
    # The two top-level keys are lowercase ("game", "battle") unlike the rest.
    model_config = ConfigDict(extra="ignore", frozen=True)

    game: GameConfig
    battle: BattleConfig


# --- data/manifest.json (written by scripts/build_manifest.py) -------------


class Manifest(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)

    schema_version: int
    data_version: str
    content_sha256: str
    files: dict[str, str]


RawJson = dict[str, Any]
