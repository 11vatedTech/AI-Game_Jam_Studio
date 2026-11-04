# Skill: Production Architect

## Mission
Design a reproducible manufacturing graph that coordinates applications, agents, models and human review without losing provenance or control.

## Procedure
1. Derive acceptance matrix from requirements.
2. Inspect the capability catalog and candidate applications; research gaps before custom code.
3. Break production into typed dependency tasks with declared inputs/outputs, scope, side effects, resource profile, timeout, idempotency, postconditions and rollback.
4. Assign one writer per mutable project region. Use checkpoints and stable artifact IDs.
5. Schedule heavy workloads against measured RAM/VRAM/disk and existing editor processes.
6. Persist job state before/after external side effects; on uncertain failure, reconcile before retry.
7. Verify application state after writes and retain logs/output metadata.
8. Keep optional paid/network services explicit and off by default.

## Deliverables
Task DAG, app/version matrix, operation contract, permissions, recovery plan, artifact lineage and acceptance report.
