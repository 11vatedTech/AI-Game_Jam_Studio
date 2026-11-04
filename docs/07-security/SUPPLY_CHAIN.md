# Software and Model Supply Chain

## Threat-aware acquisition

- Prefer official repositories/releases and verified package registries.
- Pin commits/tags and dependency lockfiles. Avoid branch-head dependencies for production.
- Review install scripts, post-install hooks, binary downloads, dependency source, license, network calls and file writes.
- Run scanners and test in an isolated environment with minimal permissions.
- Generate software bill of materials (SBOM) for distributable builds.
- Track vulnerabilities and upgrade impact.
- Validate checksums/signatures where provided.
- Promote tested packages from quarantine to approved environment; preserve exact artifact hashes.

## ComfyUI custom-node control

Custom nodes can execute Python and install dependencies. Treat them as code, not harmless graph presets. Use a separate clone/environment, inspect repository and install scripts, constrain network and filesystem access, pin revisions, run tests, then approve and record the node. Do not mass-install node packs into the main ComfyUI installation without review.

## Model and dataset acquisition

Record source, license, file hash, format, quantization, size, intended runtime, safety policy, and compatibility. Check free disk and VRAM/RAM plan before downloading. Avoid untrusted pickle/model formats where safer alternatives exist. Do not load model code or remote custom code without review.

## Update strategy

Use a staged update channel: candidate → sandbox tests → project regression → promoted → rollback available. Upgrades require change notes and support matrix updates.
