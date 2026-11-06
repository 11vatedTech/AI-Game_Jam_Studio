# High-Priority Candidate: DCC-MCP Core

**Repository:** https://github.com/dcc-mcp/dcc-mcp-core  
**Docs:** https://dcc-mcp.github.io/dcc-mcp-core/guide/architecture  
**Status:** RESEARCHED candidate; not yet adopted or locally certified.

## Why it is strategically important

DCC-MCP Core describes a reusable control plane for agents to operate creative software through MCP and REST. Its published architecture includes a gateway, capability/Action Registry, search/describe/call pattern, Skills discovery, multi-instance routing, a Rust/Python implementation, persistence/workflow-related components, and application adapters. Its catalog spans game engines, DCC, CAD, compositing, image/audio/video, and related production tools.

The project README's catalog contains dozens of adapters (the published catalog snapshot has been reported as 48 entries). This is not a statement that all are stable or production-supported. Some entries may be experimental, limited, or discovery-only. Counts must be checked against the exact pinned source and adapter support matrix.

## Release and maintenance evidence

The GitHub release page observed on 2026-11-04 lists `v0.20.53` as latest, released 2026-11-01. Windows x86_64 CLI and server release assets are published. The adjacent releases include `v0.20.52` (2026-10-29), `v0.20.51` (2026-10-28), and `v0.20.50` (2026-10-27). This rapid release cadence makes version pinning, changelog review, and upgrade regression tests essential. The README documents 48 adapter entries but explicitly says the count includes experimental discovery-only PhotoCraft and is not proof of release-qualified support or automatic installation for every entry.

## Verified upstream facts from the live repository/docs snapshot

The upstream README describes 48 catalog adapter entries covering example hosts such as Maya, Blender, Houdini, 3ds Max, Cinema 4D, Nuke, Unreal, Unity, Godot, Tiled, TouchDesigner, Photoshop, Illustrator, GIMP, Krita, After Effects, Premiere, Kdenlive, OBS, ComfyUI, FreeCAD, OpenSCAD, SketchUp, Material Maker, OpenUSD, ShotGrid, RenderDoc and Wwise. The project explicitly states that the catalog count includes an experimental discovery-only PhotoCraft entry and does not imply release-qualified support for every host. The repository exposes an MIT license; verify dependency and adapter-specific terms separately.

The README also describes three notable shared contracts: (1) shared asset-import/discovery schemas and write-then-read-back postconditions; (2) declarative recipes through list/get/validate/apply operations; and (3) marketplace Skills with example prompts and required recovery/undo metadata for selected entry types. The architecture guide documents modular crates for sandbox/audit, screen capture, USD bridge, workflow catalog, scheduler, content-addressed artifacts, host dispatch, gateway and transport. These are strong design signals to verify in source and execute locally; they are not independent proof that all these subsystems meet our use cases.

## Architecture worth evaluating

- Thin MCP tool surface with search, describe, skill loading, and capability invocation.
- REST surface for non-MCP clients and operational integration.
- Central gateway and multi-instance routing.
- Per-application adapters and host-specific execution boundaries.
- Skills that can scope context/policies to a domain or project.
- Typed action/capability registry and diagnostics. The upstream README also describes a shared asset-import contract, discovery decision schema, write-then-read-back postconditions, declarative recipes, and recovery/undo metadata for marketplace Skills.
- Persistence, artifact, job, workflow, and scheduler facilities documented in its guide.

## Adoption decision — 2026-11-06 (DEFER, do not embed)

Pinned facts re-verified this round: tag `v0.20.53` (`84b940465d652d4d5981e043da9ee95ac0d5d3c7`), MIT license, gateway with configurable bearer-token auth and audit records, zero-auth default preserved for local single-workstation mode, no TLS termination in the gateway itself, and registration-time trust that carries over to other endpoints.

Decision: **DEFER**. Three evidence-backed reasons: (1) the catalog breadth is a coverage map, not per-adapter certification — embedding it would violate the same rule we apply to ourselves; (2) the zero-auth local default plus gateway-without-TLS needs hardening work before it meets the Studio's default-deny posture; (3) the workstation's installed applications (ComfyUI, Blender, Godot, ffmpeg) are now driven through typed native-API adapters with live conformance tests, so there is no proven gap that embedding would close today.

Re-evaluation condition: pin one release, install on this workstation, run its Blender and Godot adapters against disposable projects, and compare failure behavior, permission boundaries and lifecycle handling against the native adapters. Only then decide ADOPT, WRAP or REJECT per application.

## Adopt only after proving

1. Windows 11 install/start/uninstall and no hidden hosted dependency.
2. Exact supported application versions and the stability class of each adapter.
3. Application main-thread and process lifecycle behavior.
4. Path/workspace containment and per-tool permissions.
5. Authentication/network binding defaults; no unsafe remote listener.
6. Script execution, shell, file, network, and arbitrary method-call risks.
7. Multi-instance routing correctness; no cross-project leakage.
8. Cancellation, timeout, error semantics, retry safety, and postcondition verification.
9. Performance overhead, memory use, deadlocks, host crashes, and restart behavior.
10. License compatibility, transitive dependencies, model/content policies, and release process.

## Recommended position

**Priority-1 adoption candidate for the integration control plane, not an automatic foundation lock-in.** The live release page observed 2026-11-04 lists `v0.20.53` (2026-11-01) as latest and provides Windows x86_64 CLI and server packages. The repository links an MIT license. Build a disposable conformance harness around this exact pinned version first. If it passes broad tests, adopt it for compatible applications and add native bridges only where its adapters lack depth, performance, safety, or reliable postconditions. If it fails, isolate the failing adapter or subsystem; do not discard the entire ecosystem without evidence.

## Specific comparison test

For Blender, ComfyUI, Godot, Unreal, and one additional application selected by the first vertical slice, compare DCC-MCP Core against the strongest official/native API and the most mature specialist MCP integration. Run identical tasks and assess state inspection, action coverage, error visibility, transactional behavior, evidence, and recovery. The winner may differ by application; one gateway need not own every capability.
