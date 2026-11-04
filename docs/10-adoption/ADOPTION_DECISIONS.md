# Initial Adoption Decisions and Hypotheses

This is the current decision posture, not a completed technical audit. “Evaluate first” is not “adopted.” Every decision must be replaced or confirmed by evidence from pinned revisions and local tests.

| Component | Current posture | Why | Required proof |
|---|---|---|---|
| Freebuff | KEEP as primary agent/user-facing coordinator | Existing user workflow and desired agent context | Reconstruct capabilities, permissions, tool routing, context limits and local access |
| AI Game Dev | BENCHMARK + SELECTIVE ADOPTION | Demonstrates mature engine automation and extension patterns | Source/doc audit, version snapshot, matched workflow benchmarks, auth/cloud boundaries |
| DCC-MCP Core | PRIORITY-1 EVALUATION | Broad cross-DCC gateway, Skills and adapter catalog may avoid extensive custom bridge work | Pinned code, license/dependency/security audit, Windows host install and per-adapter conformance |
| Native Blender `bpy` | ADOPT FOR BLENDER OPERATIONS WHERE STRONGEST | Official app API and direct control | Blender version compatibility, headless/editor execution, output and safety tests |
| ComfyUI HTTP/WebSocket | ADOPT AS PRIMARY COMFYUI CONTROL SURFACE IF VERSION MATCHES | Native queue/workflow/status/artifact API | Versioned API smoke suite, history/output verification, queue/cancel/error behavior |
| Engine-native API | PREFER FOR AUTHORITATIVE ENGINE STATE | Deepest semantic operations and reliable main-thread access | Per-engine adapter tests and editor/runtime validation |
| LangGraph | EVALUATE | Candidate for stateful agent/graph workflows | Crash/replay/human approval/task benchmark; determine whether separate durable engine needed |
| Temporal | EVALUATE FOR DURABLE JOBS | Mature long-running workflow concept | Operational overhead vs actual job durability need; local deployment test |
| llama.cpp / Ollama | EVALUATE LOCAL MODEL RUNTIME | Local inference without mandatory API keys | Model-specific quality, tool calling, memory and performance on target GPU/CPU |
| PyTorch / Diffusers | ADOPT FOR MODEL PIPELINE EXPERIMENTS | Flexible inference and image pipeline control | CUDA/runtime compatibility, VRAM measurements, licenses and repeatability |
| TensorRT | DEFER UNTIL PROFILE JUSTIFIES | Optimization may require conversion and support effort | Measured speed/memory gains and model support |
| OpenUSD | ADOPT WHERE COMPLEX SCENE INTERCHANGE NEEDS IT | Layered scene interoperability for DCC/large scenes | App feature coverage and resolver/asset round-trip test |
| glTF | ADOPT FOR SUITABLE RUNTIME 3D DELIVERY | Standardized runtime-oriented interchange | Export/import, extensions, animation, materials and compression tests |
| MaterialX | ADOPT WHERE MATERIAL GRAPH INTERCHANGE IS SUPPORTED | Cross-tool material standard | Per-renderer feature parity tests |
| OpenTimelineIO | ADOPT FOR EDITORIAL STRUCTURE INTERCHANGE WHERE SUPPORTED | Explicit timeline interchange model | Adapter/media reference and round-trip tests |
| OpenTelemetry-compatible observability | ADOPT PATTERN/TOOLS AS PRACTICAL | Cross-process trace correlation | Verify local privacy, overhead and adapters |

## Immediate shortlist order

1. DCC-MCP Core: broad gateway candidate.
2. AI Game Dev: product benchmark for game-engine experience and feature depth.
3. Native Blender and ComfyUI APIs: first real asset pipeline.
4. One engine adapter based on current installed environment.
5. Workflow engine candidate based on the durability experiment.
6. Local model runtime based on actual model/quality/device benchmarks.

## Rejection conditions

Reject or isolate any component with unsafe permission model, unclear license, unmaintained critical dependency, destructive/unbounded behavior, weak postconditions, severe compatibility gaps, hidden paid dependency, or a lower quality ceiling than a viable alternative.
