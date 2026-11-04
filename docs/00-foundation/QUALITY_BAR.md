# Universal Professional Quality Bar

This document defines the minimum standard for claiming a deliverable is production-ready. The criteria are domain-specific; not every criterion applies to every task, but every task must declare which criteria apply and why.

## The quality dimensions

| Dimension | Required question | Minimum acceptable evidence |
|---|---|---|
| Intent fidelity | Does the result solve the actual brief and preserve its essential intent? | Requirement-to-artifact traceability and user review where needed |
| Craft | Does it use techniques and conventions expected by the relevant profession? | Specialist review rubric, native project inspection, references |
| Distinctiveness | Is it intentionally designed rather than generic or template-like? | Art direction, reference comparison, differentiated design rationale |
| Technical correctness | Is the artifact valid, editable, and structurally sound? | Native-app validation, schema/format checks, automated tests |
| Integration | Does it work in the actual target project, engine, application, or pipeline? | Import/build/runtime/round-trip test |
| Coherence | Do the parts feel and function as one complete product? | Cross-discipline review and full-product test |
| Reliability | Does it behave consistently under declared operating conditions? | Regression, stress, failure-recovery, and repeatability tests |
| Performance | Does it meet platform, resource, responsiveness, and quality targets? | Measured benchmarks on declared hardware/targets |
| Accessibility/usability | Can intended users perceive, understand, and operate it? | Accessibility checks and task-based usability review |
| Provenance/compliance | Are sources, licenses, model/data restrictions, and generation lineage known? | Machine-readable manifest and license audit |
| Delivery | Can the recipient open, run, modify, or publish the work as promised? | Clean-room open/build/run test and delivery checklist |

## No false completion

- A generated file existing is not proof it is correct.
- A screenshot of an editor with an asset selected is not proof that the asset renders or behaves correctly.
- A successful API response is not proof that a long-running operation finished.
- A compilation success is not proof of runtime correctness.
- An LLM saying “looks good” is not proof of artistic quality.
- A model benchmark score is not proof of professional suitability for a particular asset.
- A repository listing an integration is not proof that it works on the current host.

## Quality state machine

`BRIEFED → DESIGNED → PRODUCED → TECHNICALLY_VALID → INTEGRATED → FUNCTIONALLY_VALID → CRAFT_REVIEWED → PERFORMANCE_VALIDATED → COMPLIANCE_CLEARED → RELEASE_READY`.

Stages may branch or iterate. No stage may be skipped silently. A task may use a justified subset of stages, but the exclusion must be recorded in its acceptance plan.

## P0/P1/P2 issue severity

- **P0 release blocker:** data loss, security/license breach, corrupt artifact, crash, broken core requirement, severe visual defect, inaccessible critical flow, or materially false claim.
- **P1 major:** visible or functional flaw that harms professional perception or usability; missing core behavior; integration defect; serious performance problem.
- **P2 polish:** minor spacing, typography, timing, naming, alignment, edge cases, or noncritical optimization.

No P0 issue may be waived for certification. P1 requires resolution or explicit owner-approved exception with scope and expiration. P2 can be prioritized, but must remain tracked.

## Calibration

Thresholds must be calibrated by discipline and target. Do not invent universal polygon counts, texture resolutions, audio loudness, frame times, image similarity scores, or model scores. Establish baselines from target platforms, professional references, and observed successful examples. Keep thresholds versioned and test their false-positive/false-negative rates.

## Certification claims

A capability is certified only for a declared version and support matrix, when its mandatory tests pass 100%, its known limitations are documented, its security and license reviews are complete, and reproducible evidence exists. This is a bounded engineering guarantee, not a claim that every possible future request is perfectly solvable.
