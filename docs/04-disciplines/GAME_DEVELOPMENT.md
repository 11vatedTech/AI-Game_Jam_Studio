# Game Development Production Domain

## Scope

Game concept and market analysis; design documentation; mechanics; controls; game feel; progression; economy; combat; AI; level/world design; narrative; UI; audio; animation; VFX; physics; multiplayer; saves; accessibility; optimization; builds; distribution; patching and live operations.

## Engine coverage

- **Unreal Engine:** investigate Editor Python, C++/Blueprints, Editor Utility systems, automation framework, commandlets, native plugins, asset registry, Gameplay Ability System where suitable, build tools, profiling and capture.
- **Unity:** investigate Editor scripting/C#, packages, AssetDatabase, scenes/prefabs, UI Toolkit/uGUI, Unity Test Framework, build pipeline and profiling. Track licensing/seat/runtime terms by intended use.
- **Godot:** investigate EditorPlugin, GDScript/C#, scene/resource serialization, GDExtension, headless export, tests and runtime debugging.
- Future engines are added only through a real workflow use case and the adapter conformance suite; evaluate Bevy, O3DE, Stride, Flax and other candidates as appropriate.

## Game production pipeline

1. Intent brief, audience, platform, genre, scope, and production constraints.
2. Design pillars, core loop, controls, game feel, progression, risk register.
3. Prototype mechanics using temporary blockout assets only.
4. Approve visual direction and art bible.
5. Build production-ready player, enemy, environment, props, UI, animation, VFX, and sound assets.
6. Implement gameplay architecture, content data, save/loads, accessibility, and input.
7. Integrate assets and verify import settings, scale, pivots, materials, skeletons, collisions, audio and UI.
8. Playtest and tune; validate edge cases and progression.
9. Profile frame time, memory, loading, draw calls/overdraw, shader cost, audio voices, and network behavior as relevant.
10. Build, test, package, smoke test on target platform, and produce release evidence.

## Required game quality gates

- The core loop is playable and understandable without developer intervention.
- Input response, hit feedback, timing, camera, animation, audio, and UI reinforce one another.
- No placeholder final art, default fonts, unreviewed stock assets, or debug controls in release.
- Interactions work with real assets and gameplay state.
- Combat/mechanics are tuned against measured playtests where relevant.
- Runtime logs are clean of critical errors; performance meets target budgets on declared hardware.
- Save/load, pause/resume, resolution changes, controller/input rebinding, and expected failure states are tested.
- Build is reproducible from source and declared dependencies.

## End-to-end certification scenario

Produce a small but professionally art-directed vertical slice with main menu, one representative playable level, coherent player/enemy/prop set, distinct materials, at least two animation states with clean transitions, sound/music, UI, gameplay loop, pause/settings, win/fail state, performance capture, and clean platform build. This must prove art-to-engine production, not just editor automation.
