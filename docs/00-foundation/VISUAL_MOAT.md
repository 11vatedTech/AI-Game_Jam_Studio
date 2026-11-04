# Visual Moat — Professional Art Direction and Execution

## Objective

The visual moat is the studio's ability to produce work that is not merely technically valid or AI-generated, but art-directed, distinctive, polished, coherent, and convincing at the size, distance, speed, and context in which the audience experiences it.

## Principles

1. **Design before generation.** Establish visual thesis, audience, medium, genre, mood, composition rules, reference hierarchy, palette, materials, typography, camera language, and motion principles before mass production.
2. **Reference intelligently.** Use professional reference boards and breakdowns. Extract principles, not just surface appearance. Track provenance and avoid copying protected expression or branded assets without authorization.
3. **Use the right medium.** A stylized 2D game, realistic cinematic scene, CAD assembly, icon set, motion graphic, and web interface require different pipelines and review criteria.
4. **Generate editable production assets.** Final assets must have the native structure required by the task: layers, paths, meshes, topology, UVs, rigs, nodes, timelines, components, or source files. Flattened images are insufficient when editability is required.
5. **Reject generic output.** Default prompt outputs are starting material, not approved final work. Refine composition, silhouette, structure, materials, lighting, color, edge quality, typography, motion, and consistency.
6. **Evaluate in context.** Test assets in the actual game camera, scene, UI layout, video timeline, device viewport, and target display. Do not approve solely from a zoomed render.
7. **Maintain a coherent art bible.** Store visual rules, approved references, palette tokens, material definitions, typography, character turnarounds, environmental logic, lighting rules, and forbidden deviations.
8. **Preserve cross-shot and cross-asset continuity.** Characters, props, environment, UI, effects, and audio must belong to the same world and design system.

## Visual production loop

`ART_DIRECTION → REFERENCE_STUDY → COMPOSITION/BLOCKOUT → FORM/SILHOUETTE → PRIMARY DESIGN → DETAIL → MATERIALS/TEXTURE → LIGHTING/COLOUR → MOTION/ANIMATION → CONTEXT INTEGRATION → CRITIQUE → REFINEMENT → FINAL REVIEW`.

The loop is not a fixed linear tool chain. It is a quality process with backtracking. A defect in silhouette is solved at the silhouette stage, not hidden with texture detail. A bad composition is not repaired by adding particles. A poor model is not repaired by cinematic lighting.

## Visual review rubric

Each relevant factor is scored against a task-specific rubric with examples of pass/fail:

- **Intent and concept:** recognizable, original, and appropriate to the brief.
- **Composition and hierarchy:** focal point, balance, flow, negative space, readability.
- **Silhouette and shape language:** strong form at target scale; clean hierarchy; no accidental tangencies.
- **Proportion and anatomy:** plausible or intentionally stylized; consistent landmarks and articulation.
- **Topology and construction:** suitable edge flow, manifoldness where required, sane normals, no hidden geometry artifacts.
- **Surface and material:** physically plausible or intentionally stylized response; consistent roughness/metalness/normal detail; no texture stretching or seams.
- **Lighting and color:** motivated light, readable values, palette harmony, controlled contrast, atmosphere.
- **Typography and layout:** hierarchy, legibility, spacing, optical alignment, consistent font use and licensing.
- **Animation and motion:** timing, weight, anticipation, follow-through, arcs, contact, loop continuity, no visible popping.
- **Effects:** scale, timing, layering, readability, controlled noise and overdraw.
- **Integration:** correct scale, pivots, collision, mipmaps, UI scale, color management, and target pipeline.
- **Polish:** no conspicuous seams, clipping, visual noise, aliasing, broken shadows, placeholder detail, inconsistent quality, or accidental artifacts.

A numeric score is only a summary. Every failed criterion needs a concrete defect description and evidence. Artistic approval should include a qualified human reviewer for high-impact or subjective deliverables until the automated reviewer is calibrated and proven.

## Anti-patterns that fail the visual moat

- Primitive mesh, flat colored capsule, default cube, generic low-poly stand-in, or SVG/canvas drawing presented as final art.
- One unedited text-to-image output used as a finished character, environment, UI, or brand identity when structure and continuity are required.
- Unmotivated bloom, excessive particles, random detail, noisy materials, indiscriminate outlines, or generic sci-fi gloss used to disguise weak design.
- Inconsistent style across assets, mismatched scale, missing contact shadows, incorrect lighting, poor value hierarchy, default fonts, and unfinished UI.
- A beautiful hero render whose model cannot deform, whose asset does not import, whose scene cannot run, or whose camera framing hides defects.

## Visual moat proof

Every approved asset should have, where appropriate: source project, production export, context render, close-up detail render, wireframe/topology view, material/UV/texture inspection, animation/contact-sheet review, import/runtime capture, performance information, and provenance. The required evidence is defined per artifact class in the quality system.
