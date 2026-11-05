# EMBERKEEP Reference Production — Design Specification

**Status:** `APPROVED_PENDING_USER_REVIEW`
**Date:** 2026-11-05
**Spec version:** 1.0.0
**Production ID:** `emberkeep`
**Supersedes:** the informal vertical-slice work under `Games/emberkeep/` (retained as source, not as a deliverable)

---

## 0. Governing constraints

These bind every decision in this document. They are not aspirations; a change that violates one is a defect in the work, not a trade-off.

1. **Generating is not producing.** No deliverable is claimed because a file exists. Every claim carries a measurement, taken in the environment that consumes the artifact.
2. **No invisible execution.** Every production operation is recorded at the execution boundary — identity, agent, capability, inputs, permission, result, outputs, hashes, provenance, read-back, critique, repair.
3. **No self-certification.** The build agent and the critic may reach `PASS` and `PASS_PENDING_SUBJECTIVE_REVIEW`. Only a human review record may reach `CERTIFIED`.
4. **Thresholds are project law, not universal law.** Every numeric quality gate comes from the approved, versioned `art_direction.json` for this production.
5. **Artifact-hash binding.** Approvals bind to artifact hashes and the art-direction hash. If an approved artifact materially changes, its approval is invalid.
6. **Agent-agnostic product scope.** This pilot is hosted by Freebuff, but the Studio must not encode Freebuff-specific assumptions into its interfaces, registry, or ledger. Emberkeep validates the platform; it does not define it.
7. **Emberkeep is a pilot, not the Studio.** Completion of this production proves the orchestration loop. It proves nothing about disciplines and interfaces explicitly deferred in §12.

---

## 1. Scope and exit criteria

### 1.1 Deliverable

A complete, runnable **Windows x64 distribution package**, not a bare executable.

```
Games/emberkeep/dist/windows-x64/emberkeep/
  emberkeep.exe                 # Godot 4.7.2 export (or renamed binary)
  emberkeep.pck                 # game data package (separate, not embedded)
  README.txt                    # controls, objective, requirements, restart key
  THIRD_PARTY_NOTICES.md        # engine + model + font + library notices
  LICENSES/                     # verbatim licence texts
  sha256sums.txt                # hashes of every file in the package
```

Plus the **editable sources**, retained and registered:

- `Games/emberkeep/game/` — full Godot project, importable and runnable from source
- `Games/emberkeep/source/assets/<asset>/` — `.blend` originals, `.glb` exports, `.ingest.json` measurements
- `Games/emberkeep/source/concepts/` — generated concept art with generation manifests
- `Games/emberkeep/source/audio/` — synthesis scripts and rendered `.ogg`
- `docs/games/emberkeep/ART_BIBLE.md` and `art_direction.json`

### 1.2 Experience requirement

The build must be a coherent five-to-ten-minute experience, not three mechanics joined by a level. Required beats, each with observable evidence:

| # | Beat | Evidence |
|---|---|---|
| 1 | **Arrival vista** — the drowned shrine-city reads as a place, not a plane | Frame at t≈3 s; critic composition + horizon checks |
| 2 | **Orientation** — controls and goal legible without external instructions | HUD present in frame; text is legible at 1280×720 |
| 3 | **Warmth taught** — the lantern dims, a mote restores it, feedback is unmistakable | Emission/audio event log; warmth trace |
| 4 | **Three beacon objectives** — three distinct positions, each with a distinct approach | Beacon lit events ×3 with timestamps |
| 5 | **Progression toward dawn** — sky, fog and light visibly change per beacon | Three captured frames, measured luminance/fog deltas |
| 6 | **Dawn conclusion** — a decisive end state, not a silent stop | End-state frame + `state=WON` evidence |
| 7 | **Restart path** — one key restores a clean run | Restart event + second `state` transition in the same session |

Audio: ambience bed, ignition, chime, dawn cue — each triggered by a named event and audible in the recorded run.

### 1.3 Exit states

Every artifact family ends in exactly one state:

- `FAIL` — at least one objective check failed; defect records required
- `PASS` — all objective checks passed; no human review yet
- `PASS_PENDING_SUBJECTIVE_REVIEW` — objective checks passed and the critic's subjective calls are documented and unrefuted
- `CERTIFIED` — a human review record exists, bound to artifact hashes and art-direction hash

Delivery requires `CERTIFIED` on the package, the art direction, and the acceptance report.

### 1.4 Environment of record

| Item | Value |
|---|---|
| Engine | Godot `4.7.2.stable.official.ed1daf0bf` |
| Export templates | `4.7.2.stable` full set (verified present, 2.0 GB) |
| OS | Windows, local workstation `C:\Users\11vat` |
| GPU | NVIDIA RTX 5070 Ti Laptop, 12 227 MiB |
| CPU / RAM | 24 logical CPUs / 33.7 GB |
| Renderer | Forward+ |
| Capture | 1920×1080 release frames; 1280×720 legibility leg |
| Performance target | 60 FPS at 1920×1080 (ART_BIBLE §12), asserted as p95 frame time ≤ 16.7 ms |

Any change to these invalidates performance figures and requires re-measurement.

---

## 2. Art-direction contract

### 2.1 `art_direction.json`

Location: `Games/emberkeep/source/art_direction.json`
Schema: `schemas/art_direction.schema.json` (JSON Schema draft 2020-12)
Instances are **versioned** (`version: "1.0.0"`) and **hashed**; every frame, critique report and approval record carries `art_direction_sha256`.

Required content:

```jsonc
{
  "version": "1.0.0",
  "production": "emberkeep",
  "threshold_status": "provisional",   // becomes "confirmed" after calibration review
  "palette": {
    "base": ["#0B1016", "#1C2B33", "#3E5A63", "#D8CDBA", "#FFC168", "#FF7A2F"],
    "roles":  { "ink": 0, "slate": 1, "mist": 2, "bone": 3, "lantern": 4, "ember": 5 },
    // hexes are copied verbatim from docs/games/emberkeep/ART_BIBLE.md §3; the art bible is authoritative
    "derived_rules": { "max_delta_e2000_per_role": 14, "lighting_derivation_allowed": true }
  },
  "measurement": {
    "render_profile": "1080p_forward_plus_capture",
    "color_space": "sRGB_encoded_frames",
    "luminance_conversion": "IEC_61966-2-1_inverse_EOTF",
    "exposure": "engine_default_no_manual_override",
    "tonemap": "filmic",
    "excluded_layers": ["ui", "debug_overlay"],
    "bloom_included": false
  },
  "metrics": {
    "warm_share":     { "hue_deg": [20, 45], "sat_min": 0.25, "val_min": 0.20,
                        "region": "world_only_excluding_sky_and_ui",
                        "denominator": "all_world_pixels_after_exclusions",
                        "ceiling": 0.10 },
    "horizon":        { "reference_plane_y_m": 0.0,
                        "acceptable_screen_band": [0.28, 0.42],
                        "method": "project_plane_through_camera" },
    "focal_luminance":{ "focal_objects": ["lantern", "beacon_flame"],
                        "statistic": "masked_p95_linear_luminance",
                        "min_ratio_vs_scene_p50": 2.0 },
    "silhouette":     { "thumbnail_sizes_px": [128, 256],
                        "isolation_pass": "player_only_mask",
                        "min_contrast_ratio": 4.5 },
    "clutter":        { "region": "centre_third",
                        "edge_density_max": 0.18,
                        "saliency_density_max": 0.22 },
    "palette":        { "space": "CIELAB_D65", "difference": "CIEDE2000",
                        "area_weighted": true,
                        "max_mean_delta_e": 12.0, "max_p95_delta_e": 22.0 }
  },
  "consistency": {
    "events": ["arrival", "first_beacon", "dawn"],
    "properties": ["light_direction", "exposure_p50", "palette_distribution"]
  },
  "references": [
    { "id": "ref-arrival-01",
      "path": "reports/evidence/productions/emberkeep/01-direction/references/arrival_01.png",
      "sha256": "<sha256 of the approved reference frame>" }
  ]
}
```

Rules:

- The critic **reads** these values. It must not contain hard-coded thresholds.
- Changing any threshold requires a new `version` and a new approval; the critic records which version produced each finding.
- Reference images are registered artifacts with hashes; the calibration set (§4.6) is drawn from them.

### 2.2 Approval binding and invalidation

An approval record stores: `subject_kind`, `subject_id`, `artifact_hashes[]`, `art_direction_sha256`, `spec_version`, `reviewer`, `decision`, `reason`, `timestamp`.

Invalidation is automatic: if any bound artifact hash changes, the approval is marked `INVALIDATED` and the artifact family returns to `PASS_PENDING_SUBJECTIVE_REVIEW`. There is no override flag. Re-approval requires a new human review row.

---

## 3. Production loop

| Stage | Output | Verification |
|---|---|---|
| 1. Direction | `art_direction.json` v1.0.0 + art bible | Schema validation; Gate 1 |
| 2. Design language | shape/palette/typography rules in art bible | critic rubric loaded from the JSON |
| 3. Manufacture | concepts (ComfyUI), meshes (Blender), audio (synthesis) | ingest measurements, read-back, op records |
| 4. Integration | Godot scene assembly | asset presence, node hierarchy, material/scale read-back |
| 5. Critique | `critique.json` per frame set | metric algorithm versions + thresholds hash |
| 6. Refinement | corrections at the originating stage | re-render + re-score + regression check |
| 7. Acceptance | staged-package run + report | acceptance job persisted |
| 8. Gates | Gate 1 (direction), Gate 2 (delivery) | human review rows, hash-bound |

**Gate 1** happens before further lighting/asset spend: four candidate framings of the arrival view, rendered at 1280×720, each with critic scores attached, presented together. The human picks one; the pick is recorded with hashes. The chosen framing becomes the composition contract for beats 1 and 6.

**Gate 2** happens after the staged build runs. The reviewer sees the package, the acceptance report, the screenshot set, and the critic's unrefuted findings, then signs or returns specific defects.

Refinement rule: a defect is fixed at the stage that produced it. A composition defect is not repaired by adding fog; a topology defect is not repaired by decimation.

---

## 4. Critic v1

Module: `scripts/critic/`
Inputs: rendered frames (PNG), a scene report emitted by the game (`scene_report.json`: camera transform, FOV, screen-space boxes for player/lantern/beacons, horizon plane height), and `art_direction.json`.
Output: `critique.json` — findings array plus `summary`.

### 4.1 Finding record

Every finding carries all seven fields. Missing fields make the finding invalid and the critique fails schema validation.

```jsonc
{
  "id": "C-004",
  "observation": "The lower 38% of the arrival frame carries no readable surface or light.",
  "measurement": { "metric": "silhouette.contrast", "value": 2.1, "threshold": 4.5,
                   "algorithm": "critic.silhouette@1.0.0", "inputs_sha256": "..." },
  "requirement": "art_direction.metrics.silhouette.min_contrast_ratio",
  "severity": "blocker",            // blocker | major | minor | note
  "diagnosis": "Camera is positioned off the terrace, so the frame's lower half is unlit water at grazing angle.",
  "correction": { "stage": "camera_rig", "operation": "reposition_and_pitch",
                  "parameters": { "offset_z": 8.6, "pitch_deg": -16 } },
  "verification": { "status": "passed", "after_critique": "C-004v2",
                    "regressions": [] },
  "confidence": 0.93
}
```

Subjective findings add `reasoning`, `criteria_applied`, `alternatives_considered`, `confidence`.

### 4.2 Metrics and their contracts

| Metric | Method (algorithm version) | Known limitation |
|---|---|---|
| Silhouette | Isolation pass renders the player alone on the real background; compare masked grayscale at 128 and 256 px thumbnails via RMS contrast ratio | Meaningless when the player is legitimately off-camera; the critic must check `scene_report.player_visible` first |
| Luminance | sRGB → linear via IEC 61966-2-1 inverse EOTF; compare masked p95 of focal objects against masked p50 of the scene | Bloom is excluded from measurement by contract, so apparent glow in-game exceeds the measured value |
| Warm share | HSV classification (`hue 20–45°`, `sat ≥ 0.25`, `val ≥ 0.20` — the art bible's 90/10 law, §3); numerator is pixels passing classification, denominator is **every** world pixel after sky and UI exclusion. (Using the classified set as the denominator would force the ratio to 1.0 and make the metric vacuous.) | Underground/interior scenes would need a different ceiling — this is why it lives in the JSON |
| Horizon | Project the declared world horizon plane (`y = 0`) through the camera matrix; the projected line's screen-y must land inside the band | A deliberately tilted or obstructed horizon is a design change requiring a new art-direction version, not a critic exception |
| Palette | sRGB → CIELAB (D65); area-weighted histogram matched to the six base colours with CIEDE2000; lighting-derived colours counted against the nearest role with the `derived` budget | Small emissive areas are under-weighted by area weighting; composite with luminance findings |
| Clutter | Normalized Sobel edge density **plus** object/saliency density in the centre third (count of distinct salient blobs per unit area) | High-detail stone reads as clutter if the threshold is tuned to flat surfaces |
| Consistency | Compare named events on light direction (from scene report), exposure p50, palette distribution | Fewer than the declared events means `insufficient_evidence`, not `pass` |

### 4.3 Repair verification

A repair finding is only closed when:

1. the correction was executed at the declared stage (op record exists),
2. the new frame is re-scored with the same algorithm version and threshold hash,
3. the target metric improved past threshold,
4. **all other metrics did not regress by more than 1 severity level**,
5. the pair (before, after) is stored in `reports/evidence/productions/emberkeep/05-repair/`.

### 4.4 Authority limits

The critic cannot emit `CERTIFIED`, cannot edit `art_direction.json`, and cannot close a subjective finding without either human review or an explicit documented judgement (reasoning + criteria + alternatives + confidence) in the record.

### 4.5 Calibration

Before Gate 2, the critic is calibrated against a human-reviewed reference set:

- 12 frames spanning arrival, mid-run, three beacon states, dawn, plus deliberate near-miss variants
- Human assigns severity per frame and per metric
- Critic must agree on blockers and majors within one severity level; misses are recorded as calibration error in the report
- Calibration results are themselves evidence, stored at `reports/evidence/calibration/emberkeep/`

A critic that fails calibration produces `PASS_PENDING_SUBJECTIVE_REVIEW` at best, with the calibration gap stated.

### 4.6 Threshold provenance

Thresholds enter the JSON with `threshold_status: "provisional"`. The calibration report carries the same status and is the only place that may flip it to `"confirmed"`, after a human reviews the reference set. Universal statements ("warm share must never exceed 10%") are forbidden anywhere in the codebase; every ceiling is read from the versioned artifact at run time.

---

## 5. Trace ledger

### 5.1 Principle

The ledger is written by the **execution boundary** (adapter wrapper / CLI runner), not by the script being executed. A script may emit an intent record; the wrapper validates it, performs or observes the operation, performs independent read-back, and writes the authoritative record. Self-reported success without read-back is recorded as `unverified`.

### 5.2 Schema (SQLite, `user_version` 1 → 2)

`operations`:

| Column | Content |
|---|---|
| `operation_id` | ULID, primary key |
| `job_id`, `task_id`, `parent_operation_id` | lineage |
| `agent_id`, `agent_model`, `agent_version` | who requested it (Freebuff today, any agent later) |
| `capability_id`, `adapter`, `tool`, `tool_version` | what was used |
| `inputs_json`, `inputs_sha256`, `config_version` | validated input snapshot |
| `permission_decision`, `approval_id`, `execution_scope` | security |
| `started_at`, `finished_at`, `status`, `exit_code`, `error_class` | execution |
| `outputs_json` | `[{path, artifact_id, sha256, bytes}]` |
| `provenance_json` | source, model, workflow, dependencies, rights |
| `postcondition_json`, `readback_status` | verification |
| `critique_ref`, `repair_of_operation_id`, `repair_resolved` | quality linkage |

`operation_events`: `event_id`, `operation_id`, `event` (`requested|approved|started|completed|failed|cancelled|timed_out|reconciled`), `at`, `detail_json`.

### 5.3 Failure classification (required taxonomy)

`error_class` is one of:

1. `agent_knowledge` — the host agent lacked required domain knowledge
2. `agent_reasoning` — wrong plan or decision, tools were adequate
3. `capability_missing` — no capability exists for the task
4. `adapter_failure` — integration/transport/contract error
5. `application_defect` — the application itself misbehaved
6. `permission_denied` — policy or approval blocked the operation
7. `resource_constraint` — VRAM, RAM, disk, time, thermal
8. `requirement_ambiguous` — the brief did not determine the answer
9. `quality_failure` — operation succeeded, output unacceptable
10. `licensing_blocker` — rights prevent use
11. `unknown` — must be reconciled by a human; never counted as agent failure

This taxonomy is the foundation for ACES (§13). Misclassifying 5 as 1 would make the Studio conclude the host agent is incompetent because Blender crashed.

### 5.4 Protected data

Prompts, credentials and private content are not stored verbatim by default. `inputs_json` stores a redacted form with `redacted: true` and hashes of the originals. Anything requiring retention goes to a protected store declared in the security policy, never to the ledger.

### 5.5 Migration, backup, restore, recovery

Required for this production, because the schema changes for the first time:

- Forward migration `1 → 2` executed as one transaction, preceded by an automatic online backup
- Rollback = restore the pre-migration backup; verified by a drill, not asserted
- Restore drill: backup → restore to scratch path → `PRAGMA integrity_check` → row-count equality → migration idempotency
- Duplicate/retry detection: identical `(job_id, task_id, inputs_sha256)` within a window marks the second attempt `duplicate_suspected` and requires explicit resolution
- Interrupted operations: on startup, any `started` operation with no terminal event is marked `uncertain` and cannot be blindly replayed; `studio job reconcile` requires evidence
- Evidence reconciliation: an `uncertain` op is closed only by read-back against the declared outputs (hashes match → `completed`, absent → `failed`)

---

## 6. Game engineering

### 6.1 Module boundaries

`main.gd` (713 lines) is replaced by components with observable contracts:

| Module | Responsibility | Testable surface |
|---|---|---|
| `core/game_state.gd` | phase machine, beacon counts, win/lose | `state_snapshot() -> Dictionary` |
| `core/warmth.gd` | warmth model, drain, restore, clamps | `warmth_tick(dt)`, `restore(amount)` |
| `player/player_controller.gd` | movement, input mapping | position, velocity |
| `player/lantern.gd` | light energy ↔ warmth coupling | `light_energy()` |
| `world/world_builder.gd` | terrace, arches, backdrop, placement | node manifest |
| `world/beacon.gd` | objective state, ignition emission | `is_lit()`, signal |
| `camera/camera_rig.gd` | rig, pitch, follow, framing | transform |
| `ui/hud.gd` | warmth bar, beacon counter, prompts | text state |
| `audio/audio_feedback.gd` | event → sound mapping | emitted event log |
| `test/smoke_harness.gd` | headless drive + assertions + screenshots | JSON report |

Splitting is by responsibility so that behaviour is testable through public methods, not by file count.

### 6.2 Warmth invariants (replacing "globally monotonic")

1. `0.0 ≤ warmth ≤ 1.0` at every sampled frame
2. With no restorative source active and no game pause, warmth decreases at the declared rate within ±2% tolerance
3. A valid mote restores exactly the declared amount, capped at 1.0, and cannot double-apply to the same mote
4. Repeated or invalid interaction, and frame-rate variation (test at 30/60/144 FPS caps), cannot create unintended warmth
5. Phase transitions occur exactly once per condition; `WON` implies three lit beacons; `LOST` implies warmth reached 0

Assertion source: the harness samples `state_snapshot()` each frame and writes a trace; a Python checker validates the invariants against the trace rather than trusting the game's own verdict.

### 6.3 Manufactured content only

No primitive geometry or canvas/SVG-style placeholder art ships as final content. Every visible mesh in the delivery traces to a registered asset with a `.blend` original and a `.glb` export, or to an authored shader documented in the art bible. Primitive proxies are permitted only as measured dev scaffolding and must be absent from the shipped scene (asserted by the acceptance suite: node manifest vs. registered asset list).

---

## 7. Performance protocol

Fixed configuration, recorded with every result:

- **1920×1080** windowed (the art bible's acceptance resolution), Forward+, VSync off, no debug overlay, plugged-in power profile recorded by name
- A secondary 1280×720 legibility check runs the same clock, because ART_BIBLE §12 requires the frame to survive at gameplay distance *and* at detail
- 10 s warm-up excluded; 180 s continuous sampling in a scripted run
- Per-frame times captured to CSV (`frame_index`, `dt_ms`), not inferred from an FPS counter
- Report p50, p95, p99, max, mean FPS, plus CPU/GPU identity and driver version
- Assertion: `p95 ≤ 16.7 ms` and `max ≤ 50 ms` (no hitch above three frames)

A miss is a `FAIL` with a defect record; it is never rounded into a pass.

---

## 8. Packaged-build acceptance

The pipeline below runs as one persisted Studio job. Steps 3–9 operate on the **staged copy**, outside the source tree.

1. Export Windows x64 candidate with the pinned engine and `4.7.2.stable` templates
2. Stage to `%LOCALAPPDATA%\11vatedTech\AI-Game-Jam-Studio\acceptance\emberkeep-<hash8>\`
3. Verify package completeness: `.exe`, `.pck`, `README.txt`, `THIRD_PARTY_NOTICES.md`, `LICENSES/`, `sha256sums.txt` all present; hashes match; the packaged run reports the pinned engine version
4. Launch the staged build (not the project directory)
5. Drive the required experience — arrival, warmth, three beacons, dawn, restart
6. Inspect logs: zero script errors, zero missing-resource errors, audio device opened
7. Verify objectives and ending from the run's own state trace
8. Capture the five release screenshots at defined beats
9. Persist the acceptance report (JSON) as job output; register package + hashes
10. Set exit state per §1.3

Explicitly rejected as evidence: "the export command returned 0", "the exe exists", "the project runs from source".

---

## 9. Evidence layout

```
reports/evidence/productions/emberkeep/
  00-spec/          this document + hash
  01-direction/     art_direction.json + schema validation + Gate 1 record + candidates
  02-manufacture/   per-asset op records, ingest JSON, Blender renders, concept manifests
  03-integration/   import logs, node manifests, read-back results
  04-critique/      critique.json per frame set, calibration report
  05-repair/        before/after pairs, regression results
  06-acceptance/    job id, acceptance_report.json, frame-time CSV, logs, screenshots
  07-delivery/      package manifest, sha256sums, gate records, notices
```

Every file in this tree is registered as an artifact with SHA-256 and provenance.

---

## 10. What this production must prove (and what it must not claim)

Proves:
- the Studio can orchestrate a real multi-application production (ComfyUI → Blender → Godot → export → staged run)
- every operation is traceable at the execution boundary
- an independent critic can measure art-direction compliance and drive a repair loop
- a packaged artifact can be tested as a package, not as a project
- approvals bind to hashes and expire when artifacts change

Does **not** prove:
- universal creative capability
- that adapters are production-hardened beyond the operations exercised here
- that subjective quality is automatable
- anything about disciplines or interfaces listed in §12

---

## 11. Risks

| Risk | Mitigation |
|---|---|
| Godot script/parse errors under warnings-as-errors | module split + headless import gate before every run |
| Visual quality is judged poor at Gate 1/2 | Gate 1 before expensive work; four framings; critic scores attached |
| Critic thresholds mis-tuned | provisional flag, calibration set, human confirmation |
| Runner/session interruption mid-production | state lives in repo artifacts, not chat; each stage ends with registered evidence |
| Export template mismatch | versions pinned and verified before export; failure is `adapter_failure`, not agent failure |
| Scope creep into menus/save/combat | explicitly out of scope (§12) |

---

## 12. Deferred (tracked in the parent Studio roadmap, not dropped)

| ID | Item | Home |
|---|---|---|
| D-01 | ACES gap-analysis engine | sub-project after this pilot |
| D-02 | API + SDK servers (MCP + CLI exist) | parent roadmap |
| D-03 | Adapter depth: Blender/Godot read-back contracts far beyond this pilot, cancellation, ComfyUI WebSocket streaming, workflow schema validation | parent roadmap |
| D-04 | DCC-MCP Core / AI Game Dev pinned evaluation | parent roadmap |
| D-05 | Additional engines (Unreal, Unity) | parent roadmap |
| D-06 | Disciplines beyond games+3D+2D+audio: video, CAD, web/app, writing, research | parent roadmap |
| D-07 | Reusable pipeline extraction (P4) | after this pilot |
| D-08 | Model routing, resource scheduling, memory, autonomous repair at scale (P6) | parent roadmap |
| D-09 | Save system, settings menu, accessibility pass, localisation | out of scope entirely for this pilot |
| D-10 | Trailer, store page, marketing renders beyond the key art and five screenshots | parent roadmap |

The exclusion of these items does not weaken the governing product requirement: **any compatible AI agent must be able to use the Studio's accumulated knowledge, skills, pipelines, integrations, models, quality intelligence and manufacturing capability to produce substantially better work than it could alone.**

---

## 13. ACES substrate (built now, engine later)

Built during this production:

- **Capability registry** (`catalogs/runtime/capabilities.json`) extended with stable competency IDs (`3d.asset.ingest`, `3d.asset.author`, `2d.concept.generate`, `audio.sfx.synthesize`, `engine.godot.build`, `engine.godot.acceptance`, `quality.critic.frame`)
- **Agent identity record** on every operation (`agent_id`, model, version, available interfaces)
- **Structured execution history** (§5) with success/failure classification
- **Critic findings and repair outcomes** linked to operations
- **Skill/knowledge injection points**: declared paths (`skills/`, `context/`) that a host agent can be pointed at, with provenance
- **Artifact and workflow provenance** for everything registered

Deferred to the ACES spec: profiling which competencies a given agent lacks, routing to specialist models, and adaptive assistance. Those need this history to exist first, and they must learn from successes as well as failures.

---

## 14. Definition of done

1. `dist/windows-x64/emberkeep/` exists, complete, hash-listed, and runs from outside the repo
2. Acceptance job persisted with `CERTIFIED` or an explicit defect list
3. Five release screenshots captured from the staged build
4. Critic critique and calibration stored; no unrefuted blocker
5. Two human gates recorded, bound to hashes, invalidated correctly when artifacts change
6. Op ledger populated for every production operation, with read-back, no `unknown` classes left unreconciled
7. Migration + backup + restore drill evidence present
8. `PROJECT_STATUS.md` updated with the honest state, including anything that failed
