# Project Status — Executable Foundation 0.2.0, now proven on the workstation

**Snapshot:** 2026-11-05. **Target:** `11vatedTech/AI-Game_Jam_Studio`. **Truth status:** Installed and running on the user's Windows workstation. The runtime suite passes there, ComfyUI is live and has manufactured assets, and Godot 4.7.2 has produced a playable slice. Adapters remain uncertified in the formal sense; see the workstation evidence below.

## Verified on this workstation (2026-11-05)

| Fact | Value | How it was measured |
|---|---|---|
| Runtime tests | 159 passed, 1 skipped, 22.74 s | `PYTHONPATH=src .venv/Scripts/python.exe -m pytest -q` |
| The skip | `tests/test_paths.py:19` — symlink creation unavailable | Windows lacks the privilege without developer mode; not a runtime defect |
| Python | 3.12.10 in `.venv` | `studio doctor` |
| Host | RTX 5070 Ti 12 227 MiB, 24 CPUs, 33.7 GB RAM | `studio doctor` |
| ComfyUI | v0.34.0, 939 nodes, `127.0.0.1:8188` | live health + node inventory |
| Models present | flux-2-klein-4b-fp8, z_image_turbo, hunyuan_3d_v2.1, wan2.1, PixelartSpritesheet | `studio doctor` model inventory |
| Godot | `4.7.2.stable.official.ed1daf0bf`, export templates `4.7.2.stable` present | `godot --version`, template directory listing |
| Manufactured assets | pylon 13 999 tris (2.831 × 2.736 × 3.600 m), lamplighter 2 159 tris, architecture kit 4 346 tris / 49 objects, lantern hero ≈4.6k tris | `Games/emberkeep/source/assets/*/*.ingest.json` |
| Manufactured audio | `ambience.ogg` 48 s, `ignite.ogg`, `chime.ogg`, `dawn.ogg` | `Games/emberkeep/game/assets/audio/` |
| Playable slice | headless smoke exits 0, `state=WON`, 4 screenshots | `reports/evidence/runs/emberkeep-smoke/runtime_report.json` |
| Packaged build | **not yet produced** — export templates downloaded but never invoked | no `dist/` artifact exists |

## Verified in this build environment

| Area | Status | Evidence / exact boundary |
|---|---|---|
| Product specification | DESIGNED | `docs/00`–`docs/15`; full design/research/quality/discipline taxonomy retained |
| Python runtime package | IMPLEMENTED | `src/elevenvt_studio`; Python 3.11+; core has no mandatory third-party dependencies |
| CLI | IMPLEMENTED | `studio` commands: init/status/doctor/capabilities/job/artifacts/quality/approvals/mcp |
| SQLite persistence | IMPLEMENTED / HARDENING REQUIRED | Jobs, tasks, events, artifacts, approvals and human reviews persisted; schema version guard (`PRAGMA user_version=1`), integrity check and online backup implemented; future-version DBs are rejected; migration framework and restore drills remain open |
| DAG job executor | IMPLEMENTED / SEQUENTIAL | DAG validation, output refs, checkpoints, per-job cross-process lock, approval resume and crash/uncertain-side-effect quarantine; human-only `job reconcile` supports evidence-backed retry or mark-succeeded; no parallel scheduler, project locks or cancellation yet |
| Policy/approvals | IMPLEMENTED / HARDENING REQUIRED | Versioned default-deny policy, exact scope/side-effect/target binding, expiry, pending-only decision, CLI-only human approval; audit hardening remains |
| Workspace confinement | IMPLEMENTED / TESTED | Relative paths, traversal and symlink checks; no-overwrite file creation; OS-specific edge cases need Windows validation |
| Artifact integrity | IMPLEMENTED | Sidecar manifest, streaming SHA-256 verify, explicit unknown-by-default rights, human artifact review CLI; domain validators still incomplete |
| Resource profile | IMPLEMENTED / PARTIAL | OS/CPU/disk and NVIDIA `nvidia-smi`; RAM via optional psutil; not a global reservation daemon |
| MCP stdio server | IMPLEMENTED / HOST NOT YET VERIFIED | Production bridge uses official MCP Python SDK v2 (`mcp>=2,<3`) for protocol revision `2026-07-28` and legacy interoperability; CI has SDK integration tests; Freebuff workstation connection must still be reproduced. The legacy fallback is disabled unless a developer explicitly sets `STUDIO_ALLOW_LEGACY_MCP=1`; it is not a production path. |
| ComfyUI | IMPLEMENTED / LIVE, NOT CERTIFIED | Loopback HTTP health, queue, prompt submit, history, node/model inventory, bounded completion polling, output download and artifact provenance; no WebSocket streaming, cancellation, workflow schema validation or semantic visual QA yet. Verified against a **live** v0.34.0 instance: `flux2_klein` txt2img and `hunyuan3d` image→mesh both produced real assets. |
| Blender | IMPLEMENTED / NOT CERTIFIED | Version and approval-gated background script process; unrestricted Blender Python is not sandboxed; semantic operations/read-back missing |
| Godot | IMPLEMENTED / NOT CERTIFIED | Version and approval-gated headless editor check; deterministic + live capture service; package and gameplay validation missing |
| Perception transport | IMPLEMENTED / MODEL DELIVERY UNPROVEN | Bundle format v2, authoritative/transport artifact split, adaptive encoding with named refusal, image content blocks on both MCP servers, probe with single-use/expiring challenges, derived evidence grade, gate refusal. Structural delivery is tested; **no vision-capable agent is connected in this environment**, so model readback is not demonstrated |
| Capture masks | FIXTURE-VERIFIED / EMBERKEEP PARTIAL | Visible segmentation respects occlusion by construction (occluders stay as depth writers), silhouette and illumination are separate semantics, and the wall fixture asserts the pixel regions. Emberkeep's lantern is fully unoccluded at the default camera, so its occlusion path is proven by the fixture rather than by the game |
| Unreal / Unity | RESEARCH ONLY | No executable adapters in this release |
| DCC-MCP Core / AI Game Dev | RESEARCH / EXTERNAL INTEGRATION CANDIDATES | Not embedded or locally reproduced in this environment |
| Other creative disciplines | DESIGNED / NOT INTEGRATED | Audio, video, CAD, UI, web/app, writing, scientific and publishing pipelines need real adapters and tests |
| Security / license / commercial readiness | PARTIAL DESIGN | Full audit, sandbox, SBOM, migration/restore drills, cross-project lock, penetration tests and rights review remain release blockers |

## Hosted CI baseline before the handoff repair

The base commit `4924961684530eaad536dfc576d177409745dc0d` triggered Actions run `42088269841` on 2026-11-05. All six Ubuntu/Windows and Python 3.11/3.12/3.13 jobs failed during test collection because the CI install omitted the `quality` extra that supplies NumPy and Pillow to critic/perception tests. The logs show `ModuleNotFoundError: numpy` and `ModuleNotFoundError: PIL`. This is an environment/dependency-contract failure before test execution, not a failed assertion in the reported 159-test workstation run. The repair is staged on branch `agent/handoff-production-gap-closure-2026-11-05`; the branch's pull-request matrix is the verification gate.

## Actual test result

The runtime suite completed **159 passed, 1 skipped in 22.74 s** on the Windows workstation using `PYTHONPATH=src .venv/Scripts/python.exe -m pytest -q`. Coverage includes job DAG persistence, exact approval binding, file/workspace confinement, SHA-256 manifests, backup/integrity checks, database schema-version rejection, crash quarantine/reconciliation, fail-closed MCP transport behavior, official-SDK MCP integration, ComfyUI redirect/response bounds, and a complete ComfyUI queue → completion → output retrieval → artifact verification flow.

The skipped test is `tests/test_paths.py:19` — symlink creation is unavailable without Windows developer mode. It is an environment limitation, not a runtime defect, and it does **not** skip the MCP SDK protocol test: `tests/test_mcp_sdk.py` now passes with the installed `mcp` dependency (an earlier revision of this document incorrectly attributed the skip to MCP).

Passing tests still do not constitute adapter certification, and no packaged build exists yet.

## Hosted CI follow-up — cross-platform path validation

The first handoff PR run (`42111183630`) confirmed that dependency installation, JSON parsing and repository-contract/link verification passed on all Ubuntu jobs. The three Ubuntu test jobs then exposed one independent defect: `perception.bundle._safe_relative` relied on the host OS `pathlib.Path` grammar, so a Windows drive path such as `C:/Windows/system32/x.png` was accepted when a bundle was verified on Linux. Each Ubuntu version reported the same failing regression test (146 passed, 1 failed, 13 environment skips). This is a path-boundary defect, not a dependency issue.

The handoff branch now checks POSIX and Windows path grammars explicitly, normalizes separators before constructing the host path, rejects drive/UNC paths and rejects parent traversal in either dialect. Regression cases cover Windows drive paths, UNC paths and backslash traversal. The follow-up Actions run is the required proof; do not mark the CI gate complete until every matrix job passes.

## Perception subsystem (spec rev 2)

Spec: `docs/superpowers/specs/2026-11-05-perception-transport-design.md`; plan: `docs/superpowers/plans/2026-11-05-perception-transport-plan.md`.

| Property | Evidence | State |
|---|---|---|
| Images survive the tool call | `tests/test_perception_mcp.py` — real `handle()` call returns `image` blocks with no `structuredContent` and no `audience` annotation, under the SDK default | PROVEN (structural) |
| Model can read them | `reports/evidence/productions/emberkeep/02-manufacture/PROBE_REPORT.json` | **NOT ESTABLISHED** — no vision-capable client connected; a harness pass is not a model result |
| Deterministic capture | `CAPTURE_REPORT.json` — three runs, identical frame and mask hashes, grade `authoritative` | PROVEN on this machine only |
| Live capture is supervision only | `LIVE_CAPTURE_REPORT.json` — verified bundle, grade `supervisory`, gate refuses with `EVIDENCE_NOT_AUTHORITATIVE` | PROVEN |
| Masks respect occlusion | `tests/test_perception_godot_fixture.py` — target behind a wall excluded from visibility, present in silhouette | PROVEN by fixture |
| Protocol eras | `tests/test_perception_mcp.py` (legacy `2025-11-25`) and `tests/test_mcp_sdk.py` (official SDK negotiates `2026-07-28`) | PROVEN for the image contract on both paths |
| Ledger completeness | `LEDGER_REPORT.json` — `perception.capture` recorded at the engine boundary, outcome `ok`, `gaps: []` | PROVEN |
| Emberkeep frame passes the critic | `CRITIC_REPORT.json` — PASS, p5 0.01565 vs 0.015 floor, lantern gap 0.46, warm share 0.006, ΔE 2.24 | PROVEN on qualified evidence, thin margin (4%) |
| The critic names a cause, not just a symptom | `CRITIC_REPORT.json` → `luminance_cause` with separate coverage, variation and illumination dimensions; `tests/test_critic_spatial.py` | PROVEN on synthetic ground truth and measured on Emberkeep; scene reliability NOT established |
| Illumination is measured, not inferred from brightness | `light_control_{all,direct,environment,emissive}` in the qualified bundle; contribution 0.54 total, 0.55 ambient, 0.04 direct, 0.03 emissive | PROVEN on this frame; indirect bounce NOT measured |
| The scene-level warm share is established | `warm_share` → `not_measured`, `semantic_scope: not_established` | **NOT ESTABLISHED** — no semantic scene-region mask exists; only `warm_share_frame` (0.006035) is measured |
| Every metric discloses its arithmetic | `disclosure` block on each finding: numerator, denominator, source hashes, threshold, contract revision, measurement or inference | PROVEN by `test_every_metric_discloses_what_it_divided_and_what_it_read` |
| Coverage evidence exists | `mask_world_occupancy` (kind `scene_coverage`) in the bundle, cross-checked against a magenta-background render | PROVEN as a measurement; it is constant for Emberkeep because the flood fills the frame |

Honest limits: repeatability is same-machine only, and within a batch; the mask construction is derived from documented render semantics rather than an official feature; a 1080p capture is not a packaging test; and the game may not grant itself authority, so no capture is `authoritative` until the Studio's three-run qualification says so.

One cross-batch gap was found while re-running the evidence: the frame and five of the six masks reproduce exactly across separate invocations, but `mask_lantern_illumination` does not, because it is a difference of two renders taken later in the frozen frame and any time-advancing shader (volumetric fog) shifts it. It is recorded in `CAPTURE_REPORT.json` rather than smoothed over, and no metric depends on that mask.

### The grade fix, and the diagnosis that was wrong twice

The arrival frame failed `luminance_floor` at p5 0.00163. The first reading was "a dead-black lower third", which is a description of pixels, not a cause.

**Correction, measured.** An earlier version of this document claimed the water plane sat below the terrace slab and never rendered, so the camera looked past the world edge into the sky's ground hemisphere. That is false, and it was checkable. The water plane was already 260 × 260 at y = -1.25 in the failing build, and a magenta-background counterfactual renders zero background pixels anywhere in frame. The camera never sees past the world edge: the flood covers the whole view. The dark lower third was **water that was present, near-black and visually flat**. Whether it was also unlit was not measured at that point, and the first version of this document asserted it anyway; the controlled captures below later showed the passing frame's water gets 54% of its luminance from scene light, so "unlit" is not a safe description of the surface either.

What actually moved the metric was therefore material and light, not geometry: water albedo from near-black (0.02, 0.035, 0.045) to a slate mirror (0.20, 0.28, 0.32), stronger ripple normals, ambient 0.26 → 1.4, moon 0.34 → 0.9, exposure 2.05, and a mist-to-ink sky gradient that is mostly invisible from this camera because the flood fills the frame. The waterline change to y = -0.45 stays because it makes the deck read as a quay rather than a floating slab — an art improvement, not the fix, and it is recorded as such.

Measured result: p5 0.00163 → 0.01565, p50 0.00425 → 0.03509, PASS with the lantern still the warmest thing in frame (gap 0.46, warm share 0.006).

The cost is honest to state: the palette's own ink is 0.0050 linear, a third of the floor, so at most 5% of any frame may sit at ink. A deep-night grade and this threshold cannot coexist. What passes is a haze-lit blue hour, not the original near-black night, and the 4% margin means the next art change must re-run the critic rather than assume the pass survives.

### Milestone: Diagnostic Semantics Qualification

Three different defects produced the same finding: unlit geometry, absent geometry, and exposure that never reached the lower frame. The critic reported the symptom and left the cause to whoever read it — and two different readers (this agent, twice) got it wrong.

`luminance_cause` (`lum-cause-3`) answers three questions separately, because they fail separately, and states the status of each:

| dimension | question | evidence | Emberkeep |
|---|---|---|---|
| coverage | is a rendered surface at this pixel? | `scene_coverage` mask | `present`, `measured` |
| surface variation | does the region vary at viewing scale? | tile spread at 8/16/32 px | `low_variation`, `measured`, readability `not_established` |
| illumination response | how much luminance is scene light? | paired mechanism controls | `adequate_contribution`, contribution 0.54, `measured` |

It composes a kind only from what was measured: `missing_coverage`, `dark_sky`, `dark_low_variation_surface`, `dark_variation_surface`, `underlit_surface`, `no_darkness`, or `undetermined`. Each dimension reports `evidence_status`; the composed diagnosis reports `evidence_status: measured_inputs` and `assertion_type: inference`, so a conclusion never borrows the status of its inputs. On the passing frame it reads `dark_low_variation_surface` — a lit, smooth surface whose variation sits below threshold at every scale. It is always severity `note`: a diagnosis explains a verdict, it never decides one.

**Variation is not detail.** The dimension was renamed because local variance says the image varies, not that a viewer can read it. Smooth water, deliberate gradients and specular blobs are low-variation and can be correct; noise scores higher than craft. Tiles that straddle a lit neighbour are excluded, so a bright object beside a flat surface can no longer look like detail on it, and `scale_invariant` spread is reported as indistinguishable noise/fine texture rather than as structure.

**The illumination experiment now exists.** Every run captures paired controls at identical camera and exposure with one mechanism held back (`all`, `direct`, `environment`, `emissive`); they are qualified for repeatability and verified with the rest of the bundle, and kept out of the six-image per-call transport. Result on the passing frame: total 0.5425, ambient 0.5500, direct 0.0444, emissive 0.0326. The shares are not additive — ambient alone removes slightly more than everything — so they rank light sources rather than partition light. Indirect bounce is not measured and says so. Adequacy remains `not_established`: it is an art-direction judgement.

**The duplicate warm measurement is gone.** `warm_share` and `warm_share_frame` returned the identical 0.006035 because the world mask selects the whole frame. The scene question is now `not_measured` with `semantic_scope: not_established` until a mask with declared semantics exists; `warm_share_frame` carries the contract limit alone and discloses that the limit was authored as a share of the scene.

Every metric carries a disclosure block: numerator, denominator and its semantics, included and excluded regions, SHA-256 of the frame and each mask and control frame, the threshold, the contract revision, and whether the assertion is a `measurement` or an `inference`; a metric that could not run states why.

The reasoning and the rules extracted from this are preserved in `docs/06-quality/CASE_STUDY_DARK_DIAGNOSIS.md`, and the universal form — `No diagnostic may claim a cause more strongly than its evidence permits` — is now a section of `docs/06-quality/QUALITY_SYSTEM.md`.

The input it needed did not exist. `mask_world_visible` is a segmentation of the world's geometry after depth, not a statement about whether anything is there — it selects 97–100% of the Emberkeep frame. A new role, `mask_world_occupancy` (semantics `scene_coverage`), renders the scene against a background colour the palette cannot produce and marks every pixel carrying a surface, independent of how dark that surface is lit. It is verified against an independent magenta-background render rather than trusted.

Superseded captures now live in `captures/superseded/` with a `SUPERSEDED.json` recording why each was replaced, including the failing first capture, which is the ground truth for the correction above.

## Immediate next work

Governing plan: `docs/superpowers/plans/2026-11-05-emberkeep-implementation-plan.md` (approved), against `docs/superpowers/specs/2026-11-05-emberkeep-reference-production-design.md`.

| Phase | State |
|---|---|
| P0 Foundations (tracking, evidence storage, status) | **COMPLETE** — 66 source files tracked; 37 evidence files hash-addressed in `reports/evidence/ARTIFACTS.sha256`; this document corrected |
| P1 Art-direction contract | **COMPLETE** — schema, loader, hash binding, 15 tests |
| P2 Trace ledger + migration to schema 2 | **COMPLETE** — 10-class taxonomy, gaps CLI, 17 tests |
| P3 Critic v1 + end-to-end benchmark | **COMPLETE** — 8 metrics, p95 1.16 s at 1080p vs 3 s budget; no native code needed |
| P4 Godot modularisation | in progress — capture service, render-layer taxonomy, physics-tick waits and mask fixture landed; the 715-line monolith is not yet split |
| P5 Package + staged acceptance | pending |
| P6 ACE-Step 1.5 score | pending |
| P7 Human gates | pending |
| P8 Distribution + evidence bundle | pending |
| P9 ACES capture + retrospective | pending |

Nothing above is complete until its phase proof command has run and its output is committed.

## Release posture

**Developer Preview / Runtime Foundation. Not production certified. Not a multi-million-dollar valuation claim.** No claim is made that every capability listed in the design scope is already implemented. The current code is a durable local execution/control-plane foundation with a tested ComfyUI protocol path; the universal multi-discipline production system, native app operations, visual quality moat and commercial readiness are still substantial implementation programs governed by measurable, version-specific acceptance gates.
