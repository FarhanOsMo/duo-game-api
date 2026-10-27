"""Count the words in a Markdown document's body and check them against a range.

The title line (a leading "# ...") is excluded because assignment word limits
apply to the statement itself. Markdown markup characters are not words.

Usage: python scripts/word_count.py docs/COVER_STATEMENT.md --min 150 --max 200
Exit code 1 when the count is outside the range.
"""

import argparse
import re
import sys
from pathlib import Path


def count_words(markdown: str) -> int:
    lines = markdown.splitlines()
    if lines and lines[0].startswith("# "):
        lines = lines[1:]
    text = "\n".join(lines)
    text = re.sub(r"`[^`]*`", lambda m: m.group(0).strip("`"), text)
    text = re.sub(r"[#*_>|\[\]()]", " ", text)
    # \u2019 is the typographic apostrophe, so both spellings of it's count as one word.
    return len(re.findall("[A-Za-z0-9][A-Za-z0-9'\u2019.\\-/%]*", text))


def main() -> int:
    parser = argparse.ArgumentParser(description="Word count with a range check")
    parser.add_argument("path", type=Path)
    parser.add_argument("--min", type=int, required=True)
    parser.add_argument("--max", type=int, required=True)
    args = parser.parse_args()

    words = count_words(args.path.read_text(encoding="utf-8"))
    ok = args.min <= words <= args.max
    print(
        f"{args.path.as_posix()}: {words} words (required {args.min}-{args.max}) "
        f"{'OK' if ok else 'OUT OF RANGE'}"
    )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
