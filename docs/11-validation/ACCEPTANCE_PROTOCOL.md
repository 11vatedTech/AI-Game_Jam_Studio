# Acceptance and Certification Protocol

## Test record

Every test records ID, requirement, scope, setup, tool/app/model versions, hardware, steps, expected result, actual result, pass/fail, logs, artifact hash, evidence path, date, operator/reviewer and issue links.

## Pass semantics

- **PASS:** every specified predicate satisfied.
- **FAIL:** one or more predicates violated.
- **NOT_RUN:** no result; never counted as pass.
- **BLOCKED:** precondition/environment prevented execution.
- **WAIVED:** only with explicit authorized approval for non-P0 items.

## Suite acceptance

A capability suite passes only if all mandatory tests pass, there are no unresolved P0/P1 defects (unless an approved P1 exception is valid), and required reviews and governance checks are complete. Certification is per declared versions/support matrix.

## Release acceptance

A release must also pass system-level integration, regression, security, license, performance, packaging and clean-room tests. A release cannot inherit certification from a different version or machine configuration without evidence that the support matrix applies.

## Human craft review

Where craft is subjective or context-heavy, use a defined rubric, two independent reviewers for high-impact assets where feasible, and recorded defect examples. Automated review may assist but cannot certify subjective quality until it demonstrates reliability on an annotated test set.

## Regression discipline

After any change, identify impacted dependencies and run targeted plus full required regressions. Golden artifact changes require explicit approval and new baseline evidence; do not update golden images to hide defects.
