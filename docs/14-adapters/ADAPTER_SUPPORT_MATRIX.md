# Adapter Support Matrix — v0.2.0 Snapshot

`IMPLEMENTED` means an executable operation exists. It does not imply end-to-end workflow or production certification.

| Application/system | Executable operations | Status | Next evidence required |
|---|---|---|---|
| ComfyUI | `/system_stats`, `/queue`, `/prompt`, `/history/{id}`, `/object_info`, model-category inventory, completion polling, bounded `/view` retrieval and artifact manifests | IMPLEMENTED / NOT CERTIFIED | Real workstation run, WebSocket progress, cancel, workflow schema validation, pinned model/node catalog, semantic image QA and repeatable golden workflow |
| Blender | `--version`; approved `--background --python` script execution | IMPLEMENTED / NOT CERTIFIED | Version support, script sandbox, semantic operation library, save/reopen, render/export and native scene read-back |
| Godot | `--version`; approved headless editor import/parse validation | IMPLEMENTED / NOT CERTIFIED | Project/scene semantic inspection, runtime launch, automated interaction, package/export, logs and screenshot/performance capture |
| Unreal Engine | None | RESEARCH / NOT CONNECTED | Confirm installed version; compare official Python/Editor APIs, remote control, MCP projects and AI Game Dev; build native plugin/bridge test |
| Unity | None | RESEARCH / NOT CONNECTED | Verify installed editor; compare editor scripting, package/editor APIs, RQL/AI Game Dev and competing bridges |
| DCC-MCP Core | Not embedded; connect as separate MCP server in Freebuff | PRIORITY EVALUATION | Pin release, audit, install on Windows, exercise each adapter independently and map capability support |
| AI Game Dev | Not embedded; use as external benchmark/product integration candidate | BENCHMARK | Match representative workflows by engine, measure quality/depth/reliability and optional cloud boundaries |
| Local LLM endpoint | Optional OpenAI-compatible chat client | EXPERIMENTAL | Actual endpoint/model test, structured tool call, context, reliability, latency and quality benchmarks |
| ffmpeg | Not integrated | PROPOSED | Probe executable, license/build configuration, codec support, safe typed workflows, media QA |
| Audio DAW/tools | Not integrated | PROPOSED | Evaluate native scripting/API, MIDI/audio export, loudness/peak analysis, stems and project round-trip |
| CAD applications | Not integrated | PROPOSED | Select parametric CAD and interchange workflows; verify geometry and dimension constraints |
| Web/app design tools | Not integrated | PROPOSED | Browser/CDP and design-system workflows; accessibility and responsive screenshot tests |

## Certification record format

Each adapter release must have: upstream URL and immutable revision, source/license audit, install procedure, exact host/application version, supported operation list, required scopes, data types/units/color spaces/coordinate frames, timeout/cancellation, postconditions, error mapping, fixtures, automated tests, real app evidence, security review, known limitations and owner. Mark certification only for the exact tested matrix.

## MCP host bridge

The production path uses the official Python SDK v2 through the optional `[mcp]` extra. It is designed for MCP revision `2026-07-28` and legacy clients; in-memory/SDK integration testing is configured in CI. The tiny built-in JSON-RPC harness remains a no-extra fallback only and is not the certification target. Verify a real Freebuff host connection on the user's Windows installation before marking this adapter `CERTIFIED`.
