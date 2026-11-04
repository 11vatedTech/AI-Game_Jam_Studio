# Godot Adapter — Editor/Headless Pipeline

## Implemented now
- Configured executable detection and `--version`.
- Approval-gated headless editor import/parse invocation on a project directory inside the managed workspace.
- Captured exit code, stdout/stderr and evidence hash.

## What this validation means
`godot --headless --path <project> --editor --quit` can exercise project import/editor initialization. It does not prove gameplay correctness, visual fidelity, package/export correctness or end-user runtime behavior.

## Required next adapter layer
Add a Godot-side tool/plugin or local RPC bridge exposing typed operations for project/scene/resource/script inspection, node creation/configuration, signals, animation, materials, shaders, import settings, asset references, input maps, export presets and build/run. Validate operations with scene read-back.

Add automated runtime launch, deterministic test scenes, scripted interaction, log/error collection, screenshot/video capture, frame-time and memory measurements, packaged build smoke tests and clean-machine launch. Version support must be pinned to exact Godot minor/patch and export template version.
