# ADR-0003: Human Approval for Risky Side Effects

- **Status:** Accepted
- **Date:** 2026-11-04

## Decision

Mutating existing projects, deleting, running arbitrary scripts, installing plugins/packages, using remote network/credentials or publishing requires a narrowly bound, expiring human approval. Approval binds to exact scope, side-effect class and target. Agents may request but must not grant their own approvals. The executable policy is default-deny.

## Rationale

External creative applications and custom nodes may execute code with user privileges. A typed tool schema is not a sandbox. Reversible-first execution, duplicate projects, review and postconditions reduce risk but do not replace isolation.
