"""The data actually committed to the repo must load and pass every check."""

import subprocess
import sys

from app.data.loader import GameData
from app.data.manifest import DATA_FILES, MANIFEST_FILE, build_manifest, render_manifest
from tests.conftest import DATA_DIR, REPO_ROOT


def test_committed_data_loads(game_data: GameData) -> None:
    assert game_data.monsters, "monsters.json has no entries"
    assert game_data.abilities
    assert game_data.elements.entries
    assert game_data.config.game.monster.max_level >= 1


def test_every_exported_file_is_present() -> None:
    present = {p.name for p in DATA_DIR.glob("*.json")} - {MANIFEST_FILE}
    assert present == set(DATA_FILES)


def test_committed_manifest_is_current() -> None:
    committed = (DATA_DIR / MANIFEST_FILE).read_text(encoding="utf-8").replace("\r\n", "\n")
    assert committed == render_manifest(build_manifest(DATA_DIR))


def test_validate_data_script_passes_on_committed_data() -> None:
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "validate_data.py")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.startswith("OK data")
