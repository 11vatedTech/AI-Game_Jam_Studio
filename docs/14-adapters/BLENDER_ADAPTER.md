# Blender Adapter — Native Python and Background Execution

## Implemented now
- Blender executable detection through configured executable name/path.
- Version output.
- Approval-gated background execution of an existing Python script located inside the managed workspace.
- Captured process return code, stdout/stderr and hashed evidence JSON.

## Trust boundary
A Blender Python script runs with the current OS user's privileges and can access files/network. The current wrapper is not a sandbox. Human approval is mandatory. Do not use this operation on unknown scripts or project files. For untrusted plugins/assets, use a separate OS account or isolated VM.

## Required next adapter layer
Build a typed semantic operation library over `bpy` rather than making unrestricted generated scripts the default. Operations should cover scene/object inspection, collections, transforms, mesh data, modifiers, materials/nodes, UV layers, cameras/lights, actions/NLA, armatures, constraints, geometry nodes, render settings, file save/reopen, export and validation. Group writes into undoable/transactional phases where possible.

For each operation, perform read-before-write preconditions and read-after-write postconditions. Capture Blender version, Python version, add-ons, render engine, color management, unit scale, axis conventions and dependency state. Produce editable `.blend`, target exports (for example glTF/USD/FBX only where appropriate), rendered context views, structural inspection and import/runtime verification.

Never approve a model only from a beauty render. Check silhouette, scale, topology, normals, manifoldness as needed, UV distortion, texel density, material graph, texture paths, rig weights, bone naming/orientation, animation contacts and target-engine behavior.
