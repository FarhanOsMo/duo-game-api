"""Content hashing for the data folder.

The hash is computed over canonical JSON (parsed, then re-serialised with
sorted keys and fixed separators), not over raw bytes. Data reaches the repo by
copy and paste out of Studio's Output window, so indentation, trailing
newlines and CRLF/LF differences are noise. Only a change in meaning (a value,
a key, an entry) should produce a new data version.

The manifest deliberately has no timestamp: it must be a pure function of the
data so CI can regenerate it and fail the build if the committed copy differs.
"""

import hashlib
import json
from pathlib import Path
from typing import Any

from app.data.models import Manifest

MANIFEST_FILE = "manifest.json"
MANIFEST_SCHEMA_VERSION = 1

# The eleven files the Studio exporter produces. Listed explicitly (not
# globbed) so a stray file in data/ cannot silently change the data version.
DATA_FILES: tuple[str, ...] = (
    "abilities.json",
    "config.json",
    "elements.json",
    "encounter_areas.json",
    "encounter_tables.json",
    "essences.json",
    "items.json",
    "monsters.json",
    "personalities.json",
    "rarities.json",
    "status_effects.json",
)


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def file_digest(path: Path) -> str:
    parsed = json.loads(path.read_text(encoding="utf-8"))
    return hashlib.sha256(canonical_json(parsed)).hexdigest()


def build_manifest(data_dir: Path) -> Manifest:
    files = {name: file_digest(data_dir / name) for name in DATA_FILES}
    # Hash the sorted (name, digest) pairs so renaming a file also counts as a change.
    combined = "".join(f"{name}\0{digest}\n" for name, digest in sorted(files.items()))
    content_sha256 = hashlib.sha256(combined.encode("utf-8")).hexdigest()
    return Manifest(
        schema_version=MANIFEST_SCHEMA_VERSION,
        data_version=content_sha256[:12],
        content_sha256=content_sha256,
        files=files,
    )


def render_manifest(manifest: Manifest) -> str:
    return json.dumps(manifest.model_dump(), indent=2, sort_keys=True) + "\n"
