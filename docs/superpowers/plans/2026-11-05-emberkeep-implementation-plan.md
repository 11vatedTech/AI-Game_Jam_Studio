# EMBERKEEP Reference Production — Implementation Plan

**Status:** approved for execution
**Governing specification:** `docs/superpowers/specs/2026-11-05-emberkeep-reference-production-design.md` (544 lines, commits `7a588fc`, `88422bf`, `c5c9683`)
**Rule:** the specification is not reopened. Open questions land here and in acceptance tests.

---

## 0. Carry-in requirements (from the approval)

| # | Requirement | Where satisfied |
|---|---|---|
| C1 | 3.0 s critic budget is **end-to-end** (decode + metrics + serialization), cold and warm, median/p95/p99/max, p95 is the gate | P3-T4, `scripts/quality/critic_bench.py` |
| C2 | Gates are interactive human operations **outside** agent tools; display exact hashes and direction revision; agent cannot approve its own work; chat fallback is explicitly weaker provenance | P7-T1/T2, `tests/test_review_gate.py`, MCP surface audit P7-T3 |
| C3 | ACE-Step **1.5** specifically, pinned source revision and checkpoints, per-component licence records, local REST service, 2B Turbo first, VRAM benchmarked, score and seamless loop reviewed separately | P6-T1..T5 |
| C4 | Git tracking and artifact storage established **before** production; build outputs and staging excluded; release hashes and reports preserved | P0-T1..T4 |

---

## 1. Phase dependency graph

```
P0 foundations ──┬── P1 art-direction contract ──┬── P3 critic v1 ──┐
                 └── P2 trace ledger ─────────────┘                 ├── P7 gates ── P8 evidence/distribution
P4 godot modularisation ── P5 package + acceptance ──────────────────┘              │
P6 music (independent of P1..P5) ───────────────────────────────────────────────────┘
P9 ACES capture runs continuously during P1..P8, closed out last
```

Blocking edges: P3 needs P1 (thresholds) and P2 (findings are ledger rows). P5 needs P4 (module split before export freeze). P7 needs P3 + P5. P8 needs all.

Every phase ends with a **Proof** command whose output is a committed artifact or a ledger row.

---

## P0. Foundations: tracking, storage, honest status

**Depends on:** nothing.

### T1 — Repository hygiene before any production file moves

- Create `.gitignore` entries: `Games/**/dist/`, `Games/**/.godot/`, `**/.import/`, `reports/evidence/_staging/`, `*.pdb`, `.venv/`, `__pycache__/`.
- Create `.gitattributes` with LFS filters for `*.blend`, `*.glb`, `*.png`, `*.ogg`, `*.wav`, `*.exr`.
- `git lfs install --local`; `git lfs track` the above patterns.
- **Known cost:** OneDrive-synced repo + LFS = duplicated storage. Record the decision and the measured `.git` growth; if growth exceeds 2 GB, switch to a hash-addressed artifact store (`studio artifacts` already hashes) instead of LFS for large binaries.

**Proof:** `git lfs ls-files | wc -l` > 0 and `git check-ignore Games/emberkeep/dist/x` exits 0.

### T2 — Commit the existing production sources

Commit `Games/` (source + game assets, not `dist/`), `docs/games/`, `scripts/audio/`, `scripts/blender/`, `scripts/pipelines/`, `workflows/`.

Do **not** commit: the two pre-existing modified files (`scripts/linux/bootstrap.sh`, `scripts/verify_repo.py`) — they are unrelated to this production and stay dirty until their owner resolves them.

**Proof:** `git status --short` shows only those two modified files.

### T3 — Correct the stale status document

`PROJECT_STATUS.md` currently claims v0.2.0 is not installed on the workstation. Replace with the measured state: 37 passed / 1 skipped, ComfyUI v0.34.0 at 127.0.0.1:8188, Godot 4.7.2 pinned, export templates present, assets manufactured (numbers from `Games/emberkeep/source/assets/*/*.ingest.json`).

**Proof:** every numeric claim in the file traces to a command or an ingest JSON.

### T4 — Binary artifact baseline hashes

Register existing binaries through `ArtifactStore.register` into a single job row (`P0-BASELINE`) so every later change is diffable.

**Proof:** `studio artifacts list --job-id <P0 job>` returns ≥ 12 rows with sha256.

**Exit criteria:** clean tree except the two pre-existing modifications; LFS active; baseline hashes recorded.

---

## P1. Art-direction contract (hash-bound)

**Depends on:** P0.

### T1 — Schema

`schemas/art-direction.schema.json` — JSON Schema 2020-12, required keys: `schema_version`, `production`, `revision`, `threshold_status`, `palette.base` (exactly 6), `palette.roles` (6 named), `thresholds.{silhouette,warm_share,horizon_roll,delta_e_max,clutter,lantern_dominance,consistency}`, `references[]` with `id`/`path`/`sha256`, `capture.{resolution,legibility_resolution,fov_deg}`.

Reject: unknown top-level keys (`additionalProperties: false`), `threshold_status: "confirmed"` without a `calibration` block.

### T2 — Loader and validator

`src/elevenvt_studio/quality/art_direction.py`

```python
@dataclass(frozen=True)
class ArtDirection:
    revision: str
    sha256: str
    threshold_status: str            # "provisional" | "confirmed"
    thresholds: Mapping[str, Mapping[str, Any]]
    palette: tuple[str, ...]
    roles: Mapping[str, int]
    references: tuple[Reference, ...]

def load(path: Path) -> ArtDirection: ...          # raises ValidationError with JSON path of the failure
def assert_reference_hashes(direction: ArtDirection, base: Path) -> None: ...
```

Validation must fail loudly on: wrong palette length, a `roles` index out of range, a reference whose sha256 does not match the file on disk, `threshold_status` unset.

### T3 — Content

`Games/emberkeep/art_direction.json`, `revision: "1.0.0"`, `threshold_status: "provisional"`, palette copied verbatim from `ART_BIBLE.md` §3, thresholds from the spec §4.2 table.

### T4 — Hash binding and invalidation

`src/elevenvt_studio/quality/binding.py`:

```python
def bind(direction: ArtDirection, frames: Sequence[FrameRef]) -> str   # returns direction_sha256 + frames_digest
def approvals_valid_for(conn, gate: int, direction: ArtDirection, frames) -> bool
```

Rule: any change to `art_direction.json` or to an approved frame hash invalidates Gate 1 and Gate 2 records for that production. Implemented as a query over `reviews.evidence_json` comparing stored digests — no mutable "valid" flag.

**Proof:** `python -c "from elevenvt_studio.quality import art_direction; print(art_direction.load(Path('Games/emberkeep/art_direction.json')).sha256)"`

**Tests:** `tests/test_art_direction.py` — 8 cases: valid load, missing key, bad palette length, role index out of range, reference hash mismatch, confirmed-without-calibration, revision bump invalidates approval, unrelated file change does not.

**Exit criteria:** contract loads, all negatives fail with a JSON-path message, invalidation proven by test.

---

## P2. Trace ledger and failure taxonomy

**Depends on:** P0. Feeds P3.

### T1 — Migration to schema 2

`src/elevenvt_studio/db.py`: `SCHEMA_VERSION = 2`; add `MIGRATIONS = {2: _migrate_2}`; the constructor applies migrations in order and refuses to downgrade. New tables:

```sql
CREATE TABLE operations (
  id TEXT PRIMARY KEY, job_id TEXT, task_id TEXT, kind TEXT NOT NULL,
  boundary TEXT NOT NULL,          -- agent | mcp | cli | engine | human
  target TEXT NOT NULL,            -- tool/app/model identity
  started_at TEXT NOT NULL, finished_at TEXT, outcome TEXT NOT NULL,  -- ok | failed | denied | uncertain
  request_digest TEXT, response_digest TEXT, inputs_json TEXT, outputs_json TEXT,
  failure_class TEXT, notes TEXT
);
CREATE TABLE critic_findings (
  id TEXT PRIMARY KEY, job_id TEXT NOT NULL, frame TEXT NOT NULL,
  metric TEXT NOT NULL, value REAL, threshold_json TEXT NOT NULL,
  severity TEXT NOT NULL,            -- blocker | major | minor | note
  algorithm_version TEXT NOT NULL, confidence REAL,
  limitations_json TEXT NOT NULL, evidence_json TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE decisions (
  id TEXT PRIMARY KEY, job_id TEXT, question TEXT NOT NULL, decision TEXT NOT NULL,
  rationale TEXT NOT NULL, alternatives_json TEXT, made_by TEXT NOT NULL,
  evidence_json TEXT NOT NULL, created_at TEXT NOT NULL
);
```

### T2 — Taxonomy

`src/elevenvt_studio/quality/taxonomy.py` — the 10 classes as an enum with a one-line detection rule each: `ENVIRONMENT`, `DEPENDENCY`, `INPUT_INVALID`, `POLICY_DENIED`, `TOOL_PROTOCOL`, `MODEL_QUALITY`, `PARAMETER`, `TIMEOUT`, `RESOURCE_EXHAUSTED`, `UNKNOWN`. `classify(exc, context) -> FailureClass` must return `UNKNOWN` rather than guess.

### T3 — Ledger writer

`src/elevenvt_studio/ledger.py`

```python
class Ledger:
    def start(self, *, kind: str, boundary: str, target: str, inputs: dict) -> str
    def finish(self, op_id: str, *, outcome: str, outputs: dict | None = None,
               failure: BaseException | None = None) -> None
    def context(self, **kw) -> AbstractContextManager[str]   # auto-classifies on exception, never swallows
```

Digests only — never raw bytes, never secrets. A redaction test asserts that a dict containing `api_key` is stored with the value replaced.

### T4 — CLI

`studio ledger list --job-id`, `studio ledger show <op_id>`, `studio ledger gaps --job-id` (operations with `outcome=uncertain` or missing `finished_at`).

**Tests:** `tests/test_ledger.py` (7), `tests/test_migration_v2.py` (v1 DB with rows → migrate → rows intact + new tables present + `user_version=2`).

**Proof:** `studio ledger gaps --job-id <id>` returns `[]` for a completed job.

**Exit criteria:** migration is idempotent and reversible-by-backup; every adapter call in `src/elevenvt_studio/adapters/` is wrapped by `Ledger.context`.

---

## P3. Critic v1 and its benchmark gate

**Depends on:** P1, P2.

### T1 — Metrics

`src/elevenvt_studio/quality/metrics.py`, one function per metric, each declaring `ALGORITHM_VERSION`, `CONFIDENCE`, `LIMITATIONS`:

- `luminance_percentiles(img)` — linearise sRGB (IEC 61966-2-1), p1/p5/p50/p95/p99.
- `warm_share(img, mask, band)` — numerator passing HSV `hue 20–45°, sat ≥ 0.25, val ≥ 0.20`; denominator **all** world pixels after sky/UI exclusion.
- `silhouette(i_with, i_without, region)` — IoU + perceptual delta of player-alone vs player-removed frames in the same region.
- `horizon_roll(img, camera)` — projected-plane horizon from camera transforms, not a Hough guess; falls back to `confidence=0.0` if the horizon is off-frame.
- `palette_delta_e(img, palette)` — CIELAB ΔE2000 against the 6 declared swatches.
- `clutter(img)` — edge density + saliency sum outside the focal region.
- `lantern_dominance(img)` — brightest-cluster location and whether it falls inside the lantern mask.
- `event_consistency(frames, events)` — expected visual delta per timeline event.

Masking: the game emits a mask PNG per capture (`STUDIO_SHOT_MASK`) so metric code never guesses sky.

### T2 — Critic

`src/elevenvt_studio/quality/critic.py`

```python
def evaluate(frames: Sequence[Frame], direction: ArtDirection) -> CriticReport
```

Reads thresholds from the direction object only. Severity from the JSON `blocker_below`/`major_below` bands. Writes `critic_findings` rows and `reports/quality/<job>/critic.json` matching `schemas/quality-report.schema.json` (extend that schema with `frames[].metrics[]`).

### T3 — Calibration set

12 frames in `reports/evidence/productions/emberkeep/01-direction/references/` with human labels in `calibration/labels.json` (severity per metric per frame, plus the reviewer's notes). Calibration report `reports/quality/calibration.json` reports per-metric accuracy; a metric disagreeing by >1 severity on any frame blocks Gate 1.

### T4 — Benchmark (C1)

`scripts/quality/critic_bench.py`

- Input: 24 PNGs at 1920×1080 from real captures, listed in `bench/frames.lock.json` (hashes).
- Times **end-to-end**: file read → PNG decode → all metrics → `CriticReport` JSON written to disk.
- Runs: 1 cold (fresh process, cold page cache where possible), 20 warm per frame.
- Emits median/p95/p99/max per frame and aggregate, plus machine identity (CPU model, RAM, GPU, OS build) and library versions.
- **Gate:** aggregate p95 ≤ 3000 ms. On failure: profile (`cProfile` + per-metric timings already emitted), identify the top bottleneck, then apply escalation ladder §14.2 — first with a faster library call (e.g. `cv2` over `skimage`), documenting baseline → change → measurement. Only then consider pybind11/C++.

**Proof:** `reports/evidence/productions/emberkeep/02-manufacture/critic_bench.json` + one paragraph in the evidence bundle naming the rung used.

**Tests:** `tests/test_metrics.py` (synthetic images with known warm share, known ΔE, flat frame, single bright dot), `tests/test_critic_thresholds.py` (threshold change flips verdict; no threshold literal in code — grep test).

**Exit criteria:** critic runs on 24 real frames, p95 measured and recorded; every finding carries algorithm version/confidence/limitations.

---

## P4. Godot modularisation and capture contract

**Depends on:** P0.

`Games/emberkeep/game/scripts/main.gd` (713 lines) splits into:

| File | Responsibility |
|---|---|
| `core/state.gd` | progression model, beacon states, win condition |
| `core/director.gd` | beat sequencing, timeline events |
| `world/beacons.gd` | ignition, light falloff, event emission |
| `world/terrain.gd` | shrine terrace, props, pylon placement |
| `player/controller.gd` | movement, lantern carry |
| `camera/rig.gd` | framing, horizon guarantees, Gate 1 shot positions |
| `ui/hud.gd` | prompts, objective text |
| `audio/feedback.gd` | sfx triggers, ambience bus |
| `test/smoke.gd` | `STUDIO_SMOKE_JSON`, `STUDIO_SHOT`, `STUDIO_SHOT_MASK`, `STUDIO_EVENTS` |

Capture contract (consumed by the critic): every shot writes PNG + mask PNG + a sidecar JSON with camera transform, FOV, resolution, frame index, timeline event, and engine version.

**Proof:** `godot --headless --quit-after 2 -- --smoke` exits 0 and emits 4 shots + 4 masks + sidecars.

**Tests:** headless smoke run asserted by `tests/test_godot_smoke.py` (skipped with a clear reason if Godot is absent).

**Exit criteria:** no file over 250 lines; smoke identical in behaviour to the pre-split build (`state=WON`).

---

## P5. Package and staged acceptance

**Depends on:** P4.

### T1 — Export

`scripts/release/build_package.py`

- Reads pinned engine path + template dir from config, never from PATH.
- `godot --headless --export-release "Windows Desktop" Games/emberkeep/dist/emberkeep.exe`
- Produces: `emberkeep.exe`, `emberkeep.pck`, `README.txt`, `THIRD_PARTY_NOTICES.md`, `LICENSES/` (Godot MIT, font/audio/model licences as cleared), `sha256sums.txt`.

### T2 — Staging and staged run

Copy to a fresh temp dir **outside** the source tree (`%TEMP%\emberkeep-accept-<uuid>`), run from there, capture screenshot/state/events/perf, then delete the staging dir. The acceptance report records the staging path and that it was outside the repository.

### T3 — Acceptance suite

`scripts/release/acceptance.py` — assertions:

1. Package completeness + hashes verified against `sha256sums.txt`.
2. Launch from staging, reach `state=WON` within 10 minutes.
3. All three beacons ignitable, in order, with the expected events.
4. Frame time: p95 ≤ 16.7 ms at 1920×1080, max ≤ 50 ms; separate 1280×720 legibility leg.
5. Critic pass on the 5 release frames at the approved direction hash.
6. No error/warning lines in Godot log.
7. Determinism: two runs produce identical event sequences.

Runs as a persisted job: `studio job create <spec> && studio job run <id> --approval-id <id>`; the verdict is a `reviews` row of type `release`, produced by the job, marked `PASS_PENDING_SUBJECTIVE_REVIEW` — never `CERTIFIED`.

**Failure handling:** each assertion maps to a taxonomy class; a failed run writes a defect list to `reports/evidence/productions/emberkeep/03-acceptance/defects.json` and does not retry automatically (retry masks flakiness).

**Exit criteria:** acceptance passes from staging on a machine path unrelated to the repo.

---

## P6. Music via ACE-Step 1.5 (C3)

**Depends on:** nothing (parallel).

- **T1 Discovery:** record pinned source revision, model checkpoint identities, and per-component licence records (code, DiT, language model, vocoder) in `reports/evidence/productions/emberkeep/02-manufacture/audio/LICENCES_ACE.json`. A project-level MIT claim is recorded as *insufficient* for each component unless the component's own record confirms it.
- **T2 Service:** `scripts/audio/ace_step.py` wraps a local REST service (Python 3.11–3.12), pinned at the recorded revision; refuses to run on a different revision.
- **T3 VRAM benchmark:** 2B Turbo + 0.6B LM first (CPU offload/quantisation as needed), then 1.7B LM if it fits; log peak VRAM per configuration. 4B XL is explicitly out of scope for this production.
- **T4 Outputs:** `dawn_score.ogg` (~75 s, instrumental) and `dawn_loop.ogg` (seamless; verified by end-to-end waveform continuity + spectral check, not by ear alone). Prompts, seeds, settings, model versions, source hashes recorded per file.
- **T5 Review:** score and loop reviewed separately by a human (Gate 2 evidence); failure falls back to the ambience bed labelled sound design, and the deliverable says so.

**Exit criteria:** two cleared audio assets with provenance, or a documented fallback.

---

## P7. Human gates (C2)

**Depends on:** P3 (Gate 1), P5 (Gate 2).

### T1 — Interactive gate command

`studio review gate --gate 1 --job-id <id>`:

- Requires a real TTY (`sys.stdin.isatty()`); exits 2 otherwise, so it cannot be driven by an agent through a pipe.
- Prints the exact `art_direction.json` sha256, revision, `threshold_status`, and every artifact sha256 under review.
- Requires the operator to type the first 8 hex characters of the direction hash to confirm. No `--yes` flag exists.
- Writes a `reviews` row with `reviewer` from the OS user, `evidence_json.method = "cli-interactive"`, the typed confirmation, and timestamp.

### T2 — Chat fallback, weak by construction

If the operator cannot run the CLI, the record is written with `method: "chat-transcription"`, `confidence: "weak"`, and the verbatim quoted approval. The acceptance report and `PROJECT_STATUS.md` must state which method was used per gate.

### T3 — MCP surface audit

Audit `src/elevenvt_studio/mcp/server.py` and `sdk_server.py`: no tool may approve, decide approvals, or write a `reviews` verdict. Add `tests/test_mcp_no_self_approval.py` asserting the tool inventory contains none of `approv*`, `review*`, `gate*`, `certif*` beyond read-only listing.

**Exit criteria:** agent cannot produce an approval; test proves it; gate output includes hashes.

---

## P8. Distribution and evidence

**Depends on:** P5, P6, P7.

- Key art: in-engine hero render at 1920×1080 (`reports/evidence/productions/emberkeep/04-distribution/keyart.png`) + title treatment; no generated composition.
- 5 screenshots in the approved order, each with the same sidecar contract as captures.
- `Games/emberkeep/README.md`: what it is, how to run, controls, 5–10 minute expectation, licence and attribution notes, known limitations.
- `reports/evidence/productions/emberkeep/SUMMARY.md`: the claim ledger — what was manufactured, what was verified by machine, what was reviewed by a human, and what remains unverified.

**Exit criteria:** every claim in the README traces to an artifact or a gate record.

---

## P9. ACES capture and retrospective

**Depends on:** P1–P8, runs continuously.

Emit `decisions`, `operations` and `critic_findings` rows for every real choice and failure, including the ones already made (pylon floor artifact, degenerate mesh from square framing). Close out with `docs/games/emberkeep/RETROSPECTIVE.md`: which Studio capabilities were load-bearing, which were missing, which were theatre. That document — not the architecture docs — is the input to the ACES gap analysis.

---

## 2. Verification gates summary

| Gate | Command | Pass condition |
|---|---|---|
| Unit | `python -m pytest -q` | 0 failures; new tests ≥ 25 |
| Contract | `pytest tests/test_art_direction.py tests/test_critic_thresholds.py` | all pass |
| Ledger | `studio ledger gaps --job-id <id>` | `[]` |
| Critic bench | `python scripts/quality/critic_bench.py` | aggregate p95 ≤ 3000 ms |
| Godot smoke | `godot --headless ... --smoke` | exit 0, 4 shots + masks |
| Acceptance | `studio job run <id>` on staged package | all 7 assertions pass, verdict `PASS_PENDING_SUBJECTIVE_REVIEW` |
| Gate 1 / Gate 2 | `studio review gate --gate N` | interactive, hash-confirmed, human reviewer |

## 3. Scope guards

- No pause menu, save system, settings screen, multiplayer, or additional levels (spec §12).
- No second engine, no C++ gameplay code, no GDExtension without a §14.2 record.
- No new architecture documents; this plan and the evidence bundle are the only documents produced.
- If a phase blocks for more than one working session, record a `decisions` row with the blocker and continue with the next independent phase rather than idling.

## 4. Reporting cadence

After each phase: one message with the proof command output, the artifacts created, defects found, and the next phase. No phase is reported as complete without its proof output.
