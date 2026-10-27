"""Write data/manifest.json, or check that the committed one is current.

Usage:
  python scripts/build_manifest.py           # regenerate data/manifest.json
  python scripts/build_manifest.py --check   # exit 1 if it is stale (CI gate)
"""

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from app.data.manifest import MANIFEST_FILE, build_manifest, render_manifest  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Build or check data/manifest.json")
    parser.add_argument("--data-dir", type=Path, default=REPO_ROOT / "data")
    parser.add_argument("--check", action="store_true", help="fail if the manifest is stale")
    args = parser.parse_args()

    manifest = build_manifest(args.data_dir)
    expected = render_manifest(manifest)
    path: Path = args.data_dir / MANIFEST_FILE

    if args.check:
        current = path.read_text(encoding="utf-8") if path.exists() else ""
        # Compare after normalising line endings: a Windows checkout may have CRLF.
        if current.replace("\r\n", "\n") != expected:
            print(
                f"FAIL {path.name} is stale; run: python scripts/build_manifest.py",
                file=sys.stderr,
            )
            return 1
        print(f"OK {path.name} is current (data version {manifest.data_version})")
        return 0

    path.write_text(expected, encoding="utf-8", newline="\n")
    print(f"Wrote {path.name} (data version {manifest.data_version})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
