# Materials, Look Development, Lighting, and Rendering

## Required capabilities

Procedural and hand-authored materials; PBR; stylized shading; layered surfaces; texture generation; masks; baking; shaders; node graphs; lighting; camera; color management; render setup; denoising; render farms; LOD/material optimization; and cross-renderer validation.

## Tool ecosystem

Investigate Blender node systems, Material Maker, MaterialX, OpenPBR, Substance 3D Designer/Painter (optional proprietary), engine material editors, Houdini procedural materials, and renderer-specific systems. Do not assume identical node semantics or output across renderers.

## Material acceptance

- Material response matches art direction under representative lighting.
- Correct roughness/metalness/specular/normal/height behavior; no inappropriate color-space conversion.
- Texture texel density and resolution are appropriate for screen coverage and platform budgets.
- UV seams, stretching, tiling, mip behavior and compression are reviewed in target context.
- Shader compile and runtime cost meet target.
- Material source graph, dependencies, maps, channel semantics and conversion settings are preserved.

## Lighting and rendering acceptance

Check key/fill/rim or motivated source logic, exposure, contrast, shadow quality, contact grounding, indirect light, volumetrics, reflections, flicker, noise, temporal artifacts, color transforms, framing and focal hierarchy. Capture both intended final render and diagnostic views. Maintain renderer/version/settings snapshots for reproducibility.
