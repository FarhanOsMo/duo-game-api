"""Turn one paste of Studio's Output window into the data/ files.

The exporter prints every file between marker lines. Copying the Output
window adds noise: a leading indent, optional timestamps, and a trailing
"  -  Edit" on each line. Doing that cleanup by hand for eleven files is slow
and error prone, so this script does it and verifies the result:
  * every block must parse as JSON,
  * every block's length must equal the exporter's own "[export] done" count,
  * all eleven files must be present,
and only then are any files written. Nothing is written on failure.

Usage (copy the whole Output window first, then run ONE of these):
  python scripts/import_studio_export.py                      # reads the clipboard
  python scripts/import_studio_export.py studio_output.txt    # or a saved text file
"""

import argparse
import json
import re
import sys
import textwrap
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from app.data.manifest import DATA_FILES, MANIFEST_FILE, build_manifest, render_manifest  # noqa: E402

_START = re.compile(r"^=====\s*data/(?P<name>[\w.]+\.json)\s*=====$")
_END = re.compile(r"^=====\s*end\s+(?P<name>[\w.]+\.json)\s*=====$")
_COUNT = re.compile(r"(?P<name>[\w.]+\.json):\s*(?P<chars>\d+)\s*chars")
# Studio's Output window can prefix a timestamp ("12:34:56.789  ") and the copy
# adds a trailing "  -  Edit" (a source-location link) to every line. Only the
# timestamp digits are removed here: the whitespace after them is the same on
# every line, so dedent() strips it later without eating JSON's own indentation.
_TIMESTAMP = re.compile(r"^\s*\d{1,2}:\d{2}:\d{2}\.\d{3}")
_EDIT_SUFFIX = re.compile(r"\s+-\s+Edit\s*$")


def _clean(line: str) -> str:
    return _EDIT_SUFFIX.sub("", _TIMESTAMP.sub("", line.rstrip("\r\n")))


def parse_output(text: str) -> tuple[dict[str, str], dict[str, int]]:
    """Return ({file name: JSON text}, {file name: exporter char count})."""
    blocks: dict[str, str] = {}
    counts: dict[str, int] = {}
    current: str | None = None
    buffer: list[str] = []
    for raw in text.splitlines():
        line = _clean(raw)
        stripped = line.strip()
        if current is None:
            if start := _START.match(stripped):
                current, buffer = start["name"], []
            elif stripped.startswith("[export] done"):
                counts.update({m["name"]: int(m["chars"]) for m in _COUNT.finditer(stripped)})
            continue
        if (end := _END.match(stripped)) and end["name"] == current:
            # dedent removes the indent the Output window adds while keeping JSON's own indent.
            blocks[current] = textwrap.dedent("\n".join(buffer)).strip("\n")
            current = None
        else:
            buffer.append(line)
    if current is not None:
        raise ValueError(f"block for {current} has no end marker; was the paste cut off?")
    return blocks, counts


def check_blocks(blocks: dict[str, str], counts: dict[str, int]) -> list[str]:
    problems = [f"{name}: missing from the paste" for name in DATA_FILES if name not in blocks]
    problems += [f"{name}: not a known data file" for name in blocks if name not in DATA_FILES]
    for name, body in blocks.items():
        try:
            json.loads(body)
        except json.JSONDecodeError as exc:
            problems.append(f"{name}: invalid JSON at line {exc.lineno}: {exc.msg}")
        if name in counts and len(body) != counts[name]:
            problems.append(f"{name}: {len(body)} chars but the exporter printed {counts[name]}")
    if not counts:
        # Without the exporter's own counts there is no way to prove the copy is complete,
        # so refuse rather than risk committing a silently truncated file.
        problems.append(
            "no character counts found on an '[export] done' line; copy the whole Output "
            "window, and use the exporter version that prints '<file>.json: <n> chars'"
        )
    return problems


def read_clipboard() -> str:
    # tkinter ships with the standard Python installers on Windows and macOS, so
    # reading the clipboard needs no extra dependency and no shell-specific piping
    # (PowerShell 5.1 pipes re-encode text, which can corrupt non-ASCII characters).
    import tkinter

    root = tkinter.Tk()
    root.withdraw()
    try:
        return str(root.clipboard_get())
    finally:
        root.destroy()


def main() -> int:
    parser = argparse.ArgumentParser(description="Import a Studio Output paste into data/")
    parser.add_argument(
        "source", nargs="?", help="text file with the pasted Output (default: the clipboard)"
    )
    parser.add_argument("--data-dir", type=Path, default=REPO_ROOT / "data")
    args = parser.parse_args()

    if args.source is None:
        try:
            text = read_clipboard()
        except Exception as exc:  # no display, empty clipboard or tkinter missing
            print(
                f"FAIL could not read the clipboard ({exc}). Paste the Output into a text "
                "file and run: python scripts/import_studio_export.py that_file.txt",
                file=sys.stderr,
            )
            return 1
    else:
        text = Path(args.source).read_text(encoding="utf-8-sig")
    try:
        blocks, counts = parse_output(text)
    except ValueError as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        return 1
    problems = check_blocks(blocks, counts)
    if problems:
        print("FAIL nothing was written:", *problems, sep="\n  - ", file=sys.stderr)
        return 1

    for name, body in blocks.items():
        (args.data_dir / name).write_text(body + "\n", encoding="utf-8", newline="\n")
    manifest = build_manifest(args.data_dir)
    (args.data_dir / MANIFEST_FILE).write_text(
        render_manifest(manifest), encoding="utf-8", newline="\n"
    )
    print(f"OK wrote {len(blocks)} files; data version {manifest.data_version}")
    print("Next: python scripts/validate_data.py, then open a pull request.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
