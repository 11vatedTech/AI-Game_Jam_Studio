# Project Context, Canon, and Durable Memory

## Purpose

The agent must retain relevant project knowledge across long workflows and sessions without becoming dependent on giant transcripts or unverified assumptions.

## Context layers

1. **Studio invariants:** security, licensing, acceptance rules, product principles.
2. **Project canon:** approved brief, goals, audience, constraints, architecture, art bible, design tokens, naming, target platforms.
3. **Decision history:** approved/rejected options, rationale, date, owner, consequences, superseding decisions.
4. **Artifact state:** IDs, paths, hashes, parents, dependencies, validation state, latest approved version.
5. **Capability state:** adapter version, host compatibility, last health, reproduction evidence, known failures.
6. **Task state:** current plan, dependencies, checkpoint, blockers, pending approvals, failure/retry context.
7. **Validated recipes:** workflows that have produced accepted outputs, with versions and applicability.
8. **Transient observations:** temporary model/tool outputs, screenshots, speculative notes; expire or remain explicitly untrusted.

## Memory write policy

- Store durable facts only when useful for future project execution.
- Preserve origin, timestamp, scope, confidence, author and evidence.
- Mark assumptions and inferred observations separately from approved decisions.
- A user correction supersedes incorrect project memory; keep audit history where it impacts prior artifacts.
- Avoid secrets, sensitive personal information, credentials, and unnecessary private data.
- Do not store full prompt dumps if a structured brief and artifact references suffice.

## Context retrieval

Retrieve context by project, task, capability, artifact dependency and semantic relevance. Include active constraints and superseding ADRs. Prefer a source artifact over a cached summary. Every selected memory item should have a reason it affects the current task.

## Staleness

Capabilities, app versions, model IDs, pricing, licensing, support matrices and source URLs can become stale. Give them review dates and invalidation triggers. Never rely on a remembered version when the installed environment can be inspected.
