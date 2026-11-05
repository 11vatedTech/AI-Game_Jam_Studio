# Project Status — Executable Foundation 0.2.0, now proven on the workstation

**Snapshot:** 2026-11-05. **Target:** `11vatedTech/AI-Game_Jam_Studio`. **Truth status:** Installed and running on the user's Windows workstation. The runtime suite passes there, ComfyUI is live and has manufactured assets, and Godot 4.7.2 has produced a playable slice. Adapters remain uncertified in the formal sense; see the workstation evidence below.

## Verified on this workstation (2026-11-05)

| Fact | Value | How it was measured |
|---|---|---|
| Runtime tests | 37 passed, 1 skipped, 19.9 s | `PYTHONPATH=src .venv/Scripts/python.exe -m pytest -q` |
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
| Godot | IMPLEMENTED / NOT CERTIFIED | Version and approval-gated headless editor check; runtime automation, package and gameplay validation missing |
| Unreal / Unity | RESEARCH ONLY | No executable adapters in this release |
| DCC-MCP Core / AI Game Dev | RESEARCH / EXTERNAL INTEGRATION CANDIDATES | Not embedded or locally reproduced in this environment |
| Other creative disciplines | DESIGNED / NOT INTEGRATED | Audio, video, CAD, UI, web/app, writing, scientific and publishing pipelines need real adapters and tests |
| Security / license / commercial readiness | PARTIAL DESIGN | Full audit, sandbox, SBOM, migration/restore drills, cross-project lock, penetration tests and rights review remain release blockers |

## Actual test result

The runtime suite completed **37 passed, 1 skipped in 19.88 s** on the Windows workstation using `PYTHONPATH=src .venv/Scripts/python.exe -m pytest -q`. Coverage includes job DAG persistence, exact approval binding, file/workspace confinement, SHA-256 manifests, backup/integrity checks, database schema-version rejection, crash quarantine/reconciliation, fail-closed MCP transport behavior, official-SDK MCP integration, ComfyUI redirect/response bounds, and a complete ComfyUI queue → completion → output retrieval → artifact verification flow.

The skipped test is `tests/test_paths.py:19` — symlink creation is unavailable without Windows developer mode. It is an environment limitation, not a runtime defect, and it does **not** skip the MCP SDK protocol test: `tests/test_mcp_sdk.py` now passes with the installed `mcp` dependency (an earlier revision of this document incorrectly attributed the skip to MCP).

Passing tests still do not constitute adapter certification, and no packaged build exists yet.

## Immediate next work

Governing plan: `docs/superpowers/plans/2026-11-05-emberkeep-implementation-plan.md` (approved), against `docs/superpowers/specs/2026-11-05-emberkeep-reference-production-design.md`.

| Phase | State |
|---|---|
| P0 Foundations (tracking, evidence storage, status) | **COMPLETE** — 66 source files tracked; 37 evidence files hash-addressed in `reports/evidence/ARTIFACTS.sha256`; this document corrected |
| P1 Art-direction contract | in progress |
| P2 Trace ledger + migration to schema 2 | pending |
| P3 Critic v1 + end-to-end benchmark | pending |
| P4 Godot modularisation | pending |
| P5 Package + staged acceptance | pending |
| P6 ACE-Step 1.5 score | pending |
| P7 Human gates | pending |
| P8 Distribution + evidence bundle | pending |
| P9 ACES capture + retrospective | pending |

Nothing above is complete until its phase proof command has run and its output is committed.

## Release posture

**Developer Preview / Runtime Foundation. Not production certified. Not a multi-million-dollar valuation claim.** No claim is made that every capability listed in the design scope is already implemented. The current code is a durable local execution/control-plane foundation with a tested ComfyUI protocol path; the universal multi-discipline production system, native app operations, visual quality moat and commercial readiness are still substantial implementation programs governed by measurable, version-specific acceptance gates.
