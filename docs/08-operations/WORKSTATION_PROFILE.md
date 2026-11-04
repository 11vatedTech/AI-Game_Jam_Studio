# Workstation and Resource Profile

## Baseline hypothesis

Prior user-provided machine reports indicate a Windows 11 workstation, Intel Core Ultra 9 275HX, 32 GB RAM, NVIDIA RTX 5070 Ti Laptop GPU with approximately 12 GB VRAM, and around 1 TB SSD. Historical software reports include Blender 5.2, Unreal Engine 5.8, ComfyUI 0.42.x, Python 3.12, and Godot 4.x. These are not current verified facts; Freebuff must run inventory and health checks before making dependency or performance decisions.

## Inventory procedure

Capture OS/build; CPU/core topology; physical/available RAM; GPU model, driver, CUDA support and VRAM; disk volume/free space; Python environments; compilers/SDKs; Git; CMake/Ninja; Blender; Unreal; Unity; Godot; ComfyUI; audio/video tools; model servers; ports/processes; versions; and actual health endpoints.

Store report timestamp, commands, output, and redacted environment details in local diagnostics. Never store credentials.

## Resource policy

- 12 GB VRAM is a constrained shared resource; never assume multiple heavyweight models fit concurrently.
- Reserve VRAM and RAM safety margins for the OS, desktop, editor and driver.
- Run heavy generation/model jobs sequentially by default until measurements support concurrency.
- Prefer model unloads, batch size one, tiled processing, lower precision/quantization, CPU offload and resolution scaling where quality remains acceptable.
- Schedule Blender render, Unreal shader compilation, ComfyUI inference, local LLM and video encoding to avoid peak contention.
- Check storage before model downloads, caches, derived renders and project duplication.
- Do not kill user processes or purge caches without approval.

## Environment separation

Use per-project virtual environments or containerized/quarantined runtimes where viable. Keep ComfyUI custom nodes and experimental models isolated from stable production. Use documented environment variables and lock files; avoid modifying global Python installations unnecessarily.

## Capability support matrix

Each capability declares minimum/validated RAM/VRAM, GPU/runtime, CPU/thread, disk, and application version. If the host is below minimum, mark `UNSUPPORTED` or choose a tested degraded path; don't silently downgrade quality.
