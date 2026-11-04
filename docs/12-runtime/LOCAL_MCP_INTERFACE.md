# Local MCP Interface for Freebuff

## Production transport and protocol

The production bootstrap installs the official Model Context Protocol Python SDK v2 (`mcp>=2,<3`) and the Studio server delegates framing, schema validation, discovery, protocol version negotiation and stdio lifecycle to that upstream SDK. The SDK v2 supports the current MCP protocol revision `2026-07-28` and legacy `2025-11-25` clients. The local transport is stdio: Freebuff launches the child process and exchanges messages through stdin/stdout. No network listener is opened by this integration.

```powershell
$env:STUDIO_HOME = "$env:LOCALAPPDATA\11vatedTech\AI-Game-Jam-Studio"
.\.venv\Scripts\studio.exe mcp serve
```

**Do not print to stdout from the MCP process.** stdout belongs to the protocol. Use the runtime JSONL logger or stderr for diagnostics. The repository retains a tiny legacy JSON-RPC harness for isolated compatibility development only. The production command fails closed if the official SDK is missing. A developer can opt into the legacy harness only by setting `STUDIO_ALLOW_LEGACY_MCP=1`; never use that fallback for Freebuff production integration or certification.

Primary references (checked 2026-11-04):
- Official protocol release: <https://github.com/modelcontextprotocol/modelcontextprotocol/releases/tag/2026-07-28>
- Official protocol versioning: <https://modelcontextprotocol.io/specification/2026-07-28/basic/versioning>
- Official Python SDK v2: <https://github.com/modelcontextprotocol/python-sdk>
- Python SDK v2 run / stdio documentation: <https://github.com/modelcontextprotocol/python-sdk/blob/main/docs/run/index.md>

## Tool catalog

| Tool | Purpose | Permission posture |
|---|---|---|
| `studio_status` | Runtime identity and data-root status | Read |
| `capabilities_list` | Runtime capability catalog and maturity | Read |
| `capability_invoke` | Invoke one registered operation | Every operation re-authorizes against local policy |
| `resource_profile` | Live host/GPU inventory | Read |
| `job_create`, `job_run`, `job_status`, `job_list` | Durable task graph management | Each task re-authorizes |
| `workspace_read_text`, `workspace_write_text` | Bounded workspace text access | Confined; writes are create-only |
| `artifacts_list`, `artifact_verify` | Artifact lineage and integrity | Read |
| `quality_report` | Deterministic gates and review status | Read/report generation |
| `approval_request`, `approvals_list` | Request/inspect human approvals | Cannot approve or reject |

The agent cannot approve its own requested operation through MCP. Human approval is granted through the local CLI:

```powershell
studio approvals decide <approval-id> --approve --approver "human-operator"
# Type: APPROVE <last-six-characters-of-id>
```

A human must inspect the exact scope, side-effect and target. The job resumes with the approved ID:

```powershell
studio job run <job-id> --approval-id <approval-id>
```

## Freebuff setup

Use `scripts/windows/mcp-config.example.json` as the generic host configuration shape. Replace all paths with the actual absolute paths to this checkout and its `.venv`. Confirm Freebuff's actual configuration format and reload behavior from the locally installed version; do not assume the generic JSON key shape is accepted unchanged.

The production connection test must establish:
1. The configured command launches the intended repository and virtual environment.
2. The official SDK answers `server/discover` for a 2026-era client and supports the legacy handshake for older clients.
3. `tools/list` returns the runtime tool catalog with valid schemas.
4. `studio_status` and `capabilities_list` match the local runtime.
5. A controlled smoke workflow completes and its artifact hash verifies.
6. A high-risk operation is blocked until a human approves its exact scope/target; the agent cannot approve it.
7. MCP process stdout contains only protocol traffic and the process exits cleanly when its host closes stdin.

## External specialist MCP servers

Attach DCC-MCP Core, AI Game Dev engine plugins and other professional servers as separate MCP connections in Freebuff where practical. The Studio runtime owns cross-server orchestration, durable tasks, artifact lineage and acceptance evidence; specialist servers own their native application operations. Record the exact server version, command, dependencies, host permissions and tools snapshot. Do not proxy or reimplement a proven specialist server without a measured reason.
