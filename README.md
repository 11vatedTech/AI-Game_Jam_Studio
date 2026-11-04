# 11vatedTech AI Game Jam Studio

**Universal Creative Intelligence — specification plus executable local runtime foundation**
**Current release:** `0.2.0` · **Status:** Developer Preview foundation, not universal production certification.

> Take incomplete creative or technical intent, research the professional landscape, design a manufacturable outcome, orchestrate the strongest available tools, produce genuine editable deliverables, integrate them into their real application/runtime, critique and repair defects, and prove the outcome with reproducible evidence.

## The governing principle

**Reuse proven excellence. Integrate it deeply. Extend it systematically. Verify every result.** Freebuff is the agent/reasoning coordinator. This repository supplies durable local workflow execution, permissions, capability contracts, artifact lineage, evidence, local application adapters and an MCP interface. Professional applications remain the authoritative production instruments.

## Start here

1. [`FREEBUFF_START_HERE.md`](FREEBUFF_START_HERE.md) — binding implementation and production handoff for Freebuff.
2. [`AGENTS.md`](AGENTS.md) — repository and security rules.
3. [`PROJECT_STATUS.md`](PROJECT_STATUS.md) — verified implementation state and known gaps.
4. [`docs/00-foundation/MASTER_SYSTEM_CONTRACT.md`](docs/00-foundation/MASTER_SYSTEM_CONTRACT.md) — product invariants.
5. [`docs/00-foundation/VISUAL_MOAT.md`](docs/00-foundation/VISUAL_MOAT.md) and [`docs/00-foundation/PRODUCTION_MOAT.md`](docs/00-foundation/PRODUCTION_MOAT.md) — visual and manufacturing expectations.
6. [`docs/12-runtime/RUNTIME_FOUNDATION.md`](docs/12-runtime/RUNTIME_FOUNDATION.md) — what the code actually implements and what remains missing.
7. [`docs/10-adoption/ADOPTION_DECISIONS.md`](docs/10-adoption/ADOPTION_DECISIONS.md) — reuse posture and research shortlist.

## Bootstrap (Windows 11)

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\windows\bootstrap.ps1
studio status
studio doctor
pytest -q
```

The installer creates a project-local Python virtual environment and a local Studio data directory under `%LOCALAPPDATA%\11vatedTech\AI-Game-Jam-Studio` unless `STUDIO_HOME` overrides it.

## Connect Freebuff

The runtime exposes MCP over stdio:

```powershell
studio mcp serve
```

Use [`scripts/windows/mcp-config.example.json`](scripts/windows/mcp-config.example.json) as a template. Replace paths with actual local absolute paths and adapt to the installed Freebuff version's exact MCP configuration format. Verify `server/discover` for 2026-era clients (or `initialize` for legacy clients), `tools/list`, `studio_status` and the smoke workflow before allowing write/execute operations.

## Current executable capabilities

- Local CLI and health/status diagnostics.
- SQLite-backed jobs, tasks, event records, artifacts, approval requests and human reviews; integrity and online backup commands.
- Sequential, dependency-validated workflow DAG execution and task checkpoints, with crash quarantine and evidence-backed human reconciliation (no blind replay).
- Default-deny policy, exact human approval binding and blocked-scope support.
- Managed workspace path confinement and no-overwrite file creation.
- SHA-256 artifact sidecar manifests, explicit unknown-by-default rights state, human rights/technical review and integrity verification.
- CPU/RAM/disk/GPU/VRAM inventory and conservative resource admission helper.
- Local MCP stdio server for Freebuff/other compatible agents.
- ComfyUI API health/queue/prompt/history/node-model inventory, bounded completion polling, output retrieval and SHA-256 artifact provenance.
- Official MCP Python SDK v2 integration (optional `[mcp]` extra) for the current `2026-07-28` protocol and legacy clients; production bootstrap installs it.
- Blender and Godot version probes plus approval-gated script/headless validation wrappers.
- Optional OpenAI-compatible chat client for local model endpoints.

These are implementation states, not automatic certification. See [`docs/14-adapters/ADAPTER_SUPPORT_MATRIX.md`](docs/14-adapters/ADAPTER_SUPPORT_MATRIX.md).

## Repository map

| Path | Purpose |
|---|---|
| `src/elevenvt_studio` | Executable Python runtime, MCP server, adapters, policy, DAG, artifact store |
| `catalogs/runtime` | Runtime-executable capability contracts |
| `schemas/runtime` | JSON schemas for jobs, capabilities, approvals and evidence |
| `skills` | Specialist instructions for Freebuff agents |
| `docs/00`–`docs/15` | Mission, scope, research, architecture, disciplines, pipelines, quality, security, operations and implementation standards |
| `examples/workflows` | Safe starter workflow definitions |
| `scripts/windows`, `scripts/linux` | Bootstrap, tests and integration templates |
| `tests` | Runtime unit and integration tests |

## Explicit non-claims

This repo does not bundle proprietary applications, model weights, paid cloud services or production media assets. The runtime has not been installed or validated on the user's Windows workstation. Unreal/Unity and most non-game creative applications are not yet integrated. The current ComfyUI adapter retrieves completed output files but does not validate workflow schemas or prove image quality; Blender execution is not sandboxed; Godot headless validation is not a packaged gameplay test. The official MCP SDK v2 integration is included and is the production path, but its live Freebuff connection must still be reproduced on the target workstation. No commercial certification or valuation is claimed.

## Development

```bash
python -m venv .venv
# activate the environment
python -m pip install -e ".[test]"
pytest -q
studio init
studio doctor
studio database integrity-check
studio database backup
studio job list
```

See `CONTRIBUTING.md`, `LICENSE_POLICY.md` and `CHANGELOG.md` before making changes or redistributing code/assets.

## Integrity manifest

`FILE_MANIFEST.json` records SHA-256 hashes for repository source and handoff files (excluding Git metadata, caches, local environments and itself). Regenerate it after material changes with `python scripts/generate_manifest.py`.
