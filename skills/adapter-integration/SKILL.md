# Skill: Adapter Integration Engineer

## Mission
Integrate mature applications through stable semantic APIs and make each operation safe, observable and testable.

## Research
Inspect upstream docs, source, tag, license, issues, security, examples and test suite. Compare alternatives. Pin revision. Reproduce in target OS before adoption.

## Adapter contract
Each operation declares stable ID/version, typed inputs/outputs, preconditions, side effects/scopes, permissions, resource needs, timeout/cancel, idempotency, error taxonomy, postconditions, logs and evidence. Record app version and support matrix.

## Execution
Prefer native APIs and bulk/transactional operations. Use GUI only when no robust API exists and capture pre/post screenshots. Never use raw script execution as an unrestricted default. After write, read state back. Fail closed if postcondition is not met.

## Certification
Pass all adapter tests, version compatibility, failure/cancel behavior, security and license review. Tool discovered or server started is not an integrated capability.
