import json

import pytest
from fastapi.testclient import TestClient

from tests.api.conftest import assert_error
from tests.conftest import DATA_DIR


def test_list_monsters(client: TestClient) -> None:
    body = client.get("/api/v1/monsters").json()
    assert body["count"] == 3
    first = body["items"][0]
    assert first["id"] == "mon_placeholder_a"
    # Responses keep the game's camelCase spelling and drop fields v1 does not model.
    assert first["displayName"] == "Placeholder A"
    assert "baseStats" in first
    assert "overworld" not in first


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("element=Fire", ["mon_placeholder_a"]),
        ("family=Aquatic", ["mon_placeholder_b"]),
        ("rarity=Uncommon", ["mon_placeholder_c"]),
        ("rarity=Common&element=Water", ["mon_placeholder_b"]),
        ("element=Ice", []),
    ],
)
def test_monster_filters(client: TestClient, query: str, expected: list[str]) -> None:
    body = client.get(f"/api/v1/monsters?{query}").json()
    assert [m["id"] for m in body["items"]] == expected
    assert body["count"] == len(expected)


def test_get_monster(client: TestClient) -> None:
    body = client.get("/api/v1/monsters/mon_placeholder_b").json()
    assert body["element"] == "Water"
    assert body["learnset"][1] == {"ability": "ab_tide_pulse", "level": 3}


def test_unknown_monster_is_404(client: TestClient) -> None:
    error = assert_error(client.get("/api/v1/monsters/mon_missing"), 404, "not_found")
    assert "mon_missing" in error["message"]


def test_abilities(client: TestClient) -> None:
    assert client.get("/api/v1/abilities").json()["count"] == 8
    spit = client.get("/api/v1/abilities/ab_cinder_spit").json()
    assert (spit["category"], spit["element"], spit["power"]) == ("Magical", "Fire", 40)
    assert_error(client.get("/api/v1/abilities/ab_missing"), 404, "not_found")


def test_items_and_category_filter(client: TestClient) -> None:
    assert client.get("/api/v1/items").json()["count"] == 7
    treats = client.get("/api/v1/items?category=Treat").json()
    assert treats["count"] == 4
    assert all(item["category"] == "Treat" for item in treats["items"])
    assert client.get("/api/v1/items/item_healing_herb").json()["price"] == 12
    assert_error(client.get("/api/v1/items/item_missing"), 404, "not_found")


def test_elements_include_full_matrix(client: TestClient) -> None:
    body = client.get("/api/v1/elements").json()
    names = [e["id"] for e in body["items"]]
    assert body["count"] == len(names) == 10
    assert set(body["matrix"]) == set(names)
    assert all(set(row) == set(names) for row in body["matrix"].values())
    assert body["matrix"]["Fire"]["Water"] == 0.67
    assert body["multipliers"] == {"Strong": 1.5, "Resisted": 0.67, "Neutral": 1}


def test_personalities(client: TestClient) -> None:
    body = client.get("/api/v1/personalities").json()
    brave = next(p for p in body["items"] if p["id"] == "Brave")
    assert brave["statMods"] == {"attack": 1.1, "speed": 0.95}


def test_config_is_served_exactly_as_exported(client: TestClient) -> None:
    raw = json.loads((DATA_DIR / "config.json").read_text(encoding="utf-8"))
    assert client.get("/api/v1/config").json() == raw
