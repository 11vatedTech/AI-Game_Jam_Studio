# Benchmark Study: AI Game Dev

**Reference:** https://ai-game.dev/  
**Documentation:** https://ai-game.dev/docs  
**Status in this specification:** RESEARCHED; no claim of independent local reproduction.

## Why it matters

AI Game Dev demonstrates that game-engine editors can expose broad, actionable capabilities to AI clients through dedicated plugins, tooling, and a desktop/CLI experience. It is our first functional product benchmark, not a ceiling and not an architecture to copy blindly.

## Publicly documented snapshot

The official docs page observed on 2026-11-04 describes a catalog of 241 capabilities and lists:

- Unreal Engine: 90 MCP tools.
- Unity: 72 capabilities, described as 21 MCP tools plus RQL.
- Godot: 79 MCP tools.
- Ten public projects in the ecosystem.

Official docs: https://ai-game.dev/docs

The product and documentation are dynamically updated. The exact counts can differ between page snapshots and product surfaces; record the capture date and do not treat catalog counts as stable release guarantees. A count indicates discoverable surface area, not that all operations are equally deep, robust, safe, or production-qualified.

## Benchmark dimensions to reproduce

1. Desktop application and CLI setup experience.
2. Automatic discovery/setup of engine plugins.
3. Engine-native inspection and editing.
4. Asset, scene, script, material, object, level, and test workflows.
5. Editor feedback and screenshot/viewport inspection.
6. Capability discovery and structured schemas.
7. Custom extensions and reusable tool packages.
8. Agent/provider neutrality.
9. Authentication, endpoint control, and CI integration.
10. Installation, update, diagnostics, and recovery experience.
11. Real end-to-end outcomes: build, play, inspect, modify, retest.

## Adoption decision — 2026-11-06 (DEFER embed; keep as benchmark)

Pinned facts re-verified this round: the Godot editor integration is IvanMurzak/Godot-MCP `v0.34.0` (2026-10-31, Apache-2.0 with separately-licensed RQL/Code-Exec dependencies under PolyForm Shield 1.0.0). It requires the C#/.NET (Mono) Godot editor plus the .NET 8 SDK. The workstation's installed editor is the standard GDScript build (`4.7.2.stable.official.ed1daf0bf`, no Mono binaries present), so the addon cannot load in this editor at all — adoption is blocked on an editor-variant change, not on will.

Decision: **DEFER**. The Studio's native Godot path (typed `godot.inspect_scene` with engine read-back, headless validation, deterministic smoke, packaged export and launch acceptance) covers the proven subset for the installed editor. Re-evaluate if a .NET editor is installed, weighing the PolyForm-licensed dependencies against the local-first rule, and never route through the hosted ai-game.dev service as a baseline dependency.

## What must be examined at source level

- Desktop/CLI architecture and responsibilities.
- Plugin runtime and editor-thread dispatch.
- Tool schemas and argument validation.
- Whether bulk operations are transactional or undoable.
- Error propagation and postcondition checking.
- How asynchronous operations and long-running imports/builds are handled.
- Security controls around reflective method/script execution.
- Custom tool/extension SDK and versioning compatibility.
- Engine version support and maintenance policy.
- How screenshots, console logs, tests, profiler data, and project state are exposed.
- Which features require hosted services, authentication, subscription, or remote model providers.

## What we should learn—not automatically copy

- A small number of strong native editor bridges can outperform a generic shell-based agent.
- Structured editor actions are easier to validate than free-form generated commands.
- Tool catalogs and extension APIs can make the system expand without core rewrites.
- Engine state, viewport images, logs, and tests must be part of the agent's feedback loop.
- An agent should be able to call the strongest model/provider available without locking application adapters to it.

## Benchmark comparison to our target

| Dimension | AI Game Dev public evidence | Studio target |
|---|---|---|
| Engine coverage | Unreal, Unity, Godot | At minimum these; select other engines by use case and evidence |
| Non-game creative disciplines | Some tools/ecosystem integration; game-focused core | First-class cross-discipline production system |
| Native editor operations | Core strength | Same depth, with safer typed actions and verifiable postconditions |
| Tool extensibility | Public extensions and custom MCP | Versioned, permissioned capability marketplace/catalog |
| Multi-stage manufacturing | Needs task-by-task evaluation | Full cross-application production graphs |
| Visual quality | Must be empirically benchmarked | Explicit art-direction, in-context visual QA, refinement loops |
| Reliability/evidence | Inspect exact workflows | Mandatory evidence for all certified claims |
| Local-first | Some local tools documented; feature-specific hosted components exist | No paid service required for baseline reference workflows |
| Production QA | Engine capabilities available | Unified discipline-specific QA and release gates |

## Required reproduction suite

Create a disposable project in each target engine, then test: inspect project; create scene; author a nontrivial native asset; add logic; connect input; run the project; capture logs and screenshots; deliberately inject a defect; diagnose; repair; rerun; build; reopen from clean state. Measure tool-call count, correction count, execution time, failure recovery, artifact integrity, and visual/functional acceptance.

Do not declare parity or superiority from tool count alone. The competition suite must compare complete task outcomes under equivalent briefs and resource constraints.
