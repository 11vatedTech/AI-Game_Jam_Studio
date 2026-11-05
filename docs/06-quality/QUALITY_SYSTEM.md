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

## Diagnosis discipline

**No diagnostic may claim a cause more strongly than its evidence permits.** This applies to every discipline the studio evaluates — pixels, geometry, animation, interfaces, audio — and to humans and agents alike.

1. **Separate what was observed from what was inferred.** A report field that measures and a report field that explains must be distinguishable, and the explanation must cite the measurement.
2. **State the instrument.** Coverage, detail, illumination, loudness and legibility each need their own evidence. One proxy number must not stand in for another dimension.
3. **Say `undetermined` when an input was never captured.** An absent control is not a mild limitation; it is the difference between a measurement and a guess.
4. **Make every inferred cause falsifiable and name the test that would falsify it.** A cause that no observation could contradict is a story.
5. **A failed hypothesis is evidence.** Supersede it with hashes and a reason; never delete it. The record of a corrected error is what makes the next correction credible.
6. **Disclose the arithmetic of every metric:** numerator, denominator, denominator semantics, included and excluded regions, source hashes, threshold, contract version, and whether the result is a measurement or an inference.
7. **A mask, score or statistic means one thing.** Any artifact whose meaning is ambiguous (for example a mask that means both "visible" and "present") must be split into separately typed roles.
8. **A critic must know the limits of its own instruments.** Every evaluator — 3D character, animation, audio mix, UI composition, gameplay behaviour, architecture — must state what its instruments can establish, what they cannot, and when the evidence is insufficient to judge at all.
9. **Separate measurement status from assertion type.** "Was this measured?" and "is this a measurement or an inference?" are different questions. Every dimension reports `evidence_status`; every conclusion reports `assertion_type`. A conclusion never borrows the status of its inputs.
10. **A measurement states its scope.** A number computed over the whole frame may not be reported under a name that promises the scene, the character, the mix or the room. If the scope cannot be established, the metric reports `not_measured` and names what does exist.
11. **Two identical numbers are one check.** If two metrics return the same value on the same input because they share a denominator, one of them is not measuring anything. Name the duplicate, or remove it from the verdict.
12. **A proxy measures itself, not the thing it stands for.** Pixel variation is not readability; loudness is not clarity; frame time is not smoothness. A proxy may be reported, may be gated, and may never be described as the quality it approximates.

Case study: [a critic that described a symptom and called it a cause](CASE_STUDY_DARK_DIAGNOSIS.md).

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
