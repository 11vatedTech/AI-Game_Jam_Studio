# Models, Inference, and Resource Runtime

## Model strategy

Use model capabilities as replaceable services. The studio must not bind a discipline adapter to a single LLM or model provider. Maintain profiles for text/reasoning, code, vision, image generation/editing, 3D, speech, audio, video, embedding/reranking, and evaluation models.

## Candidate local stack

- **llama.cpp:** lightweight GGUF inference and server; evaluate quantization, context, tool calling, and Windows CUDA builds.
- **Ollama:** convenient local model lifecycle/API; compare overhead, model packaging, and control.
- **PyTorch + Diffusers:** flexible model development and inference; evaluate CUDA wheel compatibility and memory.
- **ComfyUI:** node-graph image/media workflow runtime; integrate by its HTTP API and WebSocket events; use pinned workflow graphs and custom-node allowlists.
- **TensorRT:** optional NVIDIA optimization path where supported model/operator export justifies the engineering cost.
- **vLLM/SGLang:** investigate for server-grade batching and throughput if hardware/OS support and resource budget justify them; not default on a constrained Windows laptop.

## Hardware admission control

At runtime inspect: GPU model/driver/CUDA support, available VRAM, shared GPU memory, RAM, CPU, disk free, application process memory, model residency, and active jobs. Maintain a conservative safety reserve. Never trust model-card minimum VRAM as actual concurrent workload capacity.

Use execution tiers:

1. **Interactive:** small context/small models, fast feedback.
2. **Sequential heavy:** load one major model at a time, unload before next stage.
3. **Offload/tiled:** CPU offload, tiled VAE/attention, lower resolution or batch one when valid.
4. **CPU fallback:** slower path for suitable tasks only.
5. **Optional external:** paid/cloud execution only when user authorized and policy permits.

## Model registry metadata

Model family, exact ID/revision, source, file hashes, format, quantization, precision, license, commercial/re-distribution restrictions, input/output modalities, context/resolution, required runtime, VRAM/RAM/disk estimate, speed measurements, quality benchmark, known limitations, safety constraints, and approval status.

## Model evaluation

Evaluate per task. For coding: compile/test correctness, tool-use safety, defect rate, token/time cost. For image: prompt adherence, composition, fine detail, typography, identity consistency, editing controllability, resolution, artifact rate, and license. For 3D: topology, geometry completeness, UV/material quality, editability, riggability, and engine integration. For audio/video: intelligibility, temporal coherence, artifacts, control, loudness/color, and export validity. Use blind comparisons where subjective evaluation matters.
