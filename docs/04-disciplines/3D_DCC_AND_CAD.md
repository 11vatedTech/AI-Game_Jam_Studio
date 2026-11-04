# 3D DCC, Modeling, CAD, and Spatial Design

## Creative 3D

Support hard-surface, organic, stylized, realistic, modular environment, prop, character, creature, vehicle, architecture, set-dressing, sculpt, retopology, UV, baking, look-dev, rig, animation, simulation, lighting, scene assembly, and rendering.

## Candidate tools

Blender is the first open/local DCC candidate. Evaluate Blockbench, FreeCAD, OpenSCAD and specialized applications by use case. Optional professional products include Maya, Houdini, ZBrush, 3ds Max, Cinema 4D, Substance 3D, Rhino, Fusion, SolidWorks, and Onshape. Do not assume these share a license model or offline/API capabilities.

## 3D asset quality contract

- Correct scale, coordinate system, object origins, naming, transforms and hierarchy.
- Appropriate geometry density and edge flow for deformation/use case.
- Valid normals, no unintended non-manifold geometry, self-intersections or duplicate internal surfaces where disallowed.
- Topology supports required deformation and silhouette at target camera distance.
- UVs are appropriate, non-overlapping where required, and correctly packed for intended bake/use.
- Materials and textures use correct color/data spaces, channel packing, resolution and compression.
- LODs, collision, pivots, sockets, physics setup, and metadata exist where needed.
- Native source remains editable; export settings and final output are reproducible.

## CAD and industrial design

For parametric tasks, preserve feature history, constraints, dimensions, units, tolerances, assemblies, and drawings. Validate watertightness, wall thickness, clearances, manufacturability, material/process assumptions, and export to STEP/IGES/3MF/STL according to destination. Never treat a visual mesh as a valid parametric engineering model unless that is the explicit brief.

## Cross-app pipeline

Concept → blocking → primary forms → topology/feature structure → UV or parameter validation → materials → rig/assembly → native-app review → interchange export → destination import → context capture → final inspection. Each conversion records lost features and tests them.
