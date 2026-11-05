# Perception Transport and Verification — design

**Status:** revised after design review; awaiting approval
**Date:** 2026-11-05 (rev 2)
**Supersedes:** rev 1 (`d2887f6`)
**Scope:** one subsystem of the Studio Production Runtime
**Predecessors:** `2026-11-05-emberkeep-reference-production-design.md`, `2026-11-05-emberkeep-implementation-plan.md`

## 1. Thesis: three obligations, enforced separately

The review's central correction is adopted as the organising principle. A perception subsystem can satisfy one of these and fail the others, and each needs its own enforcement:

| Obligation | Question | Enforced by |
|---|---|---|
| **Transport** | Did the pixels reach the agent? | Sized, encoded image blocks + a probe that proves readback |
| **Interpretation** | Could the agent read what arrived? | Per-client probe results and an explicit identity record |
| **Authority** | May a finding from this capture decide anything? | Evidence grade derived from capture mode *and* repeatability qualification |

Rev 1 collapsed these. It promised images on the strength of a content-block contract, assumed a Godot mechanism that does not exist, and used the word "deterministic" for a command-line flag. Each of those is fixed below.

Two facts still make this urgent and concrete:

1. Every `tools/call` response in `mcp/server.py` returns `{"type": "text"}` plus `structuredContent`. No image path exists. Anything screenshot-like added on top of that transport hands the agent a file path and calls it perception.
2. The four existing Emberkeep captures are 1280×720 while `art_direction.json` declares 1920×1080. The critic already reports `frame_set_meets_declared_resolution: false`. Out-of-declaration evidence cannot support a gate.

## 2. Verified facts this design rests on

Claims that shape a contract are listed with their source and their confidence, so a later reader can attack the source rather than re-litigate the conclusion.

| # | Fact | Source | Confidence |
|---|---|---|---|
| F1 | MCP `ImageContent` is `{type:"image", data(base64), mimeType, annotations?}`; content blocks are mixable; the spec sets no size cap. | MCP schema (rev 1 research) | High |
| F2 | `annotations.audience` declares the *intended audience* of content. A user-only annotation is the wrong signal for a model-facing image. | MCP schema, `annotations` | High |
| F3 | OpenAI Agents SDK: `use_structured_content` / `useStructuredContent` **defaults to `false`** in both Python and TypeScript. Only when `true`, non-empty, and not an error does `structuredContent` replace the content blocks. | `agents/mcp/server.py` docstring; `@openai/agents-core` `mcp.d.ts` (0.21.0) | High |
| F4 | Python SDK converts MCP image blocks to model image tool-outputs automatically (`ToolOutputImageDict`, `data:` URL), but only on the content-block path. | `agents/mcp/util.py` | High |
| F5 | TypeScript SDK returns the raw MCP `content` array at its MCP layer with **no** base64→`data:` conversion found in `dist/mcp.js`; any later coercion is unverified. | `@openai/agents-core` 0.21.0 published build | Medium — absence of code, not a documented guarantee |
| F6 | Anthropic's API allows ~10 MB base64 images; its computer-use tool **rejects** screenshots over the model's image limits rather than resizing. Limits are model-dependent. | Claude platform docs (rev 1 research) | High |
| F7 | Godot `--fixed-fps` forces a fixed rate and disables real-time sync; it is not a determinism guarantee. Physics ticks and rendered frames are separate timelines. | Godot command-line + physics docs | High |
| F8 | A global RNG seed does not seed independent `RandomNumberGenerator` instances. | Godot `RandomNumberGenerator` docs | High |
| F9 | `Camera3D.cull_mask` restricts what a camera *renders*; culled geometry contributes nothing, **including depth**. A mask camera that culls occluders produces a silhouette that shows objects through walls. | `Camera3D.cull_mask`, `VisualInstance3D.layers` docs | High |
| F10 | Godot 4 has no object-ID / instance-ID / segmentation debug buffer; `Viewport.DebugDraw` has no such mode; debug modes are unsupported on Compatibility entirely. | `Viewport.DebugDraw` full enum | High |
| F11 | A viewport's depth texture **cannot be read from another viewport**. Render-then-depth-compare across viewports is not possible in stock Godot. | "Advanced post-processing" docs | High |
| F12 | Occlusion culling (`OccluderInstance3D`) is AABB-granular and all-or-nothing per object; it cannot cull part of an object. | "Occlusion culling" docs | High |
| F13 | `--headless` "disables all rendering". Capture requires a real window. | Godot command-line docs | High |
| F14 | Our MCP server implements the legacy `initialize` handshake and defaults `protocolVersion` to `2025-11-25`. The 2026-07-28 revision removed the handshake and moved client identity into per-request metadata. | `src/elevenvt_studio/mcp/server.py:47-50`; MCP changelog | High for our code; protocol revision date confirmed in rev 1 research |

F5 is the reason the probe is not optional: image delivery is *demonstrated* in the Python path and *unproven* in the TypeScript path, and no annotation can fix that. Only a readback test settles it per client.

## 3. Decisions

| Decision | Reason |
|---|---|
| Capture bundles, not loose PNGs | A frame without provenance, masks and verification status is a picture, not evidence. |
| Two evidence classes: `deterministic` and `live` | Only reproducible captures may feed a gate. |
| Grade is derived, not declared | `mode` says how it was produced; `evidence_grade` says what it may decide. Determinism is earned by repeatability, not asserted by a flag (F7). |
| Both drivers | Requested. One bundle format, one game-side capture service, so supervision cannot drift from evidence. |
| Images as MCP `image` blocks, **no** `structuredContent` | Works under the SDK default and stays safe if a host enables the structured-content preference (F3). |
| No `annotations.audience` on perception images | Audience is the intended audience; user-only would deprioritise content the model must see (F2). Delivery is proven by probe, not by annotation. |
| Separate authoritative and transport artifacts | The hash-protected original is never modified to fit a payload budget. |
| Masks are three distinct measurements, none gate-eligible until fixture-proven | `cull_mask` alone yields a silhouette with no occlusion (F9), and no ID buffer exists (F10). |
| Verification is a probe, not an inference | With no source of an agent's free text (§10), only an explicit challenge/response is honest. |
| No headless capture | F13. |
| Transport proven before the adapter is built | Building the game-side capture first risks discovering at the end that the connected agent cannot consume it. |

## 4. Scope

**In scope:** capture contract and bundle format, Godot capture service (both drivers), Studio capture adapter, MCP image transport with profiles, probe verification and identity provenance, working-tree provenance, mask semantics and their fixture, failure taxonomy, tests, exit criteria, protocol compatibility, and amendments to the Emberkeep plan.

**Out of scope, each a separate spec:** live production dashboard, capability profiling and routing, per-discipline critics, automated repair, the qualification benchmark beyond the single probe, and **all free-text claim analysis** (deferred, §10.3).

## 5. Evidence class and grade

| `mode` | Repeatability qualified | `evidence_grade` | Diagnostics | Gate / certification | Use |
|---|---|---|---|---|---|
| `deterministic` | yes | `authoritative` | yes | yes | Gate 1/2 evidence, acceptance |
| `deterministic` | no / not run | `supervisory` | yes | **no** | Iteration, provisional review |
| `live` | n/a | `supervisory` | yes | **no** | Supervision, dashboard |

This resolves the rev-1 contradiction. **The critic evaluates every bundle.** What live and unqualified evidence cannot do is satisfy a gate. The gate evaluator — not the critic — is the component that rejects non-authoritative evidence, so an agent can adjust a lantern, capture the live result, receive a real diagnostic, and iterate without that screenshot ever becoming certification.

`evidence_grade` is computed by the loader from `mode` plus `qualification.repeatability.status`, and written into the bundle. It is not a client-supplied field. Schema validation refuses a bundle whose declared grade differs from the computed one.

## 6. Capture bundle contract

Written to `<out>/bundle.json` beside the images. Schema `schemas/capture-bundle.schema.json`, strict (`additionalProperties: false`), `schema_version: "2.0"`.

```json
{
  "schema_version": "2.0",
  "capture_id": "uuid4",
  "mode": "deterministic",
  "evidence_grade": "authoritative",
  "application": {
    "name": "emberkeep",
    "adapter_version": "1.0.0",
    "engine_version": "4.7.2.stable",
    "project_path": "Games/emberkeep/game",
    "rendering_method": "forward_plus",
    "requested_resolution": [1920, 1080],
    "resolution": [1920, 1080],
    "msaa_3d": 2,
    "screen_space_aa": 1,
    "stretch_mode": "canvas_items"
  },
  "request": {
    "roles": ["frame", "mask_lantern_visible", "mask_world"],
    "physics_tick": 180,
    "render_frame": 182,
    "camera": {"side": "west", "position": [0, 2, 6]},
    "state": {"lantern_lit": true, "beacon_lit": false},
    "seed": 20261105,
    "rng_instance_seeds": {"loot": 771, "weather": 4421}
  },
  "qualification": {
    "repeatability": {
      "status": "qualified",
      "runs": 3,
      "state_digest": "sha256:…",
      "render_contract": "exact_sha256",
      "tolerance": null
    }
  },
  "artifacts": [
    {
      "role": "frame",
      "semantics": "render",
      "path": "frame.png",
      "sha256": "…",
      "width": 1920,
      "height": 1080,
      "mime": "image/png",
      "bytes": 2142331,
      "derived_from": null
    }
  ],
  "provenance": {
    "contract_sha256": "…",
    "plan_sha256": "…",
    "git": {
      "commit": "…",
      "dirty": false,
      "tree_sha256": "…",
      "untracked_or_patch_sha256": "…"
    },
    "engine": {"version": "4.7.2.stable", "executable_sha256": "…"},
    "gpu": {"vendor": "…", "device": "…", "driver": "…"},
    "settings": {"fixed_fps": 60, "physics_ticks_per_second": 60, "warmup_frames": 30},
    "host": "win32",
    "started_at": "…",
    "finished_at": "…",
    "duration_ms": 1840
  },
  "verification": {"status": "verified", "checks": [{"name": "…", "ok": true, "detail": "…"}]}
}
```

`verification.status` ∈ `verified`, `unverified`, `failed`. `verified` requires every declared check to pass.

**Checks, always run:** file exists; sha256 matches; decodes as declared mime; dimensions equal `application.resolution`; mask dimensions equal frame dimensions; `request.roles` ⊆ artifact roles; no duplicate roles; frame is not effectively black (p99 linear luminance ≤ 0.002) unless `expect_black` is declared; every mask's pixel values fall inside its declared set.

**Image filenames derive from role, never from client input:** `frame.png`, `mask_world_visible.png`, `mask_lantern_visible.png`, `mask_lantern_silhouette.png`, `mask_lantern_illumination.png`, `diff.png`.

**Path confinement (adapter side):** reject absolute paths, `..` traversal, symlinks resolving outside the capture directory, declared MIME types outside the allowed set (`image/png`, `image/jpeg`, `image/webp`), metadata over 64 KiB, and any artifact listed twice. Image files are written and hashed first; `bundle.json` is written **last**, atomically (temp file in the same directory, then replace). A bundle never describes partially written evidence.

## 7. Determinism is a procedure; authority is earned

Rev 1 wrote "reproducible by construction". That was wrong: `--fixed-fps` removes real-time sync but does not pin frame content (F7), and a global seed does not pin instance RNGs (F8).

**Three separate sub-results**, never collapsed into one boolean:

| Sub-result | Question |
|---|---|
| `simulation_repeatability` | Do game state, positions, events and outcomes agree across runs? |
| `render_repeatability` | Do output pixels meet the exact-hash or declared-tolerance contract? |
| `capture_integrity` | Are files, hashes, dimensions and the bundle internally valid? |

Identical pixels can conceal different internals, and equivalent images can differ by a pixel or two. Both failures are reportable separately.

**Procedure rules:**

- Gameplay logic stays on `_physics_process`; capture waits count physics frames. `_settle(0.9)` (wall-clock) is replaced for capture, because a wall-clock settle cannot land on a reproducible frame.
- Every bundle records **both** `physics_tick` and `render_frame`.
- `--fixed-fps 60`, physics 60 Hz, `Viewport.physics_interpolation_mode = PHYSICS_INTERPOLATION_MODE_OFF` — an interpolated frame blends two ticks and is not a reproducible state.
- RNG: the global seed **and** each independent `RandomNumberGenerator` instance are seeded, enumerated in `request.rng_instance_seeds`, and asserted in a test that no unseeded instance exists.
- `warmup_frames: 30` before the first capture; recorded so it can be challenged.
- Effects that cannot be made frame-stable are disabled for capture and named in provenance.

**Qualification protocol:** three consecutive same-machine runs with the same commit, plan, seed, engine, renderer and configuration. Compare state digests, per-metric values, and pixels.

- Exact image hashes across all three → `render_contract: "exact_sha256"`, `tolerance: null`.
- Hashes differ → measure the empirical delta, record `measured_max_delta`, and only then declare a tolerance that bounds it. **The tolerance is derived from measurement and then frozen**; no tolerance number is invented in this spec, because an invented one would be the same guess as calling the flag deterministic.
- Three runs that do not converge → `status: "unqualified"`, grade `supervisory`, and the divergence becomes a finding rather than a footnote.

## 8. Masks: three measurements, none trusted yet

Rev 1 promised that a `SubViewport` + `cull_mask` "produces a 1-bit mask". It does not, and the failure mode is worse than absent: culled geometry writes no depth, so a lantern-only camera renders the lantern *through* a wall (F9). That mask would report visibility that does not exist — a measurement that looks like success.

| Role | Semantics | Can be gate evidence? |
|---|---|---|
| `mask_world_visible` | World geometry pixels that survive scene depth testing | Only after fixture proof |
| `mask_lantern_visible` | Lantern pixels **respecting occlusion** | Only after fixture proof |
| `mask_lantern_silhouette` | Full projected lantern silhouette, occlusion ignored | Never — comparator only, must be labelled |
| `mask_lantern_illumination` | Pixels whose value changes when the lantern's light is toggled | Only after fixture proof |

`semantics` is a required field on every mask artifact, so an unoccluded silhouette can never be read as a visibility measurement.

**Mechanism (a construction, not a documented recipe):** a `SubViewport` sharing the parent `World3D` (so it renders the same instances), `Transparent BG = true`, `msaa_3d = MSAA_DISABLED` (MSAA blends ID colours at edges), default `cull_mask` on **all** layers. Within that single viewport, occluders receive a depth-only opaque `material_override` (`render_mode unshaded, depth_draw_opaque;` with `ALPHA_SCISSOR_THRESHOLD`, never writing `ALPHA`, which would move it to the transparent pipeline), and target nodes receive a flat unshaded ID colour with default `depth_test_default`. Because both passes share one framebuffer, depth testing rejects occluded target pixels — the occlusion comes from depth, not from culling.

Two consequences that must be stated rather than discovered:

- The depth texture cannot be read across viewports (F11), so "render IDs, then compare against main-scene depth" is not available. The two-pass-in-one-viewport construction is the only stock option, and it is **unverified until the fixture passes**.
- Sharing a `World3D` means `material_override` mutates the live scene. The mask pass therefore runs against a **frozen** frame: capture the `frame` artifact first, then apply overrides, render each mask, read back, and restore. Masks are only valid for the frame they were captured against, which the bundle records.

**Illumination** is not a segmentation at all: render the frozen frame with the light on and off, and diff. That difference image is its own artifact with `derived_from` set to both source captures.

**Gate rule:** no mask-derived metric may gate anything until a controlled fixture — known object positions, deliberate overlap, and a wall between camera and lantern — has been visually inspected and its expected pixel regions asserted in a test. If the fixture fails, mask metrics stay `note`. They never become invented measurements.

**Render layer taxonomy** (needed regardless, so masks and culling agree):

| Layer | Contents |
|---|---|
| 1 | World geometry (terrain, architecture, walls) |
| 2 | Props and interactables |
| 3 | Lantern and its light-emitting children |
| 4 | Player |
| 5 | VFX / particles |

Layers are the *selector* for which nodes get which override material. They are not the occlusion mechanism.

## 9. Capture service

New, `Games/emberkeep/game/scripts/capture/service.gd`, loaded only when a capture flag is present, so an ordinary play session pays nothing and opens no socket.

### 9.1 Render configuration and resolution

`--resolution` requests a window size; the adapter verifies the **actual** rendered image dimensions rather than trusting the argument. Three resolutions are distinguished and reported separately:

| Resolution | Meaning |
|---|---|
| 1280×720 | The game's normal development configuration |
| 1920×1080 | Required capture resolution for evidence |
| actual | What the file really is, asserted against `requested_resolution` |

Forcing 1080p for evidence is acceptable because the art-direction contract demands 1080p evidence. It is **not** proof that the packaged game renders correctly at 1080p, and the spec says so: P4 exercises both modes and reports both, rather than treating a capture flag as a shipped-configuration test.

### 9.2 Driver A — plan-driven

```
godot --path Games/emberkeep/game --resolution 1920x1080 --position 0,0 \
      --fixed-fps 60 --capture-plan plan.json --capture-out <dir>
```

`plan.json` is an ordered list of `{physics_tick, roles, camera, state, seed}`. The game applies each entry's state at its tick, captures after `RenderingServer.frame_post_draw`, writes artifacts, then the bundle, and exits 0 only if every entry verified. Exit code is not evidence; the bundle is.

### 9.3 Driver B — live session

```
godot --path Games/emberkeep/game --capture-live --capture-token-file <path> --capture-out <dir>
```

Binds `127.0.0.1` on port 0 and writes `session.json` (`{port, pid, started_at, project}`) into `<out>`, so the Studio discovers it instead of guessing ports. JSON-lines protocol; **no session exists until authentication succeeds on that connection.**

| Op | Request | Response |
|---|---|---|
| `hello` | `{"op":"hello","token":"…"}` | `{"ok":true,"mode":"live"}`; wrong token closes the socket |
| `capture` | `{"op":"capture","roles":[…]}` | bundle path + verification status |
| `state` | `{"op":"state"}` | frame index, scene state, fps |
| `quit` | `{"op":"quit","token":"…"}` | clean exit |

Bytes never travel over the socket: the game writes the bundle and returns its path and hashes, keeping one code path for image production.

**Hardening:** loopback bind only; 32-byte token from a file restricted by Windows ACL to the current user; constant-time comparison; token required for `hello` and `quit`; maximum 3 failed auth attempts per connection; **maximum JSON line 64 KiB**; 5 s per-request timeout; one capture in flight; 20 captures/minute per session; at most 4 concurrent connections; stale sessions detected by pid liveness and a 300 s idle exit; operation whitelist with no arbitrary evaluation, no shell, no client-supplied paths; writes confined to `--capture-out`. Every refusal is recorded as a denial, never swallowed.

## 10. Studio-side adapter

```
src/elevenvt_studio/perception/bundle.py        # CaptureBundle, load(), verify(), compute_grade()
src/elevenvt_studio/perception/transport.py     # TransportProfile, encode(), image_blocks(), summarize()
src/elevenvt_studio/perception/probe.py         # challenge issue/verify, identity record
src/elevenvt_studio/adapters/godot_capture.py   # GodotCaptureAdapter (A), LiveSession (B)
```

Adapters register through `registry.py`; every capture runs inside `Ledger.context()`, so a capture that never completes appears in `studio ledger gaps`. `contradiction.py` from rev 1 is **removed** (§10.3).

## 11. MCP transport contract

### 11.1 Response shape

`tools/call` for perception tools returns:

- one `text` block: capture id, mode, computed grade, actual resolution, per-artifact role/sha256/bytes/transform, verification status, and measured metrics when available;
- one `image` block per requested artifact, base64, correct `mimeType`;
- **no `annotations.audience`** (F2) and **no `structuredContent`**.

Omitting `structuredContent` is chosen for three reasons, in this order: it is correct under the SDK default `false` (F3); it stays correct if a host enables the preference; and it removes any dependence on which SDK converts images (F4 vs F5). The integration test exercises **both** `use_structured_content` settings, because our contract must not depend on a host's default.

### 11.2 Transport profiles

A single global `max_edge` is not a model-agnostic contract: limits are model-dependent (F6). Transport accepts a profile:

```
TransportProfile
    max_image_bytes, max_width, max_height, max_long_edge
    max_visual_tokens, supported_formats
    preferred_frame_format, mask_format
    max_images_per_call, max_total_payload_bytes
```

Rev 2 ships one conservative default profile, named and versioned (`studio-default-v1`). Capability qualification later supplies measured profiles per agent/model/client. Transport never assumes which model is connected.

### 11.3 Artifact classes and adaptive encoding

| Artifact | Authoritative | Transport |
|---|---|---|
| Game frame | PNG, full resolution, sha256 | JPEG or WebP at quality ≥ 60 |
| Segmentation mask | PNG, lossless | PNG, lossless |
| Difference / diagnostic | PNG, lossless | PNG or lossless WebP |
| Crop | PNG derived from original | PNG |

The revision's concrete defect is fixed here: the rev-1 example frame is 2,142,331 bytes, which is ~2.86 MB base64 and cannot fit a 1.5 MiB block — and a 2560 px long edge does nothing for a 1920×1080 frame that is already under it. Encoding therefore reduces within a **declared fidelity envelope** (scale ≥ 0.5, quality ≥ 60, long edge ≤ profile max) until the block fits; if it cannot, return a named refusal and offer `perception_crop` instead. Truncation and silent re-encoding are both forbidden.

Every transport artifact records provenance: source sha256, transport sha256, dimensions, format, quality, scale, and the profile used. Written to `<capture_id>/transport.json`, deliberately **outside** `bundle.json`, so derived artifacts never change the authoritative bundle hash.

### 11.4 Tools

| Tool | Purpose |
|---|---|
| `perception_capture(plan or roles, mode)` | Run a capture; returns bundle summary + images |
| `perception_get(capture_id, role)` | Re-fetch one artifact from an existing capture |
| `perception_crop(capture_id, role, region, output_size)` | Derivative crop for detail inspection; records `derived_from` |
| `perception_probe()` | Issue a challenge; returns an image containing a code, no code in text |
| `perception_probe_verify(challenge_id, answer)` | Evaluate a probe answer; records the result |

Progressive inspection is explicit because a compressed full frame is sometimes insufficient: an agent may correctly spot a bad lantern at 1080p and still need a close-up for material or seam defects. The original remains authoritative; crops are derivative evidence referencing it.

### 11.5 Protocol target

The server currently implements only the legacy handshake and defaults `protocolVersion` to `2025-11-25` (F14). The 2026-07-28 revision removed `initialize`, added `server/discover`, and moved client identity into per-request metadata.

This subsystem targets **both**: legacy `initialize` for current clients, and the 2026-07-28 discovery path, with the image transport contract tested independently of the negotiated version. A long-lived agent-agnostic platform cannot pick one era, and transport must not silently change behaviour with the version.

## 12. Verification

### 12.1 Probe contract

An agent cannot submit an extra argument to an unrelated tool, so rev 1's "when the agent's next call includes `probe_answer`" was unimplementable. The contract is two calls:

1. `perception_probe()` → returns `{challenge_id, expires_at}` in text and an image containing a random 6-character code. **The code never appears in any text block.**
2. `perception_probe_verify(challenge_id, answer)` → `{match: bool}`.

Challenges are single-use, expire after 180 s, and are bound to the Studio agent instance and client identity that requested them. Match → `perception: verified` **for that identity tuple only**. Mismatch, expiry or silence → `unverified`, routed to external evaluation rather than certification.

A probe proves bytes arrived and were processed into output. It does not prove comprehension, and the spec will not claim it does.

### 12.2 Identity provenance

MCP identifies the client application, not the model. These are stored separately and never merged:

| Field | How it is established |
|---|---|
| MCP client name/version | Client metadata, only when supplied |
| Studio agent instance | Registered Studio identity |
| Provider / model | Host configuration or explicit registration — **self-reported, marked as such** |
| Model version | Provider/configured metadata |
| Vision result | Probe evidence, per challenge |

A model is never recorded as verified merely because an agent reported its own name.

### 12.3 Deferred: free-text claim analysis

Rev 1 promised that "when an agent states an outcome in text" the critic checks it. There is no defined source for that text: an MCP server receives requests and tool arguments, not the model's conversation. Building a keyword detector against a stream we do not have would have produced a feature that could pass its unit tests and never fire in production.

It is removed from this subsystem. Claim analysis belongs with the agent-observation subsystem, where an explicit assertion interface or a host integration can supply a real source. The architectural need is recorded, not fabricated.

## 13. Failure taxonomy

| Condition | Result | Ledger class |
|---|---|---|
| No adapter for project | `unavailable` | `CAPABILITY_ABSENT` |
| Engine exits non-zero | `failed` | `EXECUTION_FAILED` |
| Black frame under a real window | `failed` | `EVIDENCE_INVALID` |
| Headless requested | `failed` before launch | `INVALID_REQUEST` |
| Dimensions ≠ declared | `failed` | `EVIDENCE_INVALID` |
| Mask fixture mismatch | mask metrics → `note` | `EVIDENCE_INVALID` |
| Transport cannot fit the profile budget | refusal, reason named | `TRANSPORT_LIMIT_EXCEEDED` |
| Live session auth failure | denial, socket closed | `POLICY_DENIED` |
| Timeout, partial artifacts | `unverified` | `EXECUTION_INCOMPLETE` |
| Repeatability runs diverge | `unqualified` + finding | `EVIDENCE_INVALID` |

No condition maps to success.

## 14. Build order

The review's most important recommendation is adopted as a **hard gate**. Do not start with the socket or the SubViewports.

| Phase | Deliverable | Exit test |
|---|---|---|
| **A. Transport proof** | A known generated test image returned through the real `tools/call` as an image block | A real connected agent identifies a marker in it; identity, hashes and result recorded; deliberately break delivery and prove the test catches it |
| **B. Frame capture** | Driver A, real 1080p Emberkeep frame, bundle + provenance | Frame verifies; 3-run repeatability reports its honest result |
| **C. Masks** | Three mask semantics + fixture | Occlusion fixture passes, or mask metrics stay `note` |
| **D. Live** | Driver B, hardened socket | Live capture graded `supervisory`, diagnostics work, gate refuses it |

Phase A is a prerequisite, not a milestone: if a connected agent cannot consume the image payload, building B–D first would produce an elaborate capture system whose output nothing can see.

## 15. Tests

**Unit:** schema round-trip at `2.0`; computed grade vs declared grade mismatch rejected; path confinement (absolute, `..`, escaping symlink, duplicate role, unknown mime, oversized metadata); hash/dimension/mask-dimension checks; black-frame threshold; transport profile reduction ladder, envelope exhaustion and named refusal; `summarize` contains every hash; live-protocol parser rejecting unknown ops, oversized lines and bad tokens; probe expiry, single-use and binding.

**Integration:**

1. **Real image delivery** — fixture bundle through `tools/call`; one `image` block per artifact, matching sha256, **no** `structuredContent`, **no** `audience` annotation; asserted under both `use_structured_content` settings.
2. **Transport integrity** — original and transport hashes, dimensions, format, quality, profile recorded and consistent; oversize input refused rather than truncated.
3. **Mask correctness** — controlled fixture with known positions, overlap and a wall between camera and lantern; expected visible regions asserted; silhouette and visible masks differ in exactly the occluded region.
4. **Repeatability** — same plan three times under pinned environment; simulation, render and integrity reported as three results.
5. **Live evaluation** — tweak a scene property at runtime, capture, receive advisory findings, and assert the gate refuses the bundle.
6. **Client incompatibility** — an agent that cannot receive image blocks is classified unsupported and never marked vision-qualified.
7. **Failure integrity** — black frame, mismatched mask, corrupted image, unauthorized socket request, interrupted capture: each fails or stays unverified, and none produces authoritative evidence.
8. **Adversarial description** — a vision-capable agent deliberately describes a known object incorrectly; the Studio preserves image, independent measurement and the discrepancy (the claim recorded by the harness, since the Studio has no claim source) so bad perception is investigable, not just success.

## 16. Exit criteria

Proven when these exist as artifacts, not descriptions:

1. A real deterministic Emberkeep capture at 1920×1080 with verified artifacts and a bundle referencing the current contract hash.
2. A real `tools/call` response containing image blocks, with the assertion output stored, under both structured-content settings.
3. A live capture from a running game, graded `supervisory`, returning diagnostics, **and refused by the gate**.
4. A recorded probe result with its identity tuple, including one deliberate failure.
5. Three-run repeatability evidence for the acceptance plan, with its honest outcome (qualified or unqualified).
6. Mask fixture result — passing fixture, or explicit `note` classification.
7. Negative-fixture suite green, with no case producing authoritative evidence.
8. `studio ledger gaps` showing no silent omissions.
9. Protocol compatibility: image transport verified under both the legacy handshake and the 2026-07-28 path, or the unsupported path explicitly reported.

## 17. Risks

| Risk | Status | Mitigation |
|---|---|---|
| Two-pass mask construction is derived, not documented (F9–F11) | Unverified | Phase C fixture; failure demotes mask metrics to `note` instead of guessing |
| TypeScript SDK may not convert images to model inputs (F5) | Unverified | Probe per client; unsupported clients routed to external evaluation |
| Render repeatability may not hold even with fixed FPS | Unverified | Three-run qualification; tolerance derived from measurement, never invented |
| 1080p capture plus mask passes is slow | Unknown | `duration_ms` recorded; if the loop suffers, masks become per-request optional |
| Protocol dual support drifts | Known | Transport tests independent of negotiated version |
| Sharing `World3D` mutates live materials for mask passes | Known | Masks run only against a frozen frame and are labelled as such |

## 18. Amendments to the Emberkeep plan

- **P4** gains: render layer taxonomy, capture service (both drivers), physics-tick waits replacing wall-clock settling, seeded RNG enumeration, repeatability qualification, 1080p capture runs, and the mask fixture.
- **P5** gains: acceptance assertions read bundles, reject non-authoritative grades, and test both supported capture modes.
- **Gate 1** is judged only on `authoritative` deterministic 1080p bundles. The existing 720p set remains historical record, marked superseded, and is not retroactively graded.
- P6–P9 unchanged.

## 19. Review disposition

| Review item | Disposition |
|---|---|
| 1.1 audience annotation | **Accepted** — annotations omitted entirely from perception images |
| 1.2 SDK shadowing overstated | **Accepted, with correction**: default is `false` in both SDKs; the stronger finding is F5 (TS conversion absent/unverified), which makes the probe mandatory rather than optional |
| 1.3 size policy vs example | **Accepted** — authoritative/transport split, adaptive encoding, provenance, named refusal |
| 1.4 cull_mask is not a mask | **Accepted** — three semantics, depth-based two-pass construction, fixture-gated, silhouette explicitly non-authoritative |
| 1.5 live must be critiqued | **Accepted** — critic evaluates all; the gate rejects, not the critic |
| 1.6 fixed FPS ≠ determinism | **Accepted** — procedure vs earned authority; three sub-results; three-run protocol |
| 1.7 contradiction detector | **Accepted** — removed and deferred with the missing-source reason recorded |
| 1.8 probe needs two calls | **Accepted** — `perception_probe` + `perception_probe_verify`, single-use, bound, expiring |
| 2.1 model-aware limits | **Accepted** — `TransportProfile`, versioned default |
| 2.2 working-tree provenance | **Accepted** — dirty state, tree hash, patch hash, engine exe, GPU/driver |
| 2.3 mask validation | **Accepted** — pixel set, semantics, MSAA-off, occlusion fixture |
| 2.4 path confinement | **Accepted** — plus bundle-written-last atomicity |
| 2.5 socket hardening | **Accepted** — line cap, timeouts, rate/connection limits, ACL, auth-before-session |
| 2.6 determinism sub-results | **Accepted** — three named results |
| 2.7 protocol target | **Accepted** — dual support, transport tested independently; our server is legacy-only today (F14) |
| 2.8 progressive inspection | **Accepted** — `perception_crop`, conservative profile first |
| 2.9 resolution meaning | **Accepted** — three resolutions distinguished; capture flag is not a shipping test |
| Duplicate table / repeated checks | **Accepted** — document rewritten as one authoritative text |
| Build order | **Accepted** — Phase A is a hard prerequisite gate |
