# Repository Agent Rules

## Authority hierarchy

1. Safety, law, security, and license obligations.
2. Explicit user requirements and approved project decisions.
3. `docs/00-foundation/QUALITY_BAR.md` and mandatory quality gates.
4. Approved architecture and ADRs.
5. Discipline-specific requirements and acceptance tests.
6. Implementation convenience and agent preferences.

A lower layer cannot waive a higher one. If two authoritative documents conflict, stop the affected change, record the conflict, and create an ADR proposal.

## Working rules

- Read `FREEBUFF_START_HERE.md` before any implementation.
- Search this repository before asking the user to repeat known context.
- Research existing professional solutions before implementing a subsystem.
- Make small, reviewable changes. Preserve unrelated work.
- Use deterministic tests and retain machine-readable evidence.
- Never alter user projects outside approved workspace boundaries.
- Do not store secrets, API keys, user credentials, or private personal data in this repository.
- Do not commit large binary assets, model weights, caches, or derived builds by default.
- Generated content needs provenance and license policy metadata.
- Mark uncertainty explicitly. Never convert assumptions into facts.

## Required status taxonomy

`NOT_STARTED`, `RESEARCHING`, `DESIGNED`, `IMPLEMENTING`, `INTEGRATING`, `TESTING`, `BLOCKED`, `VALIDATED`, `CERTIFIED`, `DEPRECATED`.

`CERTIFIED` is capability- and version-specific. A passing test on one machine does not imply certification on all operating systems or application versions.

## Change requirements

Changes affecting architecture, dependencies, security boundaries, file formats, artifact schemas, agent authority, quality gates, or licensing require an ADR. Integrations require adapter records and conformance tests. New capabilities require a capability record and acceptance test before they can be advertised as supported.
