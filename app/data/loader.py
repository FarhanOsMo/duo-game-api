"""Reads data/ into typed, immutable models and refuses to start on bad data.

Validation is fail-fast by design, mirroring the game's own boot-time checks:
a broken export should stop the deploy in CI, never reach a running service
that would answer balance questions with wrong numbers.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel, TypeAdapter, ValidationError

from app.data.errors import DataIssue, DataValidationError
from app.data.manifest import DATA_FILES, build_manifest
from app.data.models import (
    Ability,
    ConfigFile,
    ElementsFile,
    EncounterAreasFile,
    EncounterTablesFile,
    Essence,
    EssencesFile,
    ItemsFile,
    Manifest,
    Monster,
    MonstersFile,
    Personality,
    Rarity,
    StatusEffect,
)
from app.data.validator import find_reference_issues

# Top-level keys that wrap a map of entries; used to name the offending entry id.
_WRAPPER_KEYS = {"List", "Tables", "Areas"}


@dataclass(frozen=True)
class GameData:
    monsters: dict[str, Monster]
    abilities: dict[str, Ability]
    items: ItemsFile
    elements: ElementsFile
    personalities: dict[str, Personality]
    status_effects: dict[str, StatusEffect]
    rarities: dict[str, Rarity]
    essences: dict[str, Essence]
    encounter_tables: EncounterTablesFile
    encounter_areas: EncounterAreasFile
    config: ConfigFile
    raw_config: dict[str, Any]
    manifest: Manifest


_SCHEMAS: dict[str, TypeAdapter[Any]] = {
    "abilities.json": TypeAdapter(dict[str, Ability]),
    "config.json": TypeAdapter(ConfigFile),
    "elements.json": TypeAdapter(ElementsFile),
    "encounter_areas.json": TypeAdapter(EncounterAreasFile),
    "encounter_tables.json": TypeAdapter(EncounterTablesFile),
    "essences.json": TypeAdapter(EssencesFile),
    "items.json": TypeAdapter(ItemsFile),
    "monsters.json": TypeAdapter(MonstersFile),
    "personalities.json": TypeAdapter(dict[str, Personality]),
    "rarities.json": TypeAdapter(dict[str, Rarity]),
    "status_effects.json": TypeAdapter(dict[str, StatusEffect]),
}


def _entry_id(loc: tuple[int | str, ...]) -> str:
    if len(loc) > 1 and loc[0] in _WRAPPER_KEYS:
        return str(loc[1])
    return str(loc[0]) if loc else "<root>"


def _parse_file(data_dir: Path, name: str) -> tuple[Any, Any] | list[DataIssue]:
    path = data_dir / name
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return [DataIssue(name, "<file>", "file is missing")]
    except json.JSONDecodeError as exc:
        return [DataIssue(name, "<file>", f"invalid JSON at line {exc.lineno}: {exc.msg}")]
    try:
        return raw, _SCHEMAS[name].validate_python(raw)
    except ValidationError as exc:
        return [
            DataIssue(
                name,
                _entry_id(err["loc"]),
                f"{'.'.join(str(part) for part in err['loc'])}: {err['msg']}",
            )
            for err in exc.errors()
        ]


def load_game_data(data_dir: Path) -> GameData:
    """Parse, schema-check and cross-check every data file. Raises DataValidationError."""
    parsed: dict[str, Any] = {}
    raw_files: dict[str, Any] = {}
    issues: list[DataIssue] = []
    for name in DATA_FILES:
        result = _parse_file(data_dir, name)
        if isinstance(result, list):
            issues.extend(result)
        else:
            raw_files[name], parsed[name] = result
    # Cross-references are meaningless if a file failed to parse, so stop here first.
    if issues:
        raise DataValidationError(issues)

    data = GameData(
        monsters=parsed["monsters.json"].entries,
        abilities=parsed["abilities.json"],
        items=parsed["items.json"],
        elements=parsed["elements.json"],
        personalities=parsed["personalities.json"],
        status_effects=parsed["status_effects.json"],
        rarities=parsed["rarities.json"],
        essences=parsed["essences.json"].entries,
        encounter_tables=parsed["encounter_tables.json"],
        encounter_areas=parsed["encounter_areas.json"],
        config=parsed["config.json"],
        raw_config=raw_files["config.json"],
        manifest=build_manifest(data_dir),
    )
    issues = find_reference_issues(data)
    if issues:
        raise DataValidationError(issues)
    return data


def dump(model: BaseModel) -> dict[str, Any]:
    """Serialise a model back to the game's own field spelling for API responses."""
    return model.model_dump(by_alias=True, exclude_none=True)
