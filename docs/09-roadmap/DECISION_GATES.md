# Architecture and Investment Decision Gates

## Gate A — Build vs reuse

Before custom implementation, prove the relevant mature options are insufficient. Document at least one reproduction or technical blocker. A language preference or desire for ownership is not enough by itself.

## Gate B — Platform integration

A connector is not adopted because it connects once. Require version support, correct state mutation, postconditions, error transparency, permissions, logs, cancellation, restart behavior, and test coverage.

## Gate C — Workflow engine

Do not adopt two overlapping orchestrators until task lifecycle, durability, approval and recovery requirements are benchmarked. Use the least complex mature solution satisfying the measured needs.

## Gate D — Model/runtime

Require model quality benchmarks for actual task, license clearance, hardware fit, memory headroom, and local serving reliability. A model's parameter count or benchmark leaderboard does not prove production quality.

## Gate E — Asset pipeline

Do not scale a pipeline until it produces a real editable asset, passes its quality rubric, integrates into a consuming project and reproduces from captured settings.

## Gate F — Visual moat

Do not claim a visual capability from an impressive single image. Require style consistency, iteration/editability, context renders, failure cases, and blind/independent review where practical.

## Gate G — Certification and release

100% mandatory tests pass; no unresolved P0; all P1 resolved or approved exceptions; provenance/license/security review complete; clean-room delivery validated; support limitations disclosed.
