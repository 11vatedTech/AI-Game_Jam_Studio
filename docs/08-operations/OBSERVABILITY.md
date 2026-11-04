# Observability and Operations Intelligence

## Correlation identifiers

Every user request, project, plan, job, attempt, tool call, app session, artifact and evidence record should have stable identifiers and timestamps. Pass correlation IDs across subprocesses/adapters when possible.

## Logs

Use structured logs with level, event, project/job/attempt/tool IDs, adapter version, app version, operation, duration, status, error category, and evidence pointer. Redact secrets and sensitive content. Keep verbose application output separately with bounded retention.

## Metrics

Track request/task latency; plan revisions; tool invocation count; retries; error rates; timeouts; cancellation; resource utilization; VRAM/RAM peak; model load time; render/generation time; artifact throughput; test pass rate; quality defects; human intervention; and cost where applicable.

## Tracing

Trace a task from brief through planning, subtask nodes, application calls, artifact creation, review, repair and delivery. Use OpenTelemetry-compatible context if supported. Preserve trace IDs in reports.

## Health states

`HEALTHY`, `DEGRADED`, `UNAVAILABLE`, `VERSION_MISMATCH`, `RESOURCE_PRESSURE`, `NEEDS_RECONCILIATION`, `SECURITY_BLOCKED`. Health is computed from actual operation and probes, not process existence alone.

## Operational learning

Use failures to improve capability metadata and recipes. Maintain known-issue signatures and recovery steps, with confidence and source references. Do not automatically rewrite an adapter from one noisy failure without reproduction.
