# P0 — Local Runtime Foundation Acceptance

Run on a clean Windows 11 user environment and retain command output under `reports/p0/`.

| ID | Acceptance | Method | Pass condition |
|---|---|---|---|
| P0-001 | Clean installation | Windows bootstrap script on Python 3.11+ | venv and package install without global Python mutation |
| P0-002 | CLI status | `studio status` | Correct version/home/workspace/database |
| P0-003 | Workstation inventory | `studio doctor` | Timestamped OS/CPU/disk/GPU plus real app presence and ComfyUI health state |
| P0-004 | Unit/integration tests | `pytest -q` | 100% mandatory tests pass; no skipped security tests |
| P0-005 | MCP negotiation | 2026 `server/discover` plus tools/list/tool call; also prove legacy initialize interoperability | SDK-valid protocol responses, stable typed tool schemas, stdout protocol only; no ping dependency (removed from current protocol) |
| P0-006 | Safe file creation | smoke workflow | File created in workspace; hash registered and verified |
| P0-007 | Path isolation | traversal/absolute/symlink tests | All escape attempts denied |
| P0-008 | No-overwrite | concurrent duplicate path attempts | Exactly one create succeeds; none overwrites another |
| P0-009 | Approval binding | request/approve with mismatched target | Only exact scope, class, target, expiry works |
| P0-010 | Crash/restart | kill worker after task state becomes RUNNING; restart and inspect | Automated recovery quarantines task as `NEEDS_RECONCILIATION`; no replay; human CLI requires evidence and an explicit retry/mark-complete decision. Unit test passes; on-device kill/restart drill remains required. |
| P0-011 | Database backup | backup, restore into an isolated DB, compare records and integrity | Backup and integrity-check commands implemented; restore comparison is still an open workstation acceptance test. |
| P0-012 | Secrets hygiene | repository and log scan | No credentials, tokens or private data |
| P0-013 | Runtime support statement | capability catalog audit | Each feature's implementation and maturity status accurately labeled |

P0-010 has implementation and unit-test evidence but still needs a real process-kill/restart drill on Windows. P0-011 has backup/integrity implementation but still needs restore comparison. P0 is not complete until all environment-specific tests and the full table pass.
