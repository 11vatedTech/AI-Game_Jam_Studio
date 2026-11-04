# ComfyUI Adapter — Native HTTP Integration

## Implemented in runtime 0.2.0

- Loopback-only endpoint enforcement by default. Non-loopback ComfyUI endpoints are refused in this release. Ambient HTTP proxy variables are ignored, redirects are not followed, and JSON responses are capped at 64 MiB. Output downloads are capped at 512 MiB.
- Health and queue inspection through `/system_stats` and `/queue`.
- API-format workflow submission through `/prompt`, with a canonical workflow SHA-256 recorded in the job output.
- History inspection through `/history/{prompt_id}`.
- Node inventory through `/object_info` and best-effort model-category inventory through `/models/{checkpoints,loras,vae,controlnet,upscale_models,embeddings}`.
- Bounded polling until ComfyUI explicitly reports completion or a failure/timeout occurs.
- Output metadata traversal, strict output-type checking, bounded `/view` downloads, managed-workspace storage, artifact registration, SHA-256 manifests and workflow/node provenance.
- Uncertain prompt-submission errors are escalated to `NEEDS_RECONCILIATION`; the runner does not blindly replay a potentially submitted generation.

All endpoints are configurable via `[applications].comfyui_url`; default is `http://127.0.0.1:8188`. The adapter currently rejects non-loopback hosts. Keep the local service bound to loopback. A test HTTP server proves the adapter protocol path and artifact registration, not compatibility with every custom node or a real local ComfyUI installation.

## Deliberate quality boundary

A completed workflow plus output download proves only that an output file was produced and its stored bytes can be hashed. The new artifact is recorded with semantic validation `NOT_RUN` and rights `UNKNOWN`. The runtime does not yet prove that the image is attractive, anatomically correct, compositionally sound, style-consistent, commercially licensed, or even semantically appropriate. Those are separate gates.

## Required production completion work

1. Query ComfyUI version/build and expose compatibility diagnostics.
2. Discover registered node definitions; capture custom-node package, commit, dependency and license state. Do not equate node discovery with node qualification.
3. Validate workflow graphs against live node input/output definitions before enqueue. Validate model/node references and typed parameter ranges.
4. Pin checkpoint/VAE/LoRA/ControlNet/IP-Adapter/CLIP/model hashes, custom-node revisions, workflow JSON, seed, sampler, scheduler, dimensions, precision and runtime settings.
5. Add WebSocket event streaming for progress, executing node, previews and completion, with tested polling fallback. Never assume completion on disconnect.
6. Add interrupt/cancel and queue pause/clear behind separate human approval scopes; cancellation semantics must be reconciled with server history.
7. Add output schema checks for images, animation, video, audio, 3D and other custom node outputs; include cardinality, dimensions, color format, alpha and media integrity validators.
8. Build calibrated semantic/visual QA for anatomy, composition, material, artifacts, typography, style consistency and brief adherence; automated critics remain advisory until calibrated against human review.
9. Build golden workflows for several disciplines and run clean-workspace repeatability benchmarks on the actual target workstation.
10. Preserve the full editable ComfyUI workflow, exact model/node revisions, prompt, seed and runtime settings as a job-level evidence bundle.

Primary API references: <https://docs.comfy.org/development/comfyui-server/comms_routes> and <https://docs.comfy.org/development/comfyui-server/websocket_api>.
