# Perception Transport and Verification — design

**Status:** awaiting user review
**Date:** 2026-11-05
**Scope:** one subsystem of the Studio Production Runtime
**Predecessors:** `2026-11-05-emberkeep-reference-production-design.md`, `2026-11-05-emberkeep-implementation-plan.md`

## 1. Why this exists

An agent that issues commands without receiving the rendered result cannot distinguish a working production from a broken one. It reports success from exit codes. The Studio's whole claim — that it manufactures professional work rather than generating plausible activity — depends on closing that loop with evidence the agent can actually inspect.

Two facts make this urgent and concrete rather than architectural:

1. Every `tools/call` response in `mcp/server.py` currently returns `{"type": "text"}` plus `structuredContent`. There is no image path at all. Any screenshot capability added on top of that transport would hand the agent a file path and call it perception.
2. The four existing Emberkeep captures are 1280×720 while `art_direction.json` declares 1920×1080. The critic already reports `frame_set_meets_declared_resolution: false`. Evidence that is out of declaration cannot support a gate.

## 2. Decisions taken, with reasons

| Decision | Reason |
|---|---|
| Capture bundles, not loose PNGs | A frame without provenance, masks and verification status is a picture, not evidence. |
| Two evidence classes: `deterministic` and `live` | Only reproducible captures may feed a gate. Live observation is for supervision, and pretending otherwise would launder non-reproducible evidence into certification. |
| Both drivers now (plan-driven and live socket) | Requested. They share one bundle format and one game-side capture service so they cannot drift apart. |
| Images travel as MCP `image` blocks; no competing `structuredContent` | The OpenAI Agents SDK documents that a non-empty `structuredContent` takes precedence over content blocks, which would shadow the image entirely. Avoided structurally, not by convention. |
| Transport copies are downscaled to a 2560 px long edge | Anthropic rejects oversized `tool_result` images in computer-use paths rather than resizing them; 1080p is ~1,560 visual tokens at standard tier. The authoritative file stays full resolution and hash-addressed. |
| Masks via `Camera3D.cull_mask` and render layers | Emberkeep is 3D (Forward+). `Viewport.debug_draw` is unavailable on the Compatibility renderer and is not a stable contract. |
| Verification is two mechanisms, not one | A cooperative probe proves the path; contradiction detection catches blindness in agents that never take it. |
| No headless capture | Godot's `--headless` "disables all rendering". Every capture runs against a real (offscreen-positioned) window. |

## 3. Scope

**In scope:** capture contract and bundle format, Godot capture service (both drivers), Studio capture adapter, MCP image transport, perception verification, provenance, failure taxonomy mapping, tests, exit criteria, and the resulting amendments to the Emberkeep plan.

**Out of scope, each a separate spec:** live production dashboard and its event stream, capability profiling and routing, per-discipline critics, automated repair, the qualification benchmark suite beyond the single probe.

## 4. Evidence classes

| Class | `evidence_grade` | Produced by | Reproducible | May feed a gate | Used for |
|---|---|---|---|---|---|
| `deterministic` | `authoritative` | `--capture-plan` run with `--fixed-fps`, physics-tick waits | Yes, by construction | Yes | Critic findings, Gate 1/2 evidence, acceptance |
| `live` | `supervisory` | Socket request to a running interactive session | No | **No** | Supervision, iteration, the dashboard |

`mode` and `evidence_grade` are redundant by design: the schema requires both, so a bundle cannot claim authority while declaring a live origin without failing validation.

Every consumer that can influence a verdict must reject `mode: "live"` bundles. This is enforced in code, not documented as a preference. `perception_capture` returns live bundles with `evidence_grade: "supervisory"` and the critic refuses them with a named error.

## 5. Capture bundle contract

Written to `<out>/bundle.json` beside the images. Schema at `schemas/capture-bundle.schema.json`, strict (`additionalProperties: false`) like the art-direction schema.

```json
{
  "schema_version": "1.0",
  "capture_id": "uuid4",
  "mode": "deterministic",
  "evidence_grade": "authoritative",
  "application": {
    "name": "emberkeep",
    "adapter_version": "1.0.0",
    "engine_version": "4.7.2.stable",
    "project_path": "Games/emberkeep/game",
    "rendering_method": "forward_plus",
    "resolution": [1920, 1080],
    "msaa_3d": 2,
    "screen_space_aa": 1
  },
  "request": {
    "roles": ["frame", "mask_world", "mask_lantern"],
    "frame_index": 180,
    "camera": {"side": "west", "position": [0, 2, 6]},
    "state": {"lantern_lit": true, "beacon_lit": false},
    "seed": 20261105
  },
  "images": [
    {"role": "frame", "path": "shot_00_start.png", "sha256": "…", "width": 1920,
     "height": 1080, "mime": "image/png", "bytes": 2142331}
  ],
  "provenance": {
    "contract_sha256": "…", "plan_sha256": "…", "git_commit": "…",
    "settings": {"fixed_fps": 60, "physics_ticks_per_second": 60, "warmup_frames": 30},
    "host": "win32", "started_at": "…", "finished_at": "…"
  },
  "verification": {"status": "verified", "checks": [{"name": "…", "ok": true, "detail": "…"}]}
}
```

`verification.status` is one of `verified`, `unverified`, `failed`. A bundle is never written with `verified` unless every declared check passed.

**Checks, always run:** file exists; sha256 matches; decodes as the declared mime; dimensions match `application.resolution`; mask dimensions equal frame dimensions; `request.roles` ⊆ image roles; and the frame is not effectively black — defined as p99 linear luminance ≤ 0.002, the range the current broken captures occupy — unless the request declares `expect_black`.

Image filenames are derived from role, never from client input: `frame.png`, `mask_world.png`, `mask_lantern.png`, `mask_player.png`, `diff.png`.

## 6. Game-side capture service (Godot)

New, `Games/emberkeep/game/scripts/capture/service.gd`, loaded only when a capture flag is present, so an ordinary play session pays nothing and gains no network surface.

### 6.1 Render configuration

`project.godot` is changed so captures meet the declaration: the capture run passes `--resolution 1920x1080`, and the bundle records what was actually produced. Under `canvas_items` stretch the render size follows the window, not `viewport_width`, which is why the current 1280×720 output is wrong for a 1080p declaration. Verification compares pixels, so a mistake here fails loudly instead of silently degrading the evidence.

### 6.2 Render layer taxonomy

Masks need semantic separation that does not exist today; every node currently sits on layer 1.

| Layer | Contents |
|---|---|
| 1 | World geometry (terrain, architecture, walls) |
| 2 | Props and interactables |
| 3 | Lantern and its light-emitting children |
| 4 | Player |
| 5 | VFX / particles |

Masks are rendered by a dedicated `SubViewport` per role, each with its own `Camera3D` whose `cull_mask` selects the layers the role needs (`mask_world` = 1|2, `mask_lantern` = 3). Masks are 1-bit content written as PNG for transport. This duplicated camera costs render time and is the accepted price of measuring what the art direction actually constrains; the numbers will show in the capture manifest.

### 6.3 Determinism rules

- All gameplay logic already on `_physics_process`; capture waits are counted in physics frames, never `create_timer(seconds)`. The existing `_settle(0.9)` is replaced for capture purposes because wall-clock settling cannot land on a reproducible frame.
- `--fixed-fps 60`; physics ticks fixed at 60; physics interpolation disabled for capture runs via `Viewport.physics_interpolation_mode = PHYSICS_INTERPOLATION_MODE_OFF`, because an interpolated frame is a blend between two ticks and therefore not a reproducible state.
- `warmup_frames: 30` before the first capture so any converging effect settles; the value is recorded so it can be challenged.
- RNG seeded from `request.seed`.
- Temporal effects that cannot be made frame-stable are disabled for capture and recorded in provenance.

### 6.4 Driver A — plan-driven capture

```
godot --path Games/emberkeep/game --resolution 1920x1080 --position 0,0 \
      --fixed-fps 60 --capture-plan plan.json --capture-out <dir>
```

`plan.json` holds an ordered list of entries: `{frame_index, roles, camera, state, seed}`. The game applies each entry's state at its frame, captures after `RenderingServer.frame_post_draw`, writes the bundle, then quits with 0 only if every entry verified. Exit code is not evidence by itself — the bundle is.

### 6.5 Driver B — live session

```
godot --path Games/emberkeep/game --capture-live --capture-token-file <path> --capture-out <dir>
```

Binds `127.0.0.1` on port 0, writes `session.json` (`{port, pid, started_at, project}`) into `<out>` so the Studio discovers it without guessing ports. JSON-lines protocol:

| Op | Request | Response |
|---|---|---|
| `hello` | `{"op":"hello","token":"…"}` | `{"ok":true,"mode":"live"}`; wrong token closes the socket |
| `capture` | `{"op":"capture","roles":[…]}` | bundle path + verification status |
| `state` | `{"op":"state"}` | current frame index, scene state, fps |
| `quit` | `{"op":"quit","token":"…"}` | clean exit |

Bytes do not travel over the socket: the game writes the bundle to disk and returns its path and hashes, which keeps one code path for image production and avoids base64 over a local socket.

**Security:** loopback bind only; 32-byte token from a file, constant-time comparison, required for `hello` and `quit`; operation whitelist with no arbitrary evaluation, no shell, no client-supplied paths; writes confined to `--capture-out`; one capture in flight, 10 s timeout; session exits after 300 s idle. Every refusal is recorded in the ledger as a denial, not swallowed.

## 7. Studio-side adapter

`src/elevenvt_studio/perception/bundle.py` — `CaptureBundle`, `load(path)`, `verify(bundle) -> Verification`.
`src/elevenvt_studio/perception/transport.py` — `image_blocks(bundle, max_edge=2560)`, `summarize(bundle) -> str`, `resolve(bundle, role)`.
`src/elevenvt_studio/adapters/godot_capture.py` — `GodotCaptureAdapter.capture(plan) -> CaptureBundle` (driver A) and `LiveSession(port_file).capture(roles)` (driver B), both returning the same type.
`src/elevenvt_studio/perception/contradiction.py` — claim-versus-measurement checking (§9).

Adapters register through the existing `registry.py`; every capture is wrapped in a `Ledger.context()`, so a capture that never completes appears in `studio ledger gaps`.

## 8. MCP transport contract

`tools/call` for perception tools returns:

- one `text` block: a compact summary — capture id, mode, evidence grade, resolution, per-image role/sha256/bytes, verification status, and the measured critic metrics when available;
- one `image` block per requested image, base64, `mimeType: image/png`, `annotations: {"audience": ["user"], "priority": …}`;
- **no** `structuredContent` on these results.

New tools: `perception_capture`, `perception_get`, `perception_probe`.

Size policy, enforced in `transport.py`: downscale so the long edge is ≤ 2560 px and the block stays under 1.5 MiB encoded; refuse with a named error rather than truncate; record the downscale ratio in the summary so an agent knows it is not looking at 1:1 pixels. Masks are sent as their own image blocks because a mask the agent cannot see is a mask it will hallucinate about.

## 9. Perception verification

### 9.1 Cooperative probe

`perception_probe` generates an image containing a random 6-character code in high-contrast type, returns it as an image block with **no** code in the text block, and records the challenge. When the agent's next call includes `probe_answer`, the Studio compares. Match → `perception: verified` for that agent+model+client+version tuple; mismatch or silence → `unverified`, which routes to the external-evaluator path rather than certifying.

This proves the path end-to-end for a cooperating agent. It does not prove a model understood the image, only that bytes arrived and were read back through the model's own output — the strongest claim available without inspecting internals.

### 9.2 Contradiction detection

The deterministic critic already computes ground truth per frame. When an agent states an outcome in text — "the scene is well lit", "the lantern is clearly visible", "this matches the reference" — `contradiction.py` maps recognised claim classes to measured values and records a `perception_contradiction` finding when they disagree (for example a brightness claim against p5 luminance 0.0013 versus a 0.015 floor). Claim recognition is a documented keyword-to-metric mapping with `confidence: "low"` and an explicit `limitations` string; it is a detector for audit, never a verdict on its own, and never a substitute for the critic.

## 10. Provenance and evidence integration

- Authoritative images are written under `reports/evidence/productions/emberkeep/<phase>/captures/<capture_id>/` and covered by `scripts/evidence/manifest.py`; the bundle's hashes must match the manifest or the run fails.
- `contract_sha256` binds every bundle to the art-direction revision it was judged against, so a later contract change invalidates old evidence instead of silently reinterpreting it.
- Gate records reference capture ids, not filenames, so an approval cannot be transferred to a different frame.

## 11. Failure taxonomy

| Condition | Result | Ledger class |
|---|---|---|
| No adapter for project | `unavailable` | `CAPABILITY_ABSENT` |
| Engine exits non-zero | `failed` | `EXECUTION_FAILED` |
| Rendered pixels are black under a real window | `failed` | `EVIDENCE_INVALID` |
| Headless requested | `failed` before launch | `INVALID_REQUEST` |
| Dimensions ≠ declared | `failed` | `EVIDENCE_INVALID` |
| Live session refused token | denial | `POLICY_DENIED` |
| Timeout, partial images | `unverified` | `EXECUTION_INCOMPLETE` |

No condition maps to success.

## 12. Tests

Unit: bundle schema round-trip; hash and dimension verification; uniform-black detection; downscale limit and refusal; `summarize` contains every hash; live-protocol parser rejecting unknown ops and bad tokens; contradiction detector on positive and negative fixtures.

Integration: a fixture adapter producing a known bundle → MCP `tools/call` response asserted to contain one `image` block, matching sha256 in text, and **no** `structuredContent`; a `mode: "live"` bundle asserted rejected by the critic; a capture run against the real project producing 1920×1080 frame plus world and lantern masks whose hashes verify; probe round-trip recorded with the agent identity.

## 13. Exit criteria

This subsystem is proven when all of the following exist as artifacts, not descriptions:

1. A real Emberkeep deterministic capture at 1920×1080 with three verified images and a bundle referencing the current contract hash.
2. An MCP response containing real base64 image blocks, captured from an actual `tools/call`, with the assertion output stored.
3. The critic evaluating the deterministic capture and producing findings whose p5 luminance is computed from the new frame.
4. A live session capture attached to a running game, correctly graded `supervisory` and rejected by the critic.
5. One recorded probe result, pass or fail, with the agent identity it applies to.
6. One contradiction finding produced from a deliberately false claim, demonstrating the detector works and is labelled low-confidence.
7. `studio ledger gaps` showing no silent omissions for any capture performed.

## 14. Risks and unverified assumptions

| Risk | Status | Mitigation |
|---|---|---|
| Mask rendering recipe is not documented by Godot | Unverified | Build and measure in P4; if a mask cannot be made reliable, the affected metrics stay `note` rather than guessing |
| Client-side image forwarding varies by host | Verified varies (Cursor UI, model-gated vision) | Probe records per-agent results; unverified agents are routed to external evaluation, never certified |
| 1080p capture cost | Unknown | Bundle records capture duration; if it breaks the production loop, masks become optional per request |
| `--fixed-fps` reproducibility across machines | Partly documented | Same-machine reproducibility is the claim; cross-machine is asserted only for movie mode and will not be claimed |
| Base64 size | Known | Downscale + encode limit with named refusal |

## 15. Amendments to the Emberkeep implementation plan

- **P4** gains: render layer taxonomy, capture service (both drivers), physics-frame waits replacing wall-clock settling, `--resolution 1920x1080` capture runs.
- **P5** gains: acceptance assertions read bundles, not screenshots, and reject `live` bundles.
- **Gate 1** can only be judged on deterministic 1080p bundles; the existing 720p set remains as historical record, marked superseded.
- P6–P9 unchanged.
