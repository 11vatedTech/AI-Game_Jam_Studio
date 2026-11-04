# Operations, Reliability and Support Backlog

Before any broad external use, implement:

1. Versioned SQLite migrations and startup compatibility checks.
2. Database backup, restore, integrity and disaster recovery.
3. Crash reconciliation for subprocess jobs and long-running application operations.
4. Job cancellation, task timeout, graceful termination, process tree cleanup and compensation hooks.
5. Per-project/per-artifact locks and external application instance coordination.
6. Structured logs, trace IDs across job/task/adapter/process, redaction and log retention.
7. Health endpoints/diagnostics for each adapter; clear distinction between app up, adapter connected and capability qualified.
8. Resource reservation with memory/VRAM telemetry, admission, release and preemption policies.
9. Queue priority, retry/backoff/idempotency and dead-letter handling.
10. Upgrade/rollback, config migration and clean uninstall.
11. Security reporting, vulnerability response, signed releases and SBOM.
12. Backup of workflow definitions, approved project context, artifact manifests and evidence.

Do not build distributed scheduling until local reliability is proven. A local-first studio should remain useful and safe without hosted control planes.
