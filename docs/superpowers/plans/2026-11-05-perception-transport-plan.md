# Perception Transport and Verification — implementation plan

**Spec:** `2026-11-05-perception-transport-design.md` (rev 2, `12959d6`)
**Date:** 2026-11-05
**Status:** executing

## Ordering rule

Phase A is a gate. The adapter is not built until an image has been returned through
the real `tools/call` path and the response shape asserted. A capture system whose
output no client can consume is the failure this subsystem exists to prevent.

## Phase A — transport proof

| Step | Deliverable | Verification |
|---|---|---|
| A1 | `src/elevenvt_studio/perception/transport.py` — `TransportProfile`, adaptive encode, refusal | unit: size ladder, envelope exhaustion, named refusal |
| A2 | `perception/bundle.py` — load/verify/compute_grade, path confinement | unit: negative fixtures |
| A3 | `PERCEPTION_TOOLS` returning `CallToolResult` with text + `ImageContent`, no `structuredContent`, no `annotations` | integration: real `handle()` call and real SDK `convert_result()` |
| A4 | Legacy `server.py` image branch (dev-only path) | integration: same assertions |

Wired into both servers so the dev and production paths cannot diverge.

## Phase B — capture and provenance

| Step | Deliverable | Verification |
|---|---|---|
| B1 | `schemas/capture-bundle.schema.json` (v2.0, strict) | schema round-trip |
| B2 | `adapters/godot_capture.py` — driver A subprocess, bundle load, ledger context | fake-engine test + real run |
| B3 | `Games/emberkeep/game/scripts/capture/service.gd` — plan-driven, physics-frame waits, seeded RNG, bundle written last | real 1080p capture |
| B4 | Three-run repeatability qualification | report exact-hash or measured delta |

## Phase C — masks

| Step | Deliverable | Verification |
|---|---|---|
| C1 | Render-layer assignment at capture time | fixture |
| C2 | Two-pass-in-one-viewport visible mask (occluders opaque black, target white, depth decides) | fixture with wall between camera and target |
| C3 | Silhouette (cull_mask) and illumination (light toggle diff) | fixture asserts silhouette ⊃ visible and difference only in occluded region |
| C4 | Gate rule: mask metrics usable only after fixture pass | test asserts `note` when unqualified |

`mask_world_visible` is the degenerate case: the whole world is the target set, so
ordinary rasterisation supplies mutual occlusion within one pass.

## Phase D — live

| Step | Deliverable | Verification |
|---|---|---|
| D1 | `LiveSession` client with line cap, timeouts, token | unit with fake socket |
| D2 | `service.gd` live mode: loopback, port 0, `session.json`, op whitelist, auth-before-session | integration |
| D3 | Live bundle graded `supervisory` | test: gate rejects, critic still evaluates |

## Probe

`perception/probe.py` — issue/verify, 6-char code rendered into an image and never in
text, single-use, 180 s expiry, bound to agent instance + client identity. Identity
provenance stored as separate fields; self-reported model marked as self-reported.

## Exit criteria (from spec §16)

Evidence under `reports/evidence/productions/emberkeep/02-manufacture/`:

1. Real 1080p deterministic capture, verified artifacts, current contract hash.
2. Real `tools/call` response with image blocks, both structured-content settings.
3. Live capture graded `supervisory`, diagnostics work, gate refuses.
4. Probe result with identity tuple, including one deliberate failure.
5. Three-run repeatability with honest outcome.
6. Mask fixture result, or explicit `note`.
7. Negative-fixture suite green; no case yields authoritative evidence.
8. `studio ledger gaps` clean.
9. Protocol compatibility reported, unsupported path named.

## Known blockers to report honestly

- No vision-capable client is registered in this environment; Phase A's "a real agent
  identifies the marker" can only be satisfied structurally until one is connected.
  The probe tool and harness exist so it can be settled in one step when it is.
- Godot capture requires a real window (no headless). Runs happen on this desktop.
