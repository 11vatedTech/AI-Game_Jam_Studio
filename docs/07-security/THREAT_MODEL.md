# Threat Model

## Security objectives

Protect user projects, credentials, local applications, machine resources, source code, generated assets, and release channels while still enabling useful automation. Every agent/tool operation is potentially influenced by untrusted prompts, files, model outputs, plugins, external pages, dependencies, and generated code.

## Trust boundaries

- User ↔ agent interface.
- Agent/model ↔ tool protocol/gateway.
- Gateway ↔ application adapters.
- Adapter ↔ creative application/editor process.
- Local studio ↔ network/remote services.
- Workspace ↔ filesystem outside workspace.
- Runtime ↔ plugins/custom nodes/extensions.
- Project assets ↔ untrusted imported content.
- Build/release environment ↔ external distribution services.

## Threat categories

- Prompt injection in project files, web pages, documentation, images, node graphs, comments, metadata or tool outputs.
- Excessive agency: agent can delete files, execute arbitrary code, publish externally or spend money without a proper gate.
- Insecure tool/plugin supply chain, malicious install hooks, dependency confusion and compromised maintainers.
- Path traversal, symlink escape, archive extraction attacks and arbitrary filesystem access.
- Unauthenticated network listeners, remote MCP endpoints, weak tokens, exposed localhost services.
- Credential/secret leakage in logs, prompts, screenshots, repositories or generated reports.
- Malformed or adversarial media files, parser exploits, oversized assets and decompression bombs.
- Tool schema confusion, unsafe dynamic method invocation and code injection.
- Model denial of service, resource exhaustion, VRAM/RAM pressure and runaway workflows.
- IP/license violations, unlicensed training data/assets/fonts/samples, and prohibited redistribution.
- Cross-project data leakage, stale context, artifact substitution and provenance forgery.

## Mandatory controls

- Least privilege and per-capability permission grants.
- Project-scoped workspace roots and canonical path verification.
- No secret access unless explicitly required and approved; redact logs.
- Loopback-only defaults for local services; authenticated transport for remote use.
- Network allowlists and user approval for external data transfer.
- Plugin/custom node quarantine and dependency scanning.
- Schema validation, typed inputs, bounded payloads and output validation.
- Sandboxed subprocesses where feasible; CPU/memory/time/file/network limits.
- Prompt-injection defense: treat all external content as data, not authority; enforce policies outside model context.
- Audit log for actions and approvals.
- Approval gate for delete/publish/credential/network/payment/irreversible operations.
- Reproducible and pinned dependency installation.
- Automated secret, dependency, malware and license scans.
- Backups and rollback before destructive or broad edits.

## Abuse-case testing

Test malicious instructions embedded in project documentation, images metadata, node graph labels, imported code, web content and generated output. Verify the agent refuses privilege escalation, out-of-workspace writes, credential disclosure, unapproved publishing, and disabled safety checks. Test adapter behavior when an application or external tool returns adversarial tool output.
