"""Cross-file reference checks, mirroring the game's boot-time validation.

Schema validation (models.py) proves each file is well formed on its own.
These checks prove the files agree with each other: a learnset that names a
deleted ability or a monster with an unknown element is valid JSON but would
crash or silently misbehave in the game, so CI must reject it.
"""

from collections.abc import Iterable
from typing import TYPE_CHECKING

from app.data.errors import DataIssue

if TYPE_CHECKING:
    # Imported for type hints only: loader imports this module at runtime.
    from app.data.loader import GameData


def _missing(
    file: str, entry_id: str, what: str, refs: Iterable[str], known: Iterable[str]
) -> list[DataIssue]:
    known_set = set(known)
    return [
        DataIssue(file, entry_id, f"unknown {what} '{ref}'") for ref in refs if ref not in known_set
    ]


def _check_monsters(data: "GameData") -> list[DataIssue]:
    issues: list[DataIssue] = []
    f = "monsters.json"
    stat_keys = set(data.config.game.monster.stat_keys)
    for mid, mon in data.monsters.items():
        issues += _missing(f, mid, "ability", (e.ability for e in mon.learnset), data.abilities)
        issues += _missing(f, mid, "element", [mon.element], data.elements.entries)
        issues += _missing(f, mid, "rarityTier", [mon.rarity_tier], data.rarities)
        issues += _missing(f, mid, "personality", mon.personalities, data.personalities)
        issues += _missing(f, mid, "drop item", (d.item for d in mon.drops), data.items.entries)
        if mon.recruitment and mon.recruitment.favorite_treat:
            issues += _missing(
                f, mid, "favoriteTreat item", [mon.recruitment.favorite_treat], data.items.entries
            )
        if mon.essence is not None:
            issues += _missing(f, mid, "essence", [mon.essence], data.essences)
        total = sum(mon.gender_rates.values())
        if mon.gender_rates and abs(total - 100) > 1e-9:
            issues.append(DataIssue(f, mid, f"genderRates sum to {total:g}, expected 100"))
        for field, stats in (("baseStats", mon.base_stats), ("growth", mon.growth)):
            if set(stats) != stat_keys:
                issues.append(
                    DataIssue(
                        f, mid, f"{field} keys {sorted(stats)} != StatKeys {sorted(stat_keys)}"
                    )
                )
        for drop in mon.drops:
            if drop.min > drop.max:
                issues.append(DataIssue(f, mid, f"drop '{drop.item}' has min > max"))
    return issues


def _check_abilities(data: "GameData") -> list[DataIssue]:
    issues: list[DataIssue] = []
    f = "abilities.json"
    for aid, ability in data.abilities.items():
        if ability.element is not None:
            issues += _missing(f, aid, "element", [ability.element], data.elements.entries)
        statuses = [e.status for e in ability.effects if e.status is not None]
        issues += _missing(f, aid, "status effect", statuses, data.status_effects)
    return issues


def _check_catalogues(data: "GameData") -> list[DataIssue]:
    issues: list[DataIssue] = []
    stat_keys = data.config.game.monster.stat_keys
    for eid, element in data.elements.entries.items():
        issues += _missing(
            "elements.json",
            eid,
            "strongAgainst element",
            element.strong_against,
            data.elements.entries,
        )
    for iid, item in data.items.entries.items():
        issues += _missing("items.json", iid, "item rarity", [item.rarity], data.items.rarity)
    for pid, personality in data.personalities.items():
        issues += _missing("personalities.json", pid, "stat", personality.stat_mods, stat_keys)
    for sid, status in data.status_effects.items():
        issues += _missing("status_effects.json", sid, "stat", status.stat_mods, stat_keys)
    for esid, essence in data.essences.items():
        issues += _missing("essences.json", esid, "species", [essence.species], data.monsters)
        issues += _missing("essences.json", esid, "ability", [essence.ability], data.abilities)
    return issues


def _check_encounters(data: "GameData") -> list[DataIssue]:
    issues: list[DataIssue] = []
    tables = data.encounter_tables
    for tid, table in tables.tables.items():
        f = "encounter_tables.json"
        issues += _missing(f, tid, "species", (e.species for e in table.entries), data.monsters)
        issues += _missing(
            f, tid, "encounter rarity", (e.rarity for e in table.entries), tables.rarity_weights
        )
        for entry in table.entries:
            low, high = entry.level
            if low > high:
                issues.append(DataIssue(f, tid, f"level range {low}-{high} is reversed"))
    areas = {**data.encounter_areas.areas, "Default": data.encounter_areas.default}
    for area_id, area in areas.items():
        f = "encounter_areas.json"
        if area.table_id is not None:
            issues += _missing(f, area_id, "tableId", [area.table_id], tables.tables)
        elif area.encounter_enabled:
            issues.append(DataIssue(f, area_id, "encounterEnabled is true but no tableId is set"))
    return issues


def find_reference_issues(data: "GameData") -> list[DataIssue]:
    return [
        *_check_monsters(data),
        *_check_abilities(data),
        *_check_catalogues(data),
        *_check_encounters(data),
    ]
