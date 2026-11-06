# P0 — Local Runtime Foundation Acceptance

Run on a clean Windows 11 user environment and retain command output under `reports/p0/`.

| ID | Acceptance | Method | Pass condition |
|---|---|---|---|
| P0-001 | Clean installation | Windows bootstrap script on Python 3.11+ | venv and package install without global Python mutation |
| P0-002 | CLI status | `studio status` | Correct version/home/workspace/database |
| P0-003 | Workstation inventory | `studio doctor` | Timestamped OS/CPU/disk/GPU plus real app presence and ComfyUI health state |
| P0-004 | Unit/integration tests | `pytest -q` | 100% mandatory tests pass; no skipped security tests |
| P0-005 | MCP negotiation | 2026 `server/discover` plus tools/list/tool call; also prove legacy initialize interoperability | SDK-valid protocol responses, stable typed tool schemas, stdout protocol only; no ping dependency (removed from current protocol). SDK-over-stdio **PASS** 2026-11-06 (protocol `2026-07-28`, 20 tools, `studio_status`, create-only workspace write); **configured Freebuff host connection still open**. |
| P0-006 | Safe file creation | smoke workflow | File created in workspace; hash registered and verified |
| P0-007 | Path isolation | traversal/absolute/symlink tests | All escape attempts denied |
| P0-008 | No-overwrite | concurrent duplicate path attempts | Exactly one create succeeds; none overwrites another |
| P0-009 | Approval binding | request/approve with mismatched target | Only exact scope, class, target, expiry works |
| P0-010 | Crash/restart | kill worker after task state becomes RUNNING; restart and inspect | Automated recovery quarantines task as `NEEDS_RECONCILIATION`; no replay; human CLI requires evidence and an explicit retry/mark-complete decision. **PASS** 2026-11-06 on a real process kill (exit 1): restart quarantined the task, a second run stayed quarantined, attempt stayed 1, no side effect ran. **Second round PASS**: worker killed mid-`comfyui.await_completion` while a live 28-step generation was in flight server-side; restart quarantined (attempt 1); the generation later completed, proving blind retry would have duplicated GPU work. Reconcile itself remains a human CLI step. |
| P0-011 | Database backup | backup, restore into an isolated DB, compare records and integrity | **PASS** 2026-11-06: backup and restore integrity PASS, all nine table row counts matched, a specific `decisions` row read back correctly, zero foreign-key violations. **Second round PASS on a loaded DB**: 20 MiB bulk load plus a concurrent writer stopped mid-storm (82 MB DB, 3207 event rows); integrity PASS, 0.94 s backup, all nine tables matched in the isolated restore, job read back SUCCEEDED. |
| P0-012 | Secrets hygiene | repository and log scan | No credentials, tokens or private data |
| P0-013 | Runtime support statement | capability catalog audit | Each feature's implementation and maturity status accurately labeled |

P0-010 and P0-011 each have two rounds of on-device drill evidence, recorded in `reports/p0/P0-EVIDENCE-2026-11-06.json` (amended 2026-11-06T12:35Z). What remains on P0: a configured **Freebuff host** handshake (the SDK transport itself is proven; no MCP server is registered in the installed client, so this step needs the operator), the human `job reconcile` confirmation for the quarantined ComfyUI wait (interactive TTY by design), and recovery from a torn OS-level write mid-commit (none observed). The manifest generator now hashes tracked files only and `FILE_MANIFEST.json` is regenerated (355 files, no leaks). P0 is not complete until every row passes on this machine.
