# Runtime Security and Trust Boundaries

## Trust zones

1. **Agent intent zone:** Freebuff and other agents are untrusted requesters. Their tool arguments, generated scripts and paths are untrusted input.
2. **Studio control zone:** capability registry, policy engine, job database and artifact records enforce declared contracts. Do not let prompt text change policy.
3. **Managed workspace:** local generated project files under the configured workspace. All file operations resolve relative to this root and reject traversal/symlink escape.
4. **External applications:** Blender, Godot, ComfyUI, engines, DCC hosts and custom nodes execute third-party or user code with application-specific privilege. They are not assumed sandboxed.
5. **External/network zone:** remote model endpoints, downloads, registries, publishing and cloud services require distinct network/credential/publish authorization.

## Implemented controls
- Default-deny policy configuration.
- Exact matching of approval scope, side-effect class and target.
- Blocked scopes for arbitrary shell, unrestricted filesystem and secret export.
- Workspace-relative path checks and existing-ancestor symlink checks.
- No-overwrite file creation using exclusive create semantics.
- SHA-256 artifact verification and manifests that default license/provenance state to `unknown`.
- Per-job cross-process locks; argv-only subprocess launch that streams output to bounded temporary files.
- ComfyUI adapter rejects non-loopback hosts in this release.
- Human review/rights-clearance commands are CLI-only; approval decisions are pending-only, expiring and exact-target bound.
- argv-only subprocess launch with `shell=False`, bounded timeout and managed-workspace working directory.
- Human approval requirements for `EXECUTE`, `MODIFY`, `DELETE`, `NETWORK`, `CREDENTIAL` and `PUBLISH` by default.

## Critical residual risks
- Blender Python scripts and Godot editor/project code can execute arbitrary code with the user's OS permissions. Approval is necessary but is not a sandbox.
- ComfyUI custom nodes/workflows may invoke arbitrary Python or network behavior. Review workflow nodes and custom-node provenance before execution.
- A local process may be compromised by a malicious plugin or workflow. Use separate OS accounts/VMs/containers for untrusted assets where feasible.
- Per-job locking exists, but cross-job application/project locks, approval database tamper protection, signed audit evidence and encrypted backups require further hardening.
- ComfyUI adapter currently rejects non-loopback hosts. Remote ComfyUI is deliberately unsupported until TLS/authentication, host allowlists, explicit remote-network approval and security tests are implemented.

## Agent host containment

The runtime cannot stop an agent that already has unrestricted OS shell/filesystem permissions from bypassing the MCP policy and changing files directly. Run Freebuff and MCP tools under a standard, non-administrator OS account. Restrict filesystem access with OS ACLs to the repository, dedicated workspace and explicitly approved applications. Keep secrets outside the agent-readable workspace. Do not grant broad PowerShell, terminal or process-launch access when a typed MCP operation exists.

## Mandatory controls before commercial deployment
- Bind ComfyUI inspect/queue operations to loopback by default; require TLS/auth/allowlist and network approval for remote hosts.
- Add sandbox/container/VM execution for arbitrary scripts and custom nodes.
- Add secrets manager integration; never place tokens in TOML, JSON, MCP arguments, task inputs or logs.
- Add dependency lockfiles, SBOM, hash verification, signature checks, vulnerability scan and provenance attestation.
- Add database backup/restore, schema migrations, audit-log tamper evidence and retention controls.
- Add permission fuzzing, path traversal/symlink tests, malformed MCP messages, denial tests and threat-model review.
