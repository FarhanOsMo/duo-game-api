"""Read-only game data endpoints. Responses keep the game's own field spelling
(camelCase) so a Luau client sees the same keys it uses in its modules."""

from typing import Any

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.api.deps import GameDataDep
from app.api.errors import not_found
from app.data.loader import dump
from app.data.rules import element_chart
from app.domain.elements import effectiveness_matrix

router = APIRouter(prefix="/api/v1", tags=["game data"])


def _with_id(entry_id: str, model: BaseModel) -> dict[str, Any]:
    return {"id": entry_id, **dump(model)}


def _listing(items: list[dict[str, Any]]) -> dict[str, Any]:
    return {"count": len(items), "items": items}


@router.get("/monsters", summary="List monsters, optionally filtered")
def list_monsters(
    data: GameDataDep,
    element: str | None = Query(None, description="e.g. Fire"),
    family: str | None = Query(None, description="e.g. Beast"),
    rarity: str | None = Query(None, description="rarityTier, e.g. Common"),
) -> dict[str, Any]:
    items = [
        _with_id(mid, mon)
        for mid, mon in sorted(data.monsters.items())
        if (element is None or mon.element == element)
        and (family is None or mon.family == family)
        and (rarity is None or mon.rarity_tier == rarity)
    ]
    return _listing(items)


@router.get("/monsters/{monster_id}", summary="One monster")
def get_monster(monster_id: str, data: GameDataDep) -> dict[str, Any]:
    if monster_id not in data.monsters:
        raise not_found("monster", monster_id)
    return _with_id(monster_id, data.monsters[monster_id])


@router.get("/abilities", summary="List abilities")
def list_abilities(data: GameDataDep) -> dict[str, Any]:
    return _listing([_with_id(aid, a) for aid, a in sorted(data.abilities.items())])


@router.get("/abilities/{ability_id}", summary="One ability")
def get_ability(ability_id: str, data: GameDataDep) -> dict[str, Any]:
    if ability_id not in data.abilities:
        raise not_found("ability", ability_id)
    return _with_id(ability_id, data.abilities[ability_id])


@router.get("/items", summary="List items, optionally filtered by category")
def list_items(
    data: GameDataDep,
    category: str | None = Query(None, description="e.g. Treat, Consumable, Key"),
) -> dict[str, Any]:
    items = [
        _with_id(iid, item)
        for iid, item in sorted(data.items.entries.items())
        if category is None or item.category == category
    ]
    return _listing(items)


@router.get("/items/{item_id}", summary="One item")
def get_item(item_id: str, data: GameDataDep) -> dict[str, Any]:
    if item_id not in data.items.entries:
        raise not_found("item", item_id)
    return _with_id(item_id, data.items.entries[item_id])


@router.get("/elements", summary="Elements, multipliers and the full effectiveness matrix")
def list_elements(data: GameDataDep) -> dict[str, Any]:
    return {
        "count": len(data.elements.entries),
        "items": [_with_id(eid, e) for eid, e in sorted(data.elements.entries.items())],
        "multipliers": dump(data.elements.multipliers),
        # matrix[attacker][defender], derived from the rules so it can never disagree
        # with /elements/effectiveness or the damage calculation.
        "matrix": effectiveness_matrix(element_chart(data)),
    }


@router.get("/personalities", summary="List personalities and their stat modifiers")
def list_personalities(data: GameDataDep) -> dict[str, Any]:
    return _listing([_with_id(pid, p) for pid, p in sorted(data.personalities.items())])


@router.get("/config", summary="The game and battle configuration, exactly as exported")
def get_config(data: GameDataDep) -> dict[str, Any]:
    return data.raw_config
