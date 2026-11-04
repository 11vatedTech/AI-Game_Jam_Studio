# Changelog

## 0.2.0 — 2026-11-04 — Executable runtime foundation

- Added a dependency-light Python runtime and `studio` CLI.
- Added SQLite persistence for jobs, task states, events, artifacts and approvals.
- Added sequential DAG execution, dependency validation, output references, approval resume and per-job process locks.
- Added crash quarantine and evidence-backed human reconciliation; uncertain external side effects are never blindly replayed.
- Added default-deny policy and exact approval binding.
- Added managed workspace path checks, symlink escape protection and no-overwrite file creation.
- Added SHA-256 artifact registration/integrity verification.
- Added host inventory and conservative CPU/RAM/VRAM resource admission helper.
- Added official MCP Python SDK v2 stdio integration for 2026-07-28 and legacy protocol clients; production transport fails closed unless a developer explicitly opts into the legacy fallback.
- Added MCP discovery and tool-call integration tests for connected CI environments.
- Added ComfyUI inventory, queue/history, bounded completion polling, output download and artifact provenance; loopback redirects are blocked and JSON responses are size-bounded.
- Added approval-gated Blender/Godot process wrappers.
- Added optional OpenAI-compatible local model endpoint client.
- Added unit/integration tests, Windows/Linux bootstrap scripts, cross-platform CI and Freebuff specialist skills.
- Added build-environment validation report and deterministic repository SHA-256 manifest generation.
- Marked unsupported/unverified application capabilities explicitly.

Known limitations are documented in `docs/12-runtime/RUNTIME_FOUNDATION.md` and `PROJECT_STATUS.md`. This release is a developer foundation, not a production-certified universal studio.

## 0.1.0 — 2026-11-04 — Specification baseline

- Established product mission, scope, capability taxonomy, research/adoption framework, reference architecture, discipline-specific workflows, quality gates, security and phased roadmap.
