# Unified Quality System

## Purpose

Quality is a production system, not a final checkbox. The studio must define quality before production, inspect it during production, and require proof before delivery.

## Quality layers

1. Intent/requirements conformance.
2. Format and technical validity.
3. Native-application structural validity.
4. Integration and runtime behavior.
5. Professional craft and visual/audio quality.
6. Performance, usability, accessibility and compatibility.
7. Security, license and provenance.
8. Reproducibility, packaging and delivery.

## Acceptance matrix

Every task must create a table mapping requirement ID → artifact → validation method → pass threshold → evidence pointer → status. Status values: `PASS`, `FAIL`, `NOT_RUN`, `BLOCKED`, `WAIVED_WITH_APPROVAL`. A waiver requires scope, justification, approver, date, risk and expiration; P0 never waivable.

## Automated and expert evaluation

Use objective code/format/geometry/performance tests whenever feasible. Vision/audio models can triage and critique, but their findings must be calibrated against known defects and qualified human judgments. For subjective deliverables, include human review or a validated rubric and disclose residual uncertainty.

## Defect lifecycle

`DETECTED → TRIAGED → ASSIGNED_TO_STAGE → ROOT_CAUSE → FIXED → REGRESSION_TESTED → CLOSED`.

Do not just improve a visual symptom if the cause is upstream. Example: texture stretch should trigger UV repair, not more noise in the texture. Animation contact issues should trigger rig/pose/timing review, not camera shake.

## Test layers

- Unit and property tests for pure logic and data contracts.
- Adapter conformance tests against fake and real applications.
- Integration tests for multi-tool workflows.
- Editor/functional tests in application context.
- Runtime/e2e tests in packaged output.
- Visual/audio regression tests with controlled capture conditions.
- Performance/stress tests and resource measurements.
- Security, permission and supply-chain tests.
- Clean-room installation/open/build/release tests.

## Certification

A capability is certified per exact version/support matrix only when the complete mandatory suite passes 100%, P0/P1 findings are resolved, evidence is retained, owner is assigned, security and license reviews are approved, and future regression runs are automated. A release is certified only when all release-blocking capabilities and system gates pass.
