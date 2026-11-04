# ADR-0002: Integrate Professional Applications Before Reimplementing Them

- **Status:** Accepted
- **Date:** 2026-11-04

## Context

The goal spans many production disciplines. Reimplementing mature 3D editors, game engines, audio workstations, CAD, image editors, video suites or their established automation surfaces would waste effort and lower the quality ceiling.

## Decision

Adopt/extend/wrap mature applications and professional open-source systems where their capabilities meet requirements. Prefer native APIs/SDKs for authoritative state and established gateways such as MCP where they provide useful coverage. Build studio-owned orchestration, policy, artifact lineage, context, evaluation and cross-tool glue only where a demonstrated gap remains.

## Consequences

- Every dependency is pinned and rights/security-reviewed.
- A discovered upstream capability is not considered integrated until local smoke/conformance tests pass.
- A tool count is not a quality metric.
- If no mature solution meets the acceptance gate, build only the minimum missing adapter/bridge and contribute upstream where practical.
