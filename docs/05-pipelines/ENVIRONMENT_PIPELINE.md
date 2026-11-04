# Environment and World Production Pipeline

## Scope

World concept, visual language, reference collection, terrain/blocking, modular architecture, hero props, set dressing, foliage, materials, lighting, atmosphere, traversal, collision, audio zones, VFX, streaming, and optimization.

## Production sequence

1. Define world purpose, player route, scale, story beats, gameplay/navigation and visual thesis.
2. Build top-down layout and camera/blockout; test pacing, sightlines, navigation and combat spaces.
3. Establish modular kit: dimensions, snapping grid, pivots, trim sheets, material families, naming and variation rules.
4. Manufacture hero assets and modular pieces with approved quality; create variants with meaningful authored differences.
5. Build terrain/architecture and set dressing; establish focal composition and navigability.
6. Author materials, lighting, atmosphere, decals, foliage and effects.
7. Add collision, navigation, interaction, audio and streaming rules.
8. Integrate into target engine; inspect at actual player height, FOV, camera distance and movement speed.
9. Run traversal, occlusion, collision, lighting, streaming, memory, draw-call and performance tests.
10. Capture overview maps, representative route captures, close-ups, profiler logs and asset manifests.

## Environment quality criteria

- Visual hierarchy guides the player without accidental confusion.
- Architecture/materials respect coherent world logic and scale.
- Repetition is controlled through authored variation, composition, decals, wear, and modular language.
- Lighting creates depth, navigation and mood without hiding geometry flaws.
- No obvious floating objects, broken collision, z-fighting, light leaks, texture discontinuity, impossible proportions, or camera-visible missing details.
- Performance is measured on target route and view, including worst-case views.
