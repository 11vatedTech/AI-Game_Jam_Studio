# Integration Contracts

## Adapter architecture

Every adapter is a boundary around an external application or service. It should expose stable typed studio operations while hiding transport and app-version details. Use MCP, REST, CLI, Python, SDK, plugin, IPC, or file exchange according to the strongest supported interface.

## Required adapter metadata

- Adapter ID, version, upstream source, license, owner, application ID/version range.
- Supported OS/architecture and dependency manifest.
- Connection type, endpoints/ports, authentication, process/session lifecycle.
- Capability list and maturity per capability.
- Permission scopes, workspace boundaries, and dangerous operations.
- Health checks, diagnostics, logs, metrics, and error taxonomy.
- Concurrency/threading constraints and timeout/cancellation behavior.
- Artifact formats, units, color spaces, axis conventions, and path rules.
- Test suite, evidence capture, known limitations, upgrade/uninstall procedure.

## Tool definition

Every tool schema needs: unique stable identifier; version; purpose; typed input/output schema; constraints; side-effect class; permission scope; resource class; timeout; cancellation; idempotency; preconditions; postconditions; error codes; provenance; and acceptance tests.

## Side-effect classes

- `READ`: inspect state; no project mutation.
- `CREATE`: create a new isolated object/file.
- `MODIFY`: change existing project state.
- `DELETE`: destructive removal.
- `EXECUTE`: run code, scripts, commands, builds, or simulations.
- `NETWORK`: external access.
- `CREDENTIAL`: access secrets or authenticated endpoints.
- `PUBLISH`: external release/distribution.

Side-effect class is not a permission grant. Enforce explicit policy at runtime.

## Application control rules

- Prefer semantic operations (create material, set property, add keyframe) over raw screen coordinates.
- Use GUI/computer-use automation only when no stable API exists, and require a screenshot/visual precondition plus postcondition.
- Main-thread editor APIs must marshal operations to the proper thread.
- Prefer bulk/transactional edits and undo groups when supported.
- After a write, inspect resulting app state and verify the intended postcondition.
- Capture editor logs and runtime logs; distinguish warnings from failures.

## Error model

Standard categories: `INVALID_INPUT`, `UNSUPPORTED_VERSION`, `NOT_CONNECTED`, `APP_BUSY`, `PERMISSION_DENIED`, `RESOURCE_UNAVAILABLE`, `TIMEOUT`, `CANCELLED`, `CONFLICT`, `POSTCONDITION_FAILED`, `UPSTREAM_ERROR`, `CORRUPT_ARTIFACT`, `LICENSE_BLOCKED`, `SECURITY_BLOCKED`, `UNKNOWN`. Errors must preserve source, operation, retryability, and evidence context.
