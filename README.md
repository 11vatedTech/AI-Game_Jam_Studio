# 11vatedTech AI Game Jam Studio — Master Design Specification

**Specification release:** 0.1.0  
**Status:** Foundational design baseline; not an implementation or a certification.  
**Target repository:** [`11vatedTech/AI-Game_Jam_Studio`](https://github.com/11vatedTech/AI-Game_Jam_Studio)  
**Primary consumer:** Freebuff agent and the engineering/creative agents it coordinates.

> **Mission:** Build a universal creative-production intelligence that can take incomplete human intent, turn it into a professionally designed production plan, operate the strongest suitable tools and applications, manufacture genuine deliverables, integrate them into a coherent product, and prove that the result satisfies explicit acceptance criteria.

This repository is the product's **design contract**. It specifies what the system must become, how work must be performed, how quality is judged, what may be reused, what evidence is required, and how implementation is to be staged. It is deliberately separate from the eventual runtime implementation.

## Governing principle

**Reuse proven excellence. Integrate it deeply. Extend only where a demonstrated gap remains. Verify every result.** Do not recreate a mature application, protocol, workflow engine, model runtime, or production pipeline because it is easier to write a small substitute. Discover, inspect, reproduce, benchmark, adopt/extend/wrap/replace, then certify.

## What this studio is—and is not

- It is one coherent production system with a central intent-to-delivery loop and a flexible set of specialist roles, skills, tools, applications, models, and pipelines.
- It covers game development and adjacent disciplines, but is not limited to games: 2D/3D, design, media, software, simulation, CAD, writing, audio, video, publishing, and future domains.
- It uses professional applications as production instruments. MCP is one integration protocol, not the entire architecture.
- It is local-first and free/open-source-first where feasible, while allowing clearly identified optional commercial tools when they materially improve results.
- It is evidence-first. Tool discovery, file creation, a successful process exit, or an LLM statement is not proof of production quality.
- It does not promise perfect results for arbitrary subjective requests. It requires 100% passage of the mandatory acceptance suite for any capability or release it certifies.

## Start here

1. [`FREEBUFF_START_HERE.md`](FREEBUFF_START_HERE.md) — binding instructions for the Freebuff agent.
2. [`AGENTS.md`](AGENTS.md) — agent operating rules and repository navigation.
3. [`docs/00-foundation/PRODUCT_MISSION.md`](docs/00-foundation/PRODUCT_MISSION.md) — product identity and north-star outcomes.
4. [`docs/00-foundation/MASTER_SYSTEM_CONTRACT.md`](docs/00-foundation/MASTER_SYSTEM_CONTRACT.md) — 15 binding system invariants.
5. [`docs/00-foundation/QUALITY_BAR.md`](docs/00-foundation/QUALITY_BAR.md) — the minimum professional quality contract.
6. [`docs/00-foundation/VISUAL_MOAT.md`](docs/00-foundation/VISUAL_MOAT.md) — visual quality strategy and non-negotiable standards.
7. [`docs/03-architecture/REFERENCE_ARCHITECTURE.md`](docs/03-architecture/REFERENCE_ARCHITECTURE.md) — target system architecture.
8. [`docs/03-architecture/ADAPTER_CONFORMANCE.md`](docs/03-architecture/ADAPTER_CONFORMANCE.md) — how integrations earn support status.
9. [`docs/03-architecture/PROJECT_CONTEXT_AND_MEMORY.md`](docs/03-architecture/PROJECT_CONTEXT_AND_MEMORY.md) — persistent project canon and memory rules.
10. [`docs/09-roadmap/MASTER_ROADMAP.md`](docs/09-roadmap/MASTER_ROADMAP.md) — sequence, dependencies, and exit gates.
11. [`docs/10-adoption/ADOPTION_DECISIONS.md`](docs/10-adoption/ADOPTION_DECISIONS.md) — current reuse/adoption posture.

## Repository map

| Area | Purpose |
|---|---|
| `docs/00-foundation` | Mission, quality, visual moat, production moat, vocabulary |
| `docs/01-requirements` | Product requirements, capability universe, intent routing, non-functional requirements |
| `docs/02-research` | Benchmark research, reference ecosystem, integration candidates, standards, research method |
| `docs/03-architecture` | Runtime, orchestration, contracts, artifact lineage, models, plugins |
| `docs/04-disciplines` | Domain-specific production requirements across creative and technical fields |
| `docs/05-pipelines` | End-to-end manufacturing pipelines and lifecycle controls |
| `docs/06-quality` | Quality system, evaluation, testing, visual/audio review, evidence and release |
| `docs/07-security` | Threat model, permissions, licensing, provenance, supply chain |
| `docs/08-operations` | Hardware profile, installation, observability and operations |
| `docs/09-roadmap` | Phases, dependencies and decision gates |
| `docs/10-adoption` | Adopt/extend/wrap/build decisions and research priorities |
| `docs/11-validation` | Benchmark scenarios, test protocol, scorecards and certification rules |
| `catalogs` | Machine-readable capability/reference/standard/benchmark registries |
| `schemas` | JSON Schemas for capability, artifacts, jobs and quality reports |
| `templates` | ADR, adapter, skill, production plan, acceptance test, incident templates |
| `examples` | Illustrative, non-production examples of a project brief and evidence package |

## Truth labels

Use these labels consistently in docs, logs, issues, and status reports:

- **PROPOSED** — candidate direction; not yet investigated sufficiently.
- **RESEARCHED** — primary documentation/source examined; no execution proof implied.
- **INSPECTED** — repository/source/release/license/issues examined at a pinned revision.
- **REPRODUCED** — documented workflow executed in the target environment.
- **INTEGRATED** — connected to the studio using a defined contract.
- **VALIDATED** — required acceptance suite passed with retained evidence.
- **CERTIFIED** — validated, security/licensing reviewed, version-pinned, and approved for a defined support matrix.
- **DEPRECATED / REJECTED** — decision recorded with rationale and migration path where applicable.

The current specification does **not** claim that the candidate systems listed here have been installed, reproduced, integrated, or certified in the user's environment.

## Scope boundary

This is the design specification for the studio. It is not the full implementation, not an asset library, not a model bundle, and not a claim that each domain is already supported. The implementation must turn this contract into executable capabilities in the staged sequence defined here.

## Design authority

The latest approved requirements, architecture decision records, capability registry, and quality gates govern implementation. Where documents conflict, record the conflict as an ADR rather than silently choosing. Safety, security, license obligations, and release gates cannot be bypassed by a lower-priority prompt.
