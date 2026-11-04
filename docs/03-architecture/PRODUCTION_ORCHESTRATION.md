# Production Orchestration

## Task graph contract

A production task is a graph of typed nodes and edges. Each node declares: objective, inputs, outputs, tool/capability dependencies, permission, resources, timeout, retry/idempotency behavior, checkpoint boundary, completion predicate, evidence, and compensation/rollback where possible.

## Job lifecycle

`CREATED → VALIDATING → READY → RUNNING → WAITING_FOR_TOOL / WAITING_FOR_APPROVAL / WAITING_FOR_RESOURCE → VERIFYING → SUCCEEDED | FAILED | CANCELLED | BLOCKED`.

Terminal states are immutable except through an explicit superseding job or correction event. A retry creates an attempt record under the original job; it does not erase prior failures.

## Workflow requirements

- Persist state before and after external side effects.
- Use idempotency keys for operations that may be retried.
- Separate pure planning/validation tasks from side-effecting application actions.
- Use compensating actions where true transactions are impossible.
- Detect stale project state and concurrent modification.
- Reserve GPU/memory/application sessions before launching resource-intensive work.
- Support cancellation and cleanup of child processes and temporary artifacts.
- Route long-running tasks using polling, event streams, or completion callbacks; do not treat enqueue success as completion.
- Persist logs and evidence even when a job fails.
- Bound retry attempts and use backoff/jitter only where retry is safe.

## Resource scheduling

Resources include CPU threads, RAM, VRAM, disk space, application instances, licenses/seats, network bandwidth, and GPU contention. Each task declares a measured or conservative profile. Scheduler admission uses live monitoring and a safety reserve. Prefer sequential execution of heavy models on 12 GB VRAM rather than optimistic multi-model concurrency.

## Concurrency and locking

Use per-project and per-artifact locks where writes conflict. Read-only inspection can run concurrently when safe. Application adapters declare whether the host is thread-safe, main-thread-only, single-instance, or multi-instance. Avoid multiple agents concurrently modifying the same scene, graph, timeline, or project file.

## Recovery

On crash/restart, reconcile job state with actual application/process/artifact state. Mark uncertain operations `NEEDS_RECONCILIATION`. Inspect side effects before retrying. Preserve partial artifacts for diagnosis. Never blindly replay destructive editor operations.
