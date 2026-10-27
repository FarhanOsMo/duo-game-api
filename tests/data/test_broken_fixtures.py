"""Each fixture in tests/fixtures/broken_data breaks one rule; each must be rejected.

A fixture is a patch (file + JSON path + bad value) applied to a fresh copy of
the real data, so every test proves exactly one check works and nothing else
in the data is accidentally wrong.
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from app.data.errors import DataValidationError
from app.data.loader import load_game_data
from tests.conftest import FIXTURES_DIR, REPO_ROOT

BROKEN = sorted((FIXTURES_DIR / "broken_data").glob("*.json"))


def _apply(data_dir: Path, fixture: dict[str, Any]) -> None:
    target = data_dir / fixture["file"]
    if "raw" in fixture:
        target.write_text(fixture["raw"], encoding="utf-8")
        return
    document = json.loads(target.read_text(encoding="utf-8"))
    node = document
    *parents, leaf = fixture["path"]
    for key in parents:
        node = node[key]
    node[leaf] = fixture["value"]
    target.write_text(json.dumps(document), encoding="utf-8")


def test_there_is_a_fixture_per_rule() -> None:
    assert len(BROKEN) >= 15


@pytest.mark.parametrize("fixture_path", BROKEN, ids=lambda p: p.stem)
def test_broken_fixture_is_rejected(fixture_path: Path, data_copy: Path) -> None:
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    _apply(data_copy, fixture)

    with pytest.raises(DataValidationError) as caught:
        load_game_data(data_copy)

    expect = fixture["expect"]
    matching = [
        issue
        for issue in caught.value.issues
        if issue.file == expect["file"]
        and issue.entry_id == expect["entry_id"]
        and expect["message"] in issue.message
    ]
    assert matching, f"expected {expect}, got {caught.value.issues}"
    # The error text must name both the file and the id so a designer can find it.
    assert f"data/{expect['file']} [{expect['entry_id']}]" in str(caught.value)


def test_validate_script_exits_1_on_broken_data(data_copy: Path) -> None:
    _apply(data_copy, json.loads(BROKEN[0].read_text(encoding="utf-8")))
    script = REPO_ROOT / "scripts" / "validate_data.py"
    result = subprocess.run(
        [sys.executable, str(script), "--data-dir", str(data_copy)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    assert "FAIL" in result.stderr


def test_missing_file_is_reported(data_copy: Path) -> None:
    (data_copy / "rarities.json").unlink()
    with pytest.raises(DataValidationError, match=r"rarities.json \[<file>\]: file is missing"):
        load_game_data(data_copy)


def test_unknown_extra_fields_are_ignored(data_copy: Path) -> None:
    """A game update that adds fields must never break the API."""
    path = data_copy / "monsters.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    document["List"]["mon_placeholder_a"]["brandNewField"] = {"anything": [1, 2, 3]}
    document["SomeNewTopLevelKey"] = True
    path.write_text(json.dumps(document), encoding="utf-8")
    assert "mon_placeholder_a" in load_game_data(data_copy).monsters
