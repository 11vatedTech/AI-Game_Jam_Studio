# Adapter Conformance Standard

An adapter is certified only when it passes the common integration contract plus domain-specific tests.

## Test groups

- **Discovery:** metadata and capabilities match actual installed app/plugin versions.
- **Connection:** start, connect, health, reconnect, disconnect, stop, stale session.
- **Schema:** valid inputs, invalid types, missing fields, boundary values, oversized values.
- **Permissions:** read-only mode, out-of-workspace path, destructive operation, script execution, network request, credential access.
- **Semantics:** action actually changes intended native app state; read-back confirms the result.
- **Transactions:** undo group, partial edit, conflict, rollback, atomic operation where supported.
- **Concurrency:** duplicate invocation, simultaneous app sessions, app busy, conflicting project writes.
- **Lifecycle:** timeout, cancellation, crash, restart, app version mismatch, plugin upgrade/uninstall.
- **Evidence:** logs, state snapshots, screenshots, artifact hashes and structured output.
- **Performance:** latency, throughput, process/memory overhead, stability under repeated calls.
- **Compatibility:** declared app versions and supported OS/hardware.

## Certification result

Report per-capability results; an adapter may pass some capabilities and fail others. Do not mark an entire adapter certified solely because its health check passes. Expose unsupported/experimental operations separately.
