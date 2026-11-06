# Adapter Support Matrix — v0.2.0 Snapshot

`IMPLEMENTED` means an executable operation exists. It does not imply end-to-end workflow or production certification.

| Application/system | Executable operations | Status | Next evidence required |
|---|---|---|---|
| ComfyUI | `/system_stats`, `/queue`, `/prompt`, `/history/{id}`, `/object_info`, model-category inventory, completion polling, bounded `/view` retrieval, artifact manifests, **workflow validation** (`comfyui.validate_workflow`: structure, links, placeholders, live inventory check) and **interrupt/clear** (`comfyui.interrupt`) | IMPLEMENTED / NOT CERTIFIED | Live validation of the golden flux2 workflow (11 nodes, placeholders flagged), live interrupt on idle queue. Still open: WebSocket progress, pinned model/node catalog, semantic image QA, deterministic replay proof |
| Blender | `--version`; approved `--background --python` script execution; **native scene read-back** (`blender.inspect_scene` on Blender 5.2.0 LTS: objects, transforms, mesh stats, materials, images — proven live on `lantern.blend`) | IMPLEMENTED / NOT CERTIFIED | Version support, script sandbox, broader semantic operation library, save/reopen round-trip, render/export |
| Godot | `--version`; headless editor import/parse validation; **native scene read-back** (`godot.inspect_scene` on 4.7.2.stable: >100-node tree with transforms/meshes/lights — proven live on Emberkeep `main.tscn`); packaged export + clean-location launch smoke (3/3 exit 0, state=WON) | IMPLEMENTED / NOT CERTIFIED | Runtime interaction automation, headed screenshots of the packaged build, headed GPU profiling, human craft/rights review |
| Unreal Engine | `unreal.health` reads authoritative `Engine/Build/Build.version` + editor binary presence | IMPLEMENTED (health) / NOT CERTIFIED | Workstation has UE 5.8.0 (changelist 55116800). Editor workflows remain RESEARCH until one project-level operation is proven |
| Unity | `unity.health` reports CLI version + installed-editor inventory | IMPLEMENTED (health) / NOT CERTIFIED | Unity CLI 1.0.0-beta.12 present but **no editor is installed** (all `unity editors` rows uninstalled). Editor workflows stay RESEARCH; installing an editor is a multi-GB download needing operator approval |
| DCC-MCP Core | Not embedded; connect as separate MCP server in Freebuff | PRIORITY EVALUATION | Pin release, audit, install on Windows, exercise each adapter independently and map capability support |
| AI Game Dev | Not embedded; use as external benchmark/product integration candidate | BENCHMARK | Match representative workflows by engine, measure quality/depth/reliability and optional cloud boundaries |
| Local LLM endpoint | Optional OpenAI-compatible chat client | EXPERIMENTAL | Actual endpoint/model test, structured tool call, context, reliability, latency and quality benchmarks |
| ffmpeg/ffprobe | `media.probe` (format/streams/codecs JSON) and `media.transcode` (allowlisted codecs, no-overwrite, ffprobe re-verification) — proven live on ffmpeg 8.1.2 (tone → libopus ogg) | IMPLEMENTED / NOT CERTIFIED | License/build-config record per machine, loudness/peak analysis, stems, project round-trip, semantic media QA |
| Audio DAW/tools | Not integrated | PROPOSED | Evaluate native scripting/API, MIDI/audio export, loudness/peak analysis, stems and project round-trip |
| CAD applications | Not integrated | PROPOSED | Select parametric CAD and interchange workflows; verify geometry and dimension constraints |
| Web/app design tools | Not integrated | PROPOSED | Browser/CDP and design-system workflows; accessibility and responsive screenshot tests |

## Certification record format

Each adapter release must have: upstream URL and immutable revision, source/license audit, install procedure, exact host/application version, supported operation list, required scopes, data types/units/color spaces/coordinate frames, timeout/cancellation, postconditions, error mapping, fixtures, automated tests, real app evidence, security review, known limitations and owner. Mark certification only for the exact tested matrix.

## MCP host bridge

The production path uses the official Python SDK v2 through the optional `[mcp]` extra. It is designed for MCP revision `2026-07-28` and legacy clients; in-memory/SDK integration testing is configured in CI. The tiny built-in JSON-RPC harness remains a no-extra fallback only and is not the certification target. Verify a real Freebuff host connection on the user's Windows installation before marking this adapter `CERTIFIED`.
