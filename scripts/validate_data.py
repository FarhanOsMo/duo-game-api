"""Validate every file in data/ exactly as the API does at startup.

Usage: python scripts/validate_data.py [--data-dir PATH]
Exit code 0 when the data is valid, 1 otherwise (CI gate).
"""

import argparse
import sys
from pathlib import Path

# Scripts run as plain files (no package install), so put the repo root on the path.
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from app.data.errors import DataValidationError  # noqa: E402
from app.data.loader import load_game_data  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--data-dir", type=Path, default=REPO_ROOT / "data")
    args = parser.parse_args()
    try:
        data = load_game_data(args.data_dir)
    except DataValidationError as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        return 1
    print(
        f"OK data {data.manifest.data_version}: {len(data.monsters)} monsters, "
        f"{len(data.abilities)} abilities, {len(data.items.entries)} items, "
        f"{len(data.elements.entries)} elements, {len(data.personalities)} personalities, "
        f"{len(data.encounter_tables.tables)} encounter tables"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
