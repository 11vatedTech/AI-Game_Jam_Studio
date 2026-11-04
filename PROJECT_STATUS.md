# Project Status — Design Specification Baseline

**Specification version:** 0.1.0  
**Status:** Draft baseline; ready for structured review and Freebuff ingestion.  
**Implementation status:** No runtime implementation is included in this specification package.  
**GitHub status:** This artifact is being prepared as a local specification package. No GitHub commit is claimed here.

## Truthful state

| Layer | Status | Meaning |
|---|---|---|
| Mission and scope | DESIGNED | Product intent and broad disciplines are specified. |
| Quality/visual/production moat | DESIGNED | Quality principles and acceptance layers are defined; numeric benchmarks require calibration. |
| Research landscape | RESEARCHED / PROPOSED | Candidate ecosystems and primary sources are cataloged; not every candidate has been source-audited or installed. |
| Architecture | DESIGNED | Reference architecture and contracts are specified; implementation choices remain ADR-gated. |
| Runtime | NOT_STARTED | No studio runtime code is included. |
| Adapters | NOT_STARTED | No adapter is certified by this repository. |
| Pipelines | DESIGNED | Manufacturing workflows are specified; no production workflow is certified here. |
| Quality automation | DESIGNED | Test/quality framework defined; calibration and implementation pending. |
| Security review | DESIGNED | Threat model and control requirements drafted; penetration tests pending. |

## Known important candidate

DCC-MCP Core is a high-priority research/adoption candidate because its published architecture describes a broad shared gateway, capability discovery, Skills, multi-instance routing, and diagnostics across creative software. Its catalog is not treated as proof that all adapters are equally mature. The studio must pin a release, audit code/licenses/dependencies, install on the target Windows environment, and execute per-adapter smoke/acceptance suites before adoption.

## Next required actions

1. Review and approve this specification baseline.
2. Run a real workstation and repository inventory.
3. Re-audit AI Game Dev and DCC-MCP Core at pinned revisions, including licenses, architecture, extension APIs, security posture, and smoke tests.
4. Select one integrated vertical slice based on available local software and actual workflow value.
5. Implement one complete intent-to-deliverable workflow with real art, real application integration, quality review, and reproducible evidence before widening the catalog.
