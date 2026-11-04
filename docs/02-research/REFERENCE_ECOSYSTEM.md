# Reference Ecosystem and Candidate Shortlist

This is a discovery and evaluation catalog, not a declaration that all projects are compatible, maintained, secure, licensed for our use, or production ready. Exact candidate versions and license metadata must be recorded during inspection.

## Unified agent/application integration

| Candidate | Domain/value | Integration surface | Position |
|---|---|---|---|
| AI Game Dev | Engine editor automation, desktop/CLI, extensions | Engine plugins, MCP, CLI | Benchmark deeply; adopt selectively |
| DCC-MCP Core | Broad creative-application control plane, Skills, gateway | MCP, REST, Rust/Python adapters | Priority-1 evaluation candidate |
| BlenderMCP and other Blender bridges | Blender scene/model operations | Blender Python/socket/MCP | Compare against `bpy` native workflows and DCC-MCP adapter |
| Unity-MCP | Unity editor operations | C# plugin, .NET server, MCP | Benchmark engine-specific depth |
| Godot-MCP | Godot scenes, scripts, resources, editor operations | C# addon/MCP/RQL | Benchmark typed operations and undoability |
| UnrealMCP community bridges | Unreal editor/Blueprint/material/VFX operations | Python/plugin/MCP | Audit command coverage and UE version support |

## Core creative applications

| Discipline | Candidates | Best interface to investigate | Notes |
|---|---|---|---|
| 3D, animation, rendering | Blender; optional Maya, Houdini, 3ds Max, Cinema 4D, ZBrush | Python API, command line, native plugin, USD/FBX/glTF | Blender is first local-first target; proprietary products are optional professional alternatives |
| Game engines | Unreal Engine, Unity, Godot; assess O3DE/Stride/Bevy/Flax for future scope | Native editor/plugin API, commandlet, CLI, MCP | Prioritize installed engines, then benchmark by project need |
| CAD/mechanical | FreeCAD, OpenSCAD; optional Fusion, SolidWorks, Onshape | Python/CLI, feature tree, STEP/IGES/3MF | Validate parametric history and neutral-format fidelity |
| 2D illustration | Krita, GIMP, Inkscape; optional Photoshop/Illustrator, Clip Studio | Python/plugin/CLI, layered formats, SVG/PDF | Preserve editable source layers and color profile |
| Pixel/sprite art | Pixelorama, Aseprite (commercial), LibreSprite, Piskel | Native scripting/export, spritesheets, Aseprite file | License/feature and automation comparisons required |
| Block/voxel modeling | Blockbench, MagicaVoxel | Native project formats and exporters | Specialized style domains |
| Texturing/material | Material Maker, MaterialX tool ecosystem, Blender nodes; optional Substance 3D | Graph API, procedural graph, texture baking | Verify engine shader parity and texture channel packing |
| Image synthesis | ComfyUI, Diffusers/PyTorch pipelines, Krita AI workflows where supported | ComfyUI HTTP/WebSocket, Python SDK, native extensions | Workflow API and custom-node supply-chain review required |
| Video/editing/compositing | Kdenlive, Blender VSE, Natron, FFmpeg; optional DaVinci Resolve, Premiere, After Effects | CLI, scripting/plugin, OTIO, frame sequences | Separate editorial metadata from media assets |
| Audio/music | Audacity, Ardour, REAPER (commercial), SuperCollider, LMMS, MuseScore | CLI, plugin APIs, OSC/MIDI, session interchange | Test reproducibility and licensing of samples/virtual instruments |
| Game audio | Wwise/FMOD (commercial) and engine audio systems | SDK, plugin, project files | Optional professional middleware; evaluate redistribution/licensing |
| UI/product design | Penpot, Figma (hosted), Inkscape, web component/design systems | REST/plugin, tokens, export, design files | Treat hosted features and API limits as optional |
| Narrative | Ink, Yarn Spinner, Twine, Ren'Py | DSL, source project, runtime integration | Validate branching, localization, state, and test coverage |
| Level design | LDtk, Tiled, engine-native editors | CLI/export, JSON/project files, plugins | Keep world/level source editable |
| Screen capture/streaming | OBS Studio | WebSocket, plugins, CLI | Useful capture and evidence adapter |

## Software and orchestration infrastructure

| Candidate | Purpose | Evaluation point |
|---|---|---|
| LangGraph | Stateful agent/workflow graph | Persistence, human approval, debugging, loops, provider flexibility |
| Temporal | Durable long-running workflow execution | Crash recovery, retries, timers, versioning, operational overhead |
| Microsoft Agent Framework | Agent orchestration and tools | .NET/Python fit, ecosystem maturity, provider and workflow boundaries |
| CrewAI | Role/task-oriented multi-agent orchestration | Evaluate coordination overhead and observable execution |
| LlamaIndex Workflows | Event-driven workflow abstraction | Retrieval/data-heavy workflow fit |
| OpenAI Agents SDK | Agent handoffs, tools, tracing | Provider-specific coupling vs portable interface requirements |
| llama.cpp | Local model inference/runtime/server | GGUF model compatibility, quantization, throughput, VRAM/RAM |
| Ollama | Local model packaging/API | Developer ergonomics, model management, performance control |
| ComfyUI | Node-graph AI media workflows | Local queue, API, workflow versioning, custom-node safety |
| PyTorch/Diffusers | Model development and inference pipelines | Fine-grained control, CUDA compatibility, memory orchestration |
| TensorRT | NVIDIA optimized inference | Export/compatibility effort vs speed gains |
| OpenTelemetry | Traces/metrics/log correlation | Cross-process correlation and local privacy |
| Git LFS/annex/DVC or artifact stores | Large files and data lineage | Avoid storing model weights/generated binaries in normal Git |

## Candidate maturity rule

Every catalog record must eventually include: official URL, exact revision, license, maintainer status, tests, issue health, support matrix, integration mechanism, known security issues, local/offline behavior, quality ceiling, and the last reproduction result. Until then, the record is `L0` or `L1`, not certified.
