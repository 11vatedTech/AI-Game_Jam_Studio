# Unreal and Unity — Adapter Strategy

Neither engine is currently executable through this runtime. Do not claim otherwise.

## Unreal

Inspect the exact installed editor version first. Compare official Editor Python scripting, Editor Utility Widgets/Blueprints, C++ editor modules, Remote Control/Web APIs, automation tests, commandlets, build tooling and mature MCP products including AI Game Dev. Prefer native editor semantics for asset/level/material/animation/blueprint inspection and mutations. Python Editor Scripting is editor-scoped and version-dependent; it must not be mistaken for a general runtime scripting interface.

A conformant adapter must cover project/plugin/version discovery, asset registry queries, import/export, level/world operations, material/texture, mesh/skeleton/animation, blueprint or gameplay source changes, editor automation, build/cook/package, runtime launch, logs, screenshots and profiling. Every write has a read-back postcondition. Main-thread/editor lifecycle constraints must be honored.

## Unity

Inspect the exact installed Editor and package versions. Compare official Editor scripting APIs, AssetDatabase, UI Toolkit, package APIs, test framework, build pipeline, command-line batch mode, profiler and AI Game Dev/RQL alternatives. Pin package manifest and lockfile.

A conformant adapter must cover project/package discovery, hierarchy/component/resource inspection, prefabs/scenes, materials/shaders, animation, UI, scripts, importer settings, tests, player builds, runtime launch, logs, screenshots, profiling and package provenance.

## Selection rule
Choose the first engine vertical slice based on actual installed and healthy toolchains, not preference or remembered versions. Run an identical representative benchmark in every available engine before making a comparative claim. Avoid duplicate engine-specific abstraction until the native APIs have been investigated; unify only the capability contracts whose semantics genuinely match.
