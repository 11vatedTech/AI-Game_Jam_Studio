> **Current execution handoff (2026-11-05):** Read [FREEBUFF_EXECUTION_HANDOFF_2026-11-05.md](FREEBUFF_EXECUTION_HANDOFF_2026-11-05.md) before taking the next task. It records the live repository baseline, the hosted CI failure and the ordered acceptance gates. This dated handoff supersedes older chat assumptions, not the repository's security or certification rules.

# Freebuff — Operational Handoff and Mission

**You are the primary implementation agent for 11vatedTech AI Game Jam Studio.** This is a real repository with a specification and an executable v0.2.0 runtime foundation. Your assignment is to turn it into an exceptionally capable, commercial-grade creative-production system by reusing the best proven professional software and closing the remaining gaps with verified implementations.

Do not merely summarize this repository or create a plan and stop. Inspect, install within approved boundaries, test, implement, capture evidence, repair failures, and update the project status.

## 0. What is already real

The Python runtime is dependency-free at its core and includes:
- SQLite persistence for jobs, task states, event history, artifact manifests and approvals.
- A dependency-validated DAG executor with task checkpoints, output references, bounded external process calls, per-job process locks and crash/uncertain-side-effect quarantine with a human-only reconciliation command.
- A local MCP stdio server exposing status, capability discovery, resource profile, jobs, artifacts, quality reports, approval requests and controlled workspace creation.
- Default-deny permission policy, exact scope/side-effect/target approvals, explicit blocked scopes and a human-only approval CLI.
- Managed workspace path confinement, symlink escape checks, no-overwrite file creation and SHA-256 artifact integrity checks.
- Host inventory including CPU, OS, Python, disk, optional RAM metrics and NVIDIA GPU/VRAM via `nvidia-smi`.
- A native ComfyUI HTTP adapter for health, queue, prompt submission/history, live node/model inventory, bounded completion polling, output retrieval and artifact provenance. It has also been exercised against a live local ComfyUI v0.34.0 instance for txt2img and Hunyuan3D image-to-mesh, with real output assets recorded in PROJECT_STATUS.md; semantic asset quality and adapter certification remain open.
- Read-only version checks and approval-gated script/project execution for Blender and Godot.
- An optional OpenAI-compatible model endpoint client; no external model API is required by the runtime.
- Unit/integration tests. **Run them. Do not assume this handoff's previous test result matches your machine.**

This is a valuable foundation, not the finished universal studio. The implemented adapter operations are not automatically production-certified. Unity, Unreal, broad DCC-MCP Core coverage, AI Game Dev parity, CAD, audio, video, design, publishing and many specialized pipelines still require research, integration and conformance testing.

## 1. Install and establish an evidence baseline (do this first)

On Windows 11:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\windows\bootstrap.ps1
$env:STUDIO_HOME = "$env:LOCALAPPDATA\11vatedTech\AI-Game-Jam-Studio"
studio status
studio doctor
studio capabilities
pytest -q
```

Record actual output, time, versions, exit codes and issues in `reports/environment/`. Verify Python, Git, compiler toolchains, GPU driver, CUDA, ComfyUI 8188, Blender, Unreal, Unity, Godot, ffmpeg, audio/video applications, local model servers, storage and free RAM/VRAM. Never infer installation from prior conversation memory.

Configure Freebuff to attach the MCP server using `scripts/windows/mcp-config.example.json`, replacing the placeholders with actual absolute paths. The production bootstrap installs the official MCP Python SDK v2 (`mcp>=2,<3`), whose current protocol support includes the `2026-07-28` revision and legacy client interoperability. Restart/reload Freebuff, then verify `server/discover` on modern clients (or `initialize` on legacy clients), tool listing and `studio_status`. The SDK integration suite is in `tests/test_mcp_sdk.py` and is reported passing on the Windows workstation; the live Freebuff host handshake and safe tool invocation still require reproduction on the installed client. The server communicates over stdio; **stdout is protocol-only**. Send diagnostics to stderr/files.

## 2. Operating principles

### Reuse proven professional excellence
For each capability, research competing implementations before coding. Inspect primary documentation, source, tags/releases, licenses, dependency tree, security issues, test suites, examples and maintenance activity. Pin exact commits/versions. Reproduce on this Windows workstation. Compare output, reliability, latency, memory, compatibility, cost and licensing. Decide `ADOPT`, `EXTEND`, `WRAP`, `REPLACE`, `BUILD`, `DEFER` or `REJECT` and record an ADR. Do not infer quality from stars, tool counts or marketing.

Priority research starting points are the AI Game Dev project and DCC-MCP Core evaluation in `docs/02-research/`, native Blender Python API, ComfyUI server API, official Unreal/Unity/Godot editor automation, professional DCC and media tools, and the standards catalog. Treat DCC-MCP Core's published adapter breadth as a discovery map—not evidence that every adapter is mature. Run each adapter separately.

### Commercial-quality execution
The pipeline is always:
`INTENT → REQUIREMENTS → REFERENCE/RESEARCH → ART DIRECTION / TECHNICAL DESIGN → PRODUCTION PLAN → MANUFACTURE → NATIVE INTEGRATION → CONTEXT REVIEW → AUTOMATED QA → EXPERT REVIEW → TARGETED REPAIR → REGRESSION → DELIVERY → EVIDENCE`.

Do not skip the art bible, style guide, design tokens, reference study, topology/UV/rig/material checks, animation contact review, in-engine composition, audio mix check, UI usability/accessibility or packaging validation when those are relevant. A generated image is not a finished 3D character. A Blender file is not proof of a correct engine asset. An imported project is not proof of a playable build.

## 3. First implementation milestone: prove a real asset-to-game vertical slice

Do not expand all disciplines before one workflow works end to end. Execute this as the first production benchmark:

1. **Choose a small but demanding target** with a clearly art-directed visual identity, one playable character or hero object, one environment, one interaction, one sound identity, UI, and a packaged build. Use an original brief; don't imitate protected characters or a recognizable commercial game's expression.
2. **Research and inspect** the strongest compatible tools and current local environment. Confirm versions and license rights for every model, node, texture, font, sound and code dependency.
3. **Create the creative direction package**: mood/reference board, visual thesis, silhouette/form language, palette, value hierarchy, materials, camera/framing, lighting, motion language, UI typography/layout, audio direction and explicit forbidden deviations. Get human approval for the art direction before expensive production.
4. **Manufacture one hero asset** using the strongest proven local image/3D pipeline. Retain editable source (ComfyUI workflow and metadata; Blender `.blend`; textures; export settings). Inspect silhouette, dimensions, topology, normals, UVs, texel density, materials, rig/weights if applicable, animation and scale. No placeholder primitives as final deliverables.
5. **Integrate into the installed engine** using native APIs. Verify import, skeleton/material binding, animation, collision, LOD/mipmaps, scene framing, lighting and runtime behavior. Capture editor and runtime evidence.
6. **Build and test** a runnable package; automate launch, interaction tests, crash/log checks and performance capture. Record target platform and machine metrics.
7. **Evaluate visually** at actual gameplay/camera distance and target resolution, plus detail views. Identify concrete defects, fix their upstream cause, and rerun regression. Have a human reviewer score craft until model-based reviewers have been calibrated.
8. **Create evidence package** with all source/exports, artifact SHA-256, exact tool/model versions, prompts/workflows, licenses, logs, screenshots/video, test reports, resource usage, defects/repairs and acceptance verdict.

Only after one end-to-end slice is reproducibly accepted should this pattern be generalized to a reusable character pipeline, environment pipeline, VFX pipeline, UI pipeline, audio pipeline and more genres.

## 4. Scope expansion: required capability families

Build each domain to the maturity of the strongest suitable professional tools. Capability inventory is not complete until every row has candidate(s), owner, source/license, integration boundary, exact support matrix, conformance tests and evidence:

- Game engines: Unreal, Unity, Godot; scene/level, gameplay, animation, rendering, UI, audio, build, profiling, editor automation and packaging.
- 3D/DCC: Blender, specialist modelers, sculpting, retopology, UV, baking, rigging, skinning, animation, geometry nodes, procedural modeling, scene assembly, rendering and interchange.
- CAD/spatial/industrial design: parametric CAD, mesh/CAD interchange, constraints, assemblies, technical drawings, dimensioning, simulation and manufacturing/export standards.
- 2D/illustration: concept art, painting, pixel art, vector, spritesheets, tilesets, typography, layout, print and UI assets.
- Materials/lookdev: PBR, procedural materials, texture authoring, channel packing, baking, color management, shader graphs and renderer interchange.
- Animation/motion: keyframe, retargeting, mocap cleanup, facial animation, lip sync, procedural motion, camera rigs and contact/weight evaluation.
- VFX/simulation: particles, fluids, cloth, hair, destruction, compositing, volumetrics, simulations, render passes and caches.
- Audio/music/voice: sound design, recording, editing, synthesis, score, ambience, foley, dialogue, voice generation where rights allow, mixing, mastering, loudness and in-game implementation.
- Video/cinema: storyboards, shot lists, camera, editing, compositing, grading, titles, motion graphics, captions, delivery encodes and timeline interchange.
- UI/UX/web/apps: research, IA, wireframes, design systems, components, responsive layouts, accessibility, browser tests, design-to-code, prototypes and production apps.
- Software engineering: requirements, architecture, code, debugging, refactoring, code review, test generation, static analysis, builds, dependency/security scanning, CI and releases.
- Writing/narrative/brand: research, story architecture, scripts, branching dialogue, world bibles, copy, documentation, voice consistency and legal/provenance review.
- Research/data/science: reproducible experiments, analysis, visualization, notebooks, simulation, numerical methods and traceable data lineage.
- Publishing/operations: versioning, packaging, signing, store submission preparation, web deployment, compatibility testing, release notes and rollback.

Also map emergent domains and specialist tools. Do not cap scope at game development or at any one application gateway.

## 5. Required roadmap and exit gates

### P0 — workstation baseline and runtime hardening
- Execute bootstrap/tests; configure MCP; inspect Windows hardware and app installations.
- Validate crash quarantine/reconciliation on a real interrupted process and complete database restore drills.
- Close Windows-specific path/launch, cancellation, cross-project/application/artifact locking, output lineage and security gaps.
- Add structured logs and trace IDs; sanitize secrets; add backup/restore and DB migrations.
- Ensure policy decisions are persisted with exact scope/target/reviewer/evidence and cannot be agent-self-approved.
- Exit: clean install, MCP smoke, unit tests, security tests, database restart/recovery, and no unbounded command path.

### P1 — integration benchmark and cross-app gateway
- Inspect/pin AI Game Dev and DCC-MCP Core; test official/native integrations and alternatives.
- Integrate one application operation at a time. Each adapter includes typed schemas, side effects, health, version support, timeout/cancel, postconditions and test fixtures.
- Exit: per-adapter smoke suite, one real read/write workflow in a duplicate project, exact version support matrix, provenance and security review.

### P2 — image/asset manufacturing
- Connect ComfyUI: workflow validation, model/node inventory, queue events, progress, cancel, history, output download, file hashing, metadata, failure diagnosis, rerun and visual review.
- Connect Blender: native semantic operations, scene read-back, asset generation from approved source scripts, save/reopen, renders, exports and import validation.
- Exit: at least one genuine editable, art-directed asset set; repeatable from pinned workflow; no placeholder art; passed file/native/runtime/visual tests; human approval.

### P3 — first game-engine vertical slice
- Select engine using actual installed version/toolchain, not assumptions.
- Integrate native project/scene/script/resource APIs, build/test, runtime capture, logs, profiling and packaging.
- Exit: clean import, playable packaged project, no release-blocking issues, deterministic acceptance run and full evidence bundle.

### P4 — reusable professional pipelines
- Character, environment, props, materials, UI, audio, VFX, animation, cinematic, level design and gameplay pipelines.
- Each pipeline is a versioned workflow definition plus skills, application adapters, acceptance tests, recovery behavior and examples.
- Exit: repeated successful execution across at least three materially different briefs within the declared support matrix.

### P5 — cross-discipline expansion
- Add video, sound/music, CAD, product design, web/app, writing, research/science and publishing systems using best existing professional solutions.
- Exit: independent domain certification; no false claim of universal capability.

### P6 — autonomy and optimization
- Durable approvals, safe replanning, defect root-cause analysis, automated repair, model routing, memory, resource-aware queues, cost/latency quality tradeoffs, audit and benchmarks.
- Exit: reproducible benchmark improvement over baseline without regressions or unsafe permission expansion.

## 6. Mandatory release gates

A feature is not done because a tool was called. It must produce the declared artifact, application read-back, objective tests, context capture, quality review, provenance and reproducibility evidence. `PASS_PENDING_SUBJECTIVE_REVIEW` is not `CERTIFIED`. Never report 100% success if any mandatory test is missing, skipped, blocked or failed.

## 7. Handoff reporting format

After each meaningful work unit report: exact changes, actual commands, test results, outputs/evidence locations, newly certified capability versions, unresolved defects, blockers, resource measurements, license/security decisions, and the single largest remaining gap. Update `PROJECT_STATUS.md`, capability records, decision logs and roadmap checkboxes. Do not duplicate this entire handoff in chat.
