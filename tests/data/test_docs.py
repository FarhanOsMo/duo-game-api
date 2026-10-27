"""The assignment's documentation rules, enforced in CI so an edit cannot quietly break them."""

import re
import subprocess
import sys

import pytest

from tests.conftest import REPO_ROOT

README_SECTIONS = [
    "Project Summary",
    "Problem Statement",
    "Why I Built This",
    "Technologies Used",
    "Architecture Overview",
    "Key Design Decisions",
    "Challenges and How I Solved Them",
    "Outcomes or Metrics",
]


@pytest.mark.parametrize(
    ("path", "low", "high"),
    [("docs/COVER_STATEMENT.md", 150, 200), ("docs/REFLECTION.md", 400, 600)],
)
def test_word_limits(path: str, low: int, high: int) -> None:
    result = subprocess.run(
        [sys.executable, "scripts/word_count.py", path, "--min", str(low), "--max", str(high)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout


def test_readme_has_required_sections_in_order() -> None:
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    headings = re.findall(r"^## (.+)$", readme, flags=re.MULTILINE)
    found = [h for h in headings if h in README_SECTIONS]
    assert found == README_SECTIONS


def test_relative_links_in_docs_resolve() -> None:
    """No broken links: every relative Markdown link points at a file that exists."""
    broken = []
    for doc in [REPO_ROOT / "README.md", *(REPO_ROOT / "docs").rglob("*.md")]:
        text = doc.read_text(encoding="utf-8")
        for target in re.findall(r"\]\(([^)#\s]+)(?:#[^)]*)?\)", text):
            if "://" in target or target.startswith("mailto:"):
                continue
            if not (doc.parent / target).exists():
                broken.append(f"{doc.relative_to(REPO_ROOT)} -> {target}")
    assert not broken, broken
