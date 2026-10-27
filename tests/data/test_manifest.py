"""Canonical-JSON hashing: formatting noise must not change the data version."""

import json
import subprocess
import sys
from pathlib import Path

from app.data.manifest import MANIFEST_FILE, build_manifest
from tests.conftest import REPO_ROOT

SCRIPT = REPO_ROOT / "scripts" / "build_manifest.py"


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args], capture_output=True, text=True, check=False
    )


def test_whitespace_and_line_endings_do_not_change_the_hash(data_copy: Path) -> None:
    before = build_manifest(data_copy)
    path = data_copy / "elements.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    # Same meaning, different bytes: compact, CRLF, reordered keys.
    reordered = dict(reversed(list(document.items())))
    path.write_bytes(json.dumps(reordered, indent=4).replace("\n", "\r\n").encode("utf-8"))
    assert build_manifest(data_copy) == before


def test_a_value_change_changes_the_hash(data_copy: Path) -> None:
    before = build_manifest(data_copy)
    path = data_copy / "elements.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    document["Multipliers"]["Strong"] = 2
    path.write_text(json.dumps(document), encoding="utf-8")
    after = build_manifest(data_copy)
    assert after.data_version != before.data_version
    assert after.files["elements.json"] != before.files["elements.json"]
    assert after.files["monsters.json"] == before.files["monsters.json"]


def test_check_mode_detects_a_stale_manifest(data_copy: Path) -> None:
    assert _run("--data-dir", str(data_copy), "--check").returncode == 0
    (data_copy / "rarities.json").write_text('{"Common": {"name": "Common", "order": 1}}')
    stale = _run("--data-dir", str(data_copy), "--check")
    assert stale.returncode == 1
    assert "stale" in stale.stderr


def test_write_mode_regenerates_the_manifest(data_copy: Path) -> None:
    (data_copy / MANIFEST_FILE).unlink()
    assert _run("--data-dir", str(data_copy)).returncode == 0
    assert _run("--data-dir", str(data_copy), "--check").returncode == 0
