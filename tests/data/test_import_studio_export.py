"""The one-paste Studio import must reproduce the data files byte for byte."""

import subprocess
import sys
from pathlib import Path

import pytest

from app.data.manifest import DATA_FILES
from tests.conftest import DATA_DIR, REPO_ROOT

SCRIPT = REPO_ROOT / "scripts" / "import_studio_export.py"


def _studio_output(timestamps: bool = False) -> str:
    """Rebuild text shaped like a copy of Studio's Output window."""
    lines: list[str] = []
    counts: list[str] = []
    for name in DATA_FILES:
        body = (DATA_DIR / name).read_text(encoding="utf-8").rstrip("\n")
        lines += [f"===== data/{name} =====", *body.split("\n"), f"===== end {name} ====="]
        counts.append(f"{name}: {len(body)} chars")
    lines.append("[export] done. " + " | ".join(counts))
    prefix = "12:00:00.000  " if timestamps else "  "
    return "\n".join(f"{prefix}{line}  -  Edit" for line in lines)


def _run(source: Path, data_dir: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(source), "--data-dir", str(data_dir)],
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.parametrize("timestamps", [False, True], ids=["plain", "timestamps"])
def test_import_reproduces_committed_files(tmp_path: Path, timestamps: bool) -> None:
    paste = tmp_path / "output.txt"
    paste.write_text(_studio_output(timestamps), encoding="utf-8")
    out_dir = tmp_path / "data"
    out_dir.mkdir()

    result = _run(paste, out_dir)

    assert result.returncode == 0, result.stderr
    for name in [*DATA_FILES, "manifest.json"]:
        assert (out_dir / name).read_bytes() == (DATA_DIR / name).read_bytes(), name


def test_truncated_paste_writes_nothing(tmp_path: Path) -> None:
    paste = tmp_path / "output.txt"
    paste.write_text(_studio_output()[:20000], encoding="utf-8")
    out_dir = tmp_path / "data"
    out_dir.mkdir()

    result = _run(paste, out_dir)

    assert result.returncode == 1
    assert "cut off" in result.stderr
    assert not any(out_dir.iterdir())


def test_length_mismatch_is_rejected(tmp_path: Path) -> None:
    text = _studio_output().replace('"SellRatio": 0.5', '"SellRatio": 0.55')
    paste = tmp_path / "output.txt"
    paste.write_text(text, encoding="utf-8")
    out_dir = tmp_path / "data"
    out_dir.mkdir()

    result = _run(paste, out_dir)

    assert result.returncode == 1
    assert "items.json" in result.stderr
    assert not any(out_dir.iterdir())
