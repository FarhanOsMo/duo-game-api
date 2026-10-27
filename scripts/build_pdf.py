"""Build Mohamed_Farhan_Portfolio.pdf: title page, repo URL, cover statement,
the README case study and the reflection.

Usage:
  pip install -r requirements-docs.txt
  python scripts/build_pdf.py [--repo-url URL] [--output PATH]

The repository URL defaults to the `origin` git remote, so once the GitHub repo
exists the PDF picks up the real URL with no edits. Without a remote it falls
back to a clearly marked placeholder and prints a warning.

Uses Markdown + xhtml2pdf (pure Python) so it runs the same on Windows, macOS
and Linux. Fallback if it cannot run: open README.md on GitHub (or in VS Code's
Markdown preview) and use the browser's Print > Save as PDF.
"""

import argparse
import re
import subprocess
import sys
from datetime import date
from html import escape
from pathlib import Path

import markdown
from xhtml2pdf import pisa

REPO_ROOT = Path(__file__).resolve().parents[1]
PLACEHOLDER_URL = "https://github.com/<your-username>/duo-game-api"
AUTHOR = "Mohamed Farhan"

CSS = """
@page { size: letter; margin: 2cm 2cm 2cm 2cm;
        @frame footer { -pdf-frame-content: footer; bottom: 1cm; margin-left: 2cm;
                        margin-right: 2cm; height: 1cm; } }
body { font-family: Helvetica; font-size: 10pt; line-height: 1.4; color: #1f2328; }
h1 { font-size: 20pt; color: #0b3d63; margin: 0 0 6pt 0; }
h2 { font-size: 14pt; color: #0b3d63; border-bottom: 1px solid #c8d1dc;
     padding-bottom: 2pt; margin-top: 14pt; -pdf-keep-with-next: true; }
h3 { font-size: 11.5pt; color: #0b3d63; margin-top: 10pt; -pdf-keep-with-next: true; }
p, li { margin: 0 0 5pt 0; }
code { font-family: Courier; font-size: 8.5pt; background-color: #f2f4f7; }
pre { font-family: Courier; font-size: 7.5pt; background-color: #f2f4f7;
      border: 1px solid #d8dee4; padding: 5pt; }
table { border: 1px solid #c8d1dc; margin: 4pt 0 8pt 0; }
th { background-color: #e8eef5; font-weight: bold; padding: 3pt; text-align: left; }
td { padding: 3pt; vertical-align: top; border-top: 1px solid #e1e6ec; }
a { color: #0b5cad; text-decoration: none; }
.title-page { text-align: center; padding-top: 120pt; }
.title-page h1 { font-size: 26pt; }
.subtitle { font-size: 14pt; color: #444; margin-top: 8pt; }
.meta { font-size: 11pt; margin-top: 30pt; line-height: 1.8; }
.warning { color: #b42318; font-weight: bold; }
.footer { font-size: 8pt; color: #777; text-align: center; }
"""

# Helvetica in the PDF has no box-drawing glyphs, so the project tree is drawn in ASCII.
_ASCII_TREE = {"├──": "|--", "└──": "`--", "│": "|"}


def repo_url_from_git() -> str | None:
    try:
        url = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    if url.startswith("git@github.com:"):
        url = "https://github.com/" + url.removeprefix("git@github.com:")
    return url.removesuffix(".git") or None


def case_study_markdown(readme: str, repo_url: str) -> str:
    """The README from Quick Start through Outcomes, adapted for print."""
    start = readme.index("## Quick Start")
    end = readme.index("## Developer guide")
    text = readme[start:end]
    owner = repo_url.rstrip("/").split("/")[-2]
    if "<" not in owner:
        text = text.replace("<your-username>", owner)
    # Mermaid cannot render in a PDF; use the pre-rendered PNG of the same diagram.
    text = re.sub(
        r"```mermaid\n.*?```",
        "![Architecture diagram](docs/images/architecture.png)",
        text,
        flags=re.DOTALL,
    )
    for fancy, plain in _ASCII_TREE.items():
        text = text.replace(fancy, plain)
    return text


def strip_title(md_text: str) -> str:
    return re.sub(r"\A# .*\n", "", md_text)


def _wrap_code_lines(md_text: str, width: int = 100) -> str:
    """xhtml2pdf cannot wrap <pre>, so hard-wrap long lines inside fenced code blocks."""

    def wrap_block(match: re.Match[str]) -> str:
        lines = []
        for line in match.group(2).split("\n"):
            while len(line) > width:
                lines.append(line[:width])
                line = "    " + line[width:]
            lines.append(line)
        return match.group(1) + "\n".join(lines) + match.group(3)

    return re.sub(r"(```[^\n]*\n)(.*?)(```)", wrap_block, md_text, flags=re.DOTALL)


def to_html(md_text: str) -> str:
    html = markdown.markdown(
        _wrap_code_lines(md_text), extensions=["tables", "fenced_code", "sane_lists"]
    )
    # Resolve relative image paths against the repo so xhtml2pdf can load them,
    # sized to the full text width of the page.
    return re.sub(
        r'<img alt="([^"]*)" src="(?!https?:)([^"]+)"',
        lambda m: (
            f'<img alt="{m.group(1)}" src="{(REPO_ROOT / m.group(2)).as_posix()}" width="500"'
        ),
        html,
    )


def build_html(repo_url: str) -> str:
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    cover = strip_title((REPO_ROOT / "docs" / "COVER_STATEMENT.md").read_text(encoding="utf-8"))
    reflection = strip_title((REPO_ROOT / "docs" / "REFLECTION.md").read_text(encoding="utf-8"))
    url_html = f'<a href="{escape(repo_url)}">{escape(repo_url)}</a>'
    if repo_url == PLACEHOLDER_URL:
        url_html += (
            '<br/><span class="warning">Placeholder: add the GitHub remote and rebuild.</span>'
        )

    return f"""<html><head><meta charset="utf-8"/><style>{CSS}</style></head><body>
<div id="footer" class="footer">{AUTHOR} | Duo Game Data API | page <pdf:pagenumber/></div>

<div class="title-page">
  <h1>Professional DevOps Portfolio</h1>
  <div class="subtitle">Curated Capstone Showcase: Option B, New Artifact</div>
  <div class="subtitle"><b>Duo Game Data API</b></div>
  <div class="meta">
    {AUTHOR}<br/>
    Repository: {url_html}<br/>
    {date.today().strftime("%B %d, %Y").replace(" 0", " ")}
  </div>
</div>
<pdf:nextpage/>

<h1>Cover Statement</h1>
{to_html(cover)}
<p><b>Repository:</b> {url_html}</p>
<pdf:nextpage/>

<h1>Case Study: Duo Game Data API</h1>
{to_html(case_study_markdown(readme, repo_url))}
<pdf:nextpage/>

<h1>Reflection</h1>
{to_html(reflection)}
</body></html>"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the portfolio PDF")
    parser.add_argument("--repo-url", default=None, help="defaults to the origin git remote")
    parser.add_argument("--output", type=Path, default=REPO_ROOT / "Mohamed_Farhan_Portfolio.pdf")
    args = parser.parse_args()

    repo_url = args.repo_url or repo_url_from_git() or PLACEHOLDER_URL
    if repo_url == PLACEHOLDER_URL:
        print(f"WARNING using placeholder repo URL {PLACEHOLDER_URL}", file=sys.stderr)

    with args.output.open("wb") as handle:
        result = pisa.CreatePDF(build_html(repo_url), dest=handle, encoding="utf-8")
    if result.err:
        print(f"FAIL xhtml2pdf reported {result.err} error(s)", file=sys.stderr)
        return 1
    print(
        f"Wrote {args.output.name} ({args.output.stat().st_size // 1024} KB), repo URL {repo_url}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
