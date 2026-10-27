import shutil
from pathlib import Path

import pytest

from app.data.loader import GameData, load_game_data

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data"
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture(scope="session")
def game_data() -> GameData:
    """The committed data/ folder, loaded once: the same data production serves."""
    return load_game_data(DATA_DIR)


@pytest.fixture
def data_copy(tmp_path: Path) -> Path:
    """A disposable copy of data/ that a test may break without touching the real files."""
    target = tmp_path / "data"
    shutil.copytree(DATA_DIR, target)
    return target
