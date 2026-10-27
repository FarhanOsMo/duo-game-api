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

## P5: CI/CD and security scanning

### Pinning actions to commit SHAs
Tags on third-party actions can be moved by whoever controls the action's
repository, so a tag is not an immutable reference. Two of the release tags
(`aquasecurity/trivy-action` v0.36.0 and `softprops/action-gh-release` v3.0.3)
turned out to be annotated tags whose object SHA is the tag, not the commit.

**Resolution.** Resolved every action's latest release through the GitHub API
and dereferenced annotated tags to their commit SHAs. Workflows reference the
commit SHA with the version as a comment; Dependabot updates both.

### Trivy findings in the base image
Trivy 0.76.1 reported 44 HIGH/CRITICAL CVEs in the Debian 13.7 packages of the
`python:3.12.16-slim-trixie` base image, none of which has a fixed package
available. Python dependencies were clean.

**Resolution.** The gate fails only on HIGH/CRITICAL findings that have a fix
(`ignore-unfixed: true`): those are actionable by updating, while unfixed ones
cannot be resolved from this repository and would block every build. The full
list is still printed in the CI log. Moving to a distroless or minimal base
image is listed as future work. pip was also removed from the runtime
virtualenv to shrink the scan surface.

### Windows wrote CRLF into a generated file
The pre-commit `mixed-line-ending` hook rejected the generated Grafana
dashboard: Python's stdout on Windows translates `\n` to `\r\n` when output
is redirected to a file.

**Resolution.** The hook normalised the file to LF, and `.gitattributes`
(`* text=auto eol=lf`) already guaranteed the committed copy was LF, which is
why `git diff` showed no change. The repo's own scripts that write files
(`build_manifest.py`, `import_studio_export.py`) pass `newline="\n"`
explicitly, so they produce identical bytes on every OS.

### Local pre-commit hooks depended on the active shell
The data-validation hooks first used `language: system`, so they ran whatever
`python` was on PATH at commit time; outside the virtualenv that interpreter
had no pydantic and the hook would fail.

**Resolution.** Switched them to `language: python` with
`additional_dependencies: [pydantic==2.14.1]`, so pre-commit builds an
isolated environment and the hooks behave the same from any terminal.

### Verifying the pipeline without pushing
The repository is not on GitHub yet, so the workflows cannot run there.

**Resolution.** Every gate was run locally with the same pinned tool versions:
actionlint 1.7.12 (clean), gitleaks 8.30.1 over the git history (no leaks),
Trivy 0.76.1 against the built image (exit 0 under the CI policy), pip-audit
(no known vulnerabilities) and all pre-commit hooks. The GitHub-only parts
(GHCR push, environments, approval gate) are verified on the first real run.

## P6: load test

### The first saturation point was a single worker, not the code
Under light traffic (about 30 requests per second from
`scripts/generate_traffic.py`) the server-side p95 on the Grafana dashboard
was 4.67 ms. The Locust run (50 users, 60 s) pushed about 279 requests per
second with zero failures, but server-side p95 rose to 96.8 ms and p99 to
212.7 ms. Every endpoint is in-memory, so the time was spent queueing: the
container runs one Uvicorn process, and Python executes one request's CPU
work at a time in that process.

**Resolution.** Recorded as a measured capacity figure rather than tuned away,
because 280 requests per second on a laptop is far beyond a balance tool's
needs. The README states it with the machine and command, the 250 ms p95
alert threshold was confirmed to sit above this worst case, and horizontal
scaling (more workers or replicas, which a stateless service allows) is in
the improvement plan.

## P6: documentation and the portfolio PDF

### The architecture diagram would not lay out
A PDF cannot render Mermaid, so the README diagram was rendered to PNG with
`minlag/mermaid-cli`. The first version was a single left-to-right chain about
13 nodes wide, unreadable at page width. Splitting it into three stages with
`direction LR` inside each produced a single tall column instead: Mermaid
ignores a subgraph's `direction` whenever an edge links a node inside it to a
node outside it, and the long stage titles were also truncated.

**Resolution.** Edges now connect whole stages (`Content --> Release -->
Runtime`) rather than nodes across stages, and the titles were shortened.
The same Mermaid source renders on GitHub and as `docs/images/architecture.png`
for the PDF.

## P7: final review

### A log filter hid two Grafana errors
Checking Grafana's logs earlier, I filtered out lines mentioning "plugin" to
cut through startup noise. The final fresh-clone run, checked without that
filter, showed two real errors: a missing `provisioning/plugins` folder, and
Grafana 13 failing to auto-install a bundled Elasticsearch plugin
(`permission denied`).

**Resolution.** Added the plugins provisioning folder (with a README, like the
alerting one) and set `GF_PLUGINS_PREINSTALL_DISABLED=true`, since the
dashboard uses only core panels and the stack should not need the internet to
start. A clean start now logs zero error lines. Lesson recorded: verify a
"clean" result with the broadest check, not a filtered one.

### Uvicorn's colour codes in JSON logs
Running the API outside Docker showed uvicorn attaching a `color_message`
field containing terminal escape codes to every startup log line.

**Resolution.** The JSON formatter now drops `color_message`; the plain
`message` field already carries the same text.
