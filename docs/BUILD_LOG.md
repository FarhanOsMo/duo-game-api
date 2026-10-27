# Build log

A running record of real problems hit while building this project and how each
was resolved. The README's "Challenges" section is drawn only from this file.

## P1: data import, models, validation, manifest

### The game data arrived as Output-window text, not files
The data was delivered as a copy of Roblox Studio's Output window. Every line
carried a 2-space indent and a trailing `  -  Edit` (the Output window's
source-location link), and the first marker line had lost its indent in the
copy. Rebuilding the eleven files by hand is exactly the slow, error-prone step
a content pipeline should remove.

**Resolution.** Wrote `scripts/import_studio_export.py`: it reads the clipboard
(or a file), finds the `===== data/<name>.json =====` markers, strips the
Output-window noise, and verifies every block against the exporter's own
`[export] done. <file>.json: <n> chars` line before writing anything. The
first manual reconstruction was checked the same way: all eleven files matched
the exporter's counts exactly (for example `monsters.json` 5350 chars). A test
rebuilds an Output-window paste from the committed files and asserts the import
reproduces them byte for byte; the user then ran it on a real clipboard copy
and `git diff -- data` was empty.

### Timestamp stripping ate the JSON indentation
The first version of the importer removed an optional Output-window timestamp
with `^\s*\d{1,2}:\d{2}:\d{2}\.\d{3}\s+`. The trailing `\s+` also swallowed
the JSON's own indentation, so every block came out shorter than the exporter's
count (`monsters.json: 3386 chars but the exporter printed 5350`). The
parametrised test with timestamps caught it.

**Resolution.** The pattern now removes only the timestamp digits. The
separator after a timestamp is identical on every line, so `textwrap.dedent`
removes it along with the Output indent, leaving JSON indentation intact.

### A field named `list` broke mypy
The `{"List": {...}}` wrappers were first modelled with a field literally named
`list`. Inside the class body that name shadowed the builtin, and mypy strict
rejected the next annotation (`flavors: list[str]`) with
`Variable "ItemsFile.list" is not valid as a type`.

**Resolution.** Renamed the field to `entries` with `Field(alias="List")`, so
Python code reads naturally and the JSON spelling is unchanged.

### Abilities that are not attacks
`abilities.json` contains a Field ability (`ess_ab_verdant_sense`) with no
`power`, `element`, `category` or `accuracy`, plus a `Heal` category ability
with power 20 (`ess_ab_soothing_rain`). A model that required battle fields
would reject valid game data, and a damage endpoint that only rejected
`power == 0` would treat a heal as a physical attack.

**Resolution.** Battle fields are optional in the model. The damage endpoint
accepts only `Physical` and `Magical` abilities with power above zero (see P3).

### The committed exporter is older than the one that produced the data
`tools/export_game_data.lua`, as provided, emits single-line
`HttpService:JSONEncode` output and ends with `[export] done: 11 files
exported`. The export actually pasted from Studio was pretty-printed with
sorted keys and ended with per-file character counts, so it came from a newer
version of the tool. The provided file must not be edited.

**Resolution.** Flagged to the project owner to replace the file with the
version used in Studio. The importer refuses output that has no character
counts and says why, rather than accepting a copy it cannot verify.
