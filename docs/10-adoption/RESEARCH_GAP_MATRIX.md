# Research Gap Matrix

| Area | Known candidates | Research still required | Evidence to close gap |
|---|---|---|---|
| AI Game Dev | Official platform, engine plugins, extension ecosystem | Deep code audit, reproducibility, feature boundaries, cloud/paid features | Pinned source, license, test results, matched task benchmark |
| DCC-MCP Core | Broad MCP/REST control plane and Skills | Adapter maturity by app, Windows support, permissions, multi-instance, rollback | Installed conformance suite and source audit |
| Unreal | Native Python/C++/Blueprint, community MCP | Current UE support, thread safety, Blueprint automation, performance | Real project editor/runtime tests |
| Unity | Editor API, Test Framework, Unity-MCP | License/terms, current version, API depth, CI support | Reproduction and build/test benchmarks |
| Godot | EditorPlugin, GDScript/C#, Godot-MCP | Current stable compatibility, scene/resource editing depth | Native project test and packaged runtime |
| Blender | `bpy`, BlenderMCP, DCC-MCP | Native API coverage, job lifecycle, headless limitations, security | Model/rig/material/render/export pipeline |
| ComfyUI | Native HTTP/WS and custom nodes | Workflow schema/versioning, node security, output metadata, cancellation | Pinned workflow run plus artifact verification |
| 2D tools | Krita, GIMP, Inkscape, Pixelorama | Script/automation quality, layered round-trip, license | Editable source and production asset tests |
| Audio | Audacity, Ardour, SuperCollider, LMMS, Wwise/FMOD | Session scripting, plugin/sample licenses, middleware integration | Deliverable package and in-engine playback review |
| Video | Kdenlive, Blender VSE, Resolve/Premiere, FFmpeg, OTIO | Native automation and timeline interchange parity | Render, timeline round-trip and delivery QC |
| CAD | FreeCAD, OpenSCAD and proprietary CAD | Parametric operation automation, feature history, interchange | STEP/3MF and dimension/tolerance tests |
| Workflow engine | LangGraph, Temporal, competitors | Crash recovery, persistence, state versioning, simplicity | Fault-injection benchmark |
| Local inference | llama.cpp, Ollama, PyTorch, TensorRT | Windows/GPU compatibility, model quality and memory | Per-task benchmark and resource trace |
| Visual QA | OpenCV, image diff, vision models, human review | Calibration and defect taxonomy | Annotated golden dataset and reviewer agreement |
| Security | OWASP/NIST practices, package tools | Adapter-specific attack surface | Threat tests and audit logs |
| License/IP | OSS and model/asset terms | Commercial use and redistribution for exact assets | Bill of materials and review sign-off |
