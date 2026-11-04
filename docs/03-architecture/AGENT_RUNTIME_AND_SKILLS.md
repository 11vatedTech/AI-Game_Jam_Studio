# Agent Runtime, Roles, and Skills

## One coordinator, many specialized competencies

The user experiences one capable agent. Internally it may use specialist roles or delegated agents, but delegation is justified by domain depth, independent review, or useful parallelism—not by a desire to maximize agent count.

## Core responsibilities

- Intent analyst: requirements, assumptions, hidden work, and acceptance mapping.
- Research specialist: professional references, source/license/version review, technology comparisons.
- Creative director: style, narrative, composition, cohesion, design rationale.
- Domain specialists: modeler, animator, technical artist, gameplay engineer, UX designer, audio designer, editor, CAD designer, writer, software engineer, QA.
- Integrator: artifact compatibility, cross-discipline assembly, build/package.
- Evaluator: independent test and quality review.
- Release authority: evidence, compliance, release gates, and explicit approval.

Roles should be represented as reusable Skills, agent profiles, or workflow nodes. Do not create separate agent processes if a constrained subtask or critique pass is enough.

## Skill contract

A Skill contains:

1. Identifier, name, version, description, applicable domains, and maturity.
2. Preconditions and required project context.
3. Professional knowledge, terminology, and reference sources.
4. Workflow and decision criteria.
5. Tool/capability dependencies and permission requirements.
6. Input/output artifact contracts.
7. Quality rubric and acceptance tests.
8. Known failure modes and repair recipes.
9. Evidence required and version compatibility.
10. Owner, license, source, review date, and changelog.

## Context discipline

Use hierarchical context: global product invariants; project brief/art bible; discipline-specific task context; current task state; exact tool schemas; and relevant evidence. Load just the Skills and sources needed for the task. Avoid dumping every tool schema and historical transcript into every model call.

## Memory classes

- Project canon: approved requirements, architecture decisions, style bible, naming rules.
- User preferences: explicit stable preferences with scope and date.
- Artifact memory: stable asset ID, location, hash, dependencies, and lineage.
- Capability memory: actual test outcomes, version-specific failures, and support matrix.
- Recipe memory: validated workflow version, prerequisites, quality outcomes.
- Session context: transient plan and observations; expire when no longer useful.

Memory needs provenance, confidence, scope, version, and correction mechanisms. Do not store secrets or sensitive personal data as project memory.

## Independent critique

For important deliverables, a reviewer role should be separated from the generator's immediate context where practical. Review the brief, reference criteria, artifact, and evidence independently. The reviewer returns defect locations, severity, rationale, and recommended next stage. An LLM critique is advisory until calibrated against human review and objective tests.
