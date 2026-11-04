# Executable Runtime Foundation (v0.2.0)

## Purpose

The runtime is the persistent local control plane around Freebuff. It is deliberately smaller than Freebuff's reasoning system and deliberately does not own proprietary model intelligence. It supplies concrete, inspectable mechanisms for capability declaration, tool invocation, job/task durability, path boundaries, approval enforcement, artifact identity, machine inventory and MCP interoperability.

## Runtime modules

| Module | Executable responsibility | Current boundary |
|---|---|---|
| `config.py` | TOML config, data paths, safe defaults | Local config only; no secrets stored |
| `db.py` | SQLite schema and event persistence | Schema version guard v1, integrity check and online backup; migration framework/restore drills remain P0 |
| `registry.py` | Load and validate capability declarations | JSON runtime catalog; no remote discovery yet |
| `policy.py` | Default-deny side-effect policy and approval binding | CLI grants only; approval UX/audit hardening remains P0 |
| `jobs.py` | DAG validation, topological execution, task states/checkpoints and human reconciliation | Sequential runner; per-job lock; crashed/uncertain tasks quarantine as `NEEDS_RECONCILIATION`; human CLI may retry after read-back or mark success with explicit outputs/evidence; no parallel scheduler or cancellation |
| `artifacts.py` | Hash, metadata and verify files | Hash integrity only; semantic/format validators are adapter-specific |
| `resources.py` | OS/CPU/RAM/disk/GPU inventory and conservative admission | `psutil` optional; resource reservation/telemetry not yet implemented |
| `service.py` | Capability dispatch and adapter composition | Only listed runtime capabilities have handlers |
| `mcp/server.py`, `mcp/sdk_server.py` | Minimal compatibility harness plus official MCP SDK v2 tool/resource server | Production bootstrap installs official SDK v2; the SDK path is preferred; no public network transport is enabled by the default CLI |
| `adapters/comfyui.py` | Native ComfyUI HTTP requests | Health, queue, submit, history, node/model inventory and bounded output download; no WebSocket streaming, workflow validation or visual QA yet |
| `adapters/process.py` | argv-only bounded process launch | No shell; specific launch wrappers and approvals required |
| `agent/provider.py` | Optional OpenAI-compatible local endpoint | Thin chat client, not a full agent or routing policy |

## State model

SQLite records jobs, tasks, events, artifacts and approval requests. Job and task states are never inferred from LLM language. Task output JSON and error JSON are retained. The executor processes a DAG in deterministic topological order. A blocked task can be rerun after a human issues an exact approval and the approval ID is passed to the job runner; failed and successful jobs are terminal in this release. On worker restart, any task still marked `RUNNING` is quarantined as `NEEDS_RECONCILIATION`. The runtime never assumes whether an external side effect happened. The interactive CLI exposes a human-only reconciliation command; Freebuff cannot call it via MCP.

### Deliberate limitations
- No concurrent task execution. This avoids write races until per-project/app locks and reservations are implemented.
- No durable worker service. A process crash that leaves a task marked `RUNNING` is detected on the next run and quarantined as `NEEDS_RECONCILIATION`; the runtime never blindly replays it. `studio job reconcile` is CLI-only and requires interactive confirmation, a named reviewer and evidence. `retry` is only valid after checking that the external effect did not occur or was safely rolled back. `mark_succeeded` requires explicit outputs JSON and read-back evidence.
- Per-job cross-process locks prevent two workers from executing the same job simultaneously. There are not yet per-project/application/artifact locks across different jobs.
- No task cancellation API or application-specific compensation protocol yet.
- SQLite schema v1 is version guarded, with safe rejection of a newer database. Integrity-check and online backup are implemented; future schema migrations and automated backup restore drills remain P0.
- JSONL rotating logs are written under the Studio home. Redaction is a best-effort safeguard, not a substitute for avoiding sensitive payloads in logs.
- One approval ID is injected per `job run`; a workflow containing multiple different approvals should be split into staged jobs or pass task-specific approval IDs in task inputs.
- The maintained MCP SDK v2 is an optional extra for the zero-dependency core but is installed by the production bootstrap. The built-in hand-written server is only a legacy developer fallback and is not the certification target.
- The resource guard is conservative admission logic, not a global reservation service. It cannot guarantee that another process will not consume VRAM after the check.

These limitations are explicit P0/P1 implementation work, not hidden features.

## Running an end-to-end smoke job

From the repository root after installation:

```powershell
studio init
studio job create examples/workflows/foundation-smoke.json
# Copy the returned job ID
studio job run <job-id>
studio job status <job-id>
studio quality report <job-id>
# To resolve a crash-quarantined task, first inspect the real target application and evidence.
# Then choose exactly one human-reviewed resolution:
studio job reconcile <job-id> <task-id> --action retry --reviewer "operator" --evidence "Confirmed the external action did not occur or was safely rolled back."
# OR, only after read-back verification, provide a JSON outputs object:
studio job reconcile <job-id> <task-id> --action mark_succeeded --reviewer "operator" --evidence "Read back the target state and compared it to the intended result." --outputs-json .\reconciled-outputs.json
```

The expected deterministic state is two tasks `SUCCEEDED`, one registered text artifact whose SHA-256 verifies, and a quality result of `PASS_PENDING_REVIEW`. It is intentionally not `CERTIFIED`: a generated text file has no visual/audio or commercial craft review.

## Human review and rights ledger

Artifacts are assigned an explicit `unknown` rights state by default. A human operator can record evidence-backed license/validation decisions:

```powershell
studio artifacts review <artifact-id> --reviewer "reviewer-id" --license-status cleared --license-identifier "license or ownership basis" --license-source-url "https://..." --validation-status PASS --notes "Describe exactly what was inspected and why it passes."
studio quality review <job-id> --type technical --verdict PASS --reviewer "qa-reviewer" --rationale "List tests and observations."
studio quality review <job-id> --type creative --verdict PASS --reviewer "art-director" --rationale "Describe craft review and context."
studio quality report <job-id>
```

The CLI review commands are intentionally not exposed as Freebuff MCP tools. An agent may prepare evidence, but it cannot mark its own subjective review or rights clearance as human-approved. A `PASS_ALL_CHECKS` job report is still not adapter or release certification.

## Backups and operational diagnostics

```powershell
studio database integrity-check
studio database backup
studio job list
studio approvals list --status PENDING
```

Backups are local SQLite online backups with an integrity check and SHA-256. Store copies on a separately protected location according to the workstation backup policy. A successful local backup command does not prove that a restore drill has passed.
