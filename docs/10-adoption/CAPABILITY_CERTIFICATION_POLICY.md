# Capability Certification Policy

## Capability lifecycle

`PROPOSED → DISCOVERED → INSPECTED → REPRODUCED → INTEGRATED → VALIDATED → CERTIFIED`.

Transitions require evidence. A candidate may move backward if compatibility breaks, a security issue appears, or regression tests fail.

## Certification requirements

- Exact immutable source revision or package version.
- License and dependency review complete.
- Application/OS/hardware support matrix explicit.
- Input/output contracts and permissions defined.
- Health check and error taxonomy implemented.
- Required unit/integration/e2e tests pass.
- Postconditions inspect real application state.
- Failure/cancellation/recovery scenarios tested.
- Performance/resource use measured.
- Evidence and owner assigned.
- Known limitations disclosed.

## Expiry and revocation

Certification must be re-evaluated when the application, adapter, protocol, dependency, model or OS version changes materially, or when a security incident or regression occurs. Expired/unverified capabilities may remain available only with visible warning and cannot be represented as certified.
