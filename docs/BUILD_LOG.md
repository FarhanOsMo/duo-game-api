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

## P2: domain formulas

All Appendix B golden values passed on the first run. mypy strict flagged
`(level - 1) ** exponent`: `int ** float` is typed as returning `Any` (a
negative base could produce a complex number), which leaked `Any` out of a
function declared to return `int`.

**Resolution.** Switched to `math.pow(level - 1, exponent)`, which is typed
`float` and is the same operation as Lua's `^` for the non-negative bases the
formula uses. The golden values confirmed the results did not change.

## P3: API

### TestClient deprecation warning
With FastAPI 0.162 / Starlette 1.10 every test run printed
`StarletteDeprecationWarning: Using httpx with starlette.testclient is
deprecated; install httpx2 instead.` Silencing the warning would have hidden a
future breakage.

**Resolution.** Replaced `httpx` with `httpx2` in `requirements-dev.txt`,
uninstalled `httpx`, confirmed `pip check` was clean and the full suite
(132 tests) passed with no warnings.

### Unknown element names: game semantics versus API usability
The game's `getMultiplier` returns 1.0 for an unknown element. Over HTTP that
would turn a typo (`?attack=Fier`) into a plausible but wrong answer.

**Resolution.** The pure domain function keeps the game's behaviour (and is
tested for it), while `/elements/effectiveness` returns a 404 for names not in
`elements.json`. The decision is commented in `app/api/compute.py`.

## P4: containers and observability

### Alert-rule unit test compared annotations too
`promtool test rules` failed for `HighLatencyP95` even though the alert fired
correctly (p95 975 ms): promtool compares expected annotations exactly, and
the test case listed only labels.

**Resolution.** Added the expected `summary` and `description` to the test
case. All five alert-rule test cases now pass, including the ones proving
that healthy traffic and zero traffic do not fire.

### Grafana logged an error for a missing alerting folder
Grafana 13 logged `can't read alerting provisioning files from directory
... /etc/grafana/provisioning/alerting: no such file or directory` at every
start, even though alerting is intentionally done in Prometheus.

**Resolution.** Added `deploy/grafana/provisioning/alerting/` with a README
(Grafana only reads `.yaml` files there) explaining that Prometheus is the
single source of truth for alerts. Restarted Grafana and confirmed the error
no longer appears.

### Dashboard stat panels lost their units
The first real screenshot showed the p95 stat as `0.00465` and the 5xx stat
as a bare `0`. The script that generates the dashboard JSON replaced each
panel's `fieldConfig.defaults` when adding thresholds, which dropped the
`unit` setting.

**Resolution.** The generator now merges threshold settings into the
existing defaults. The regenerated dashboard shows `4.67 ms` and `0%`, and
the screenshot in `docs/images/` was retaken from the running stack.

### Taking a real screenshot without a manual login
Grafana requires a login, and a headless browser cannot complete one.

**Resolution.** For the screenshot only, Grafana was restarted with a
throwaway Compose override (kept outside the repo) that enables read-only
anonymous viewing, captured with headless Chrome in kiosk mode while
`scripts/generate_traffic.py` ran, and then restarted from the committed
configuration. A follow-up request confirmed anonymous access was off again.
