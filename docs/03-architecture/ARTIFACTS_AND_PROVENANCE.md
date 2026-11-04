# Artifacts, Lineage, and Provenance

## Artifact identity

Every artifact receives a stable logical ID independent of its filename. Record artifact type, project, task/job, version, hash, location, native format, target format, source dependencies, generator/tool/model version, settings, license/provenance, validation state, and downstream consumers.

## Artifact lifecycle

`INPUT → WORKING → REVIEW → APPROVED_SOURCE → EXPORTED → INTEGRATED → RELEASED → ARCHIVED`.

A rejected artifact remains accessible for audit and learning but cannot be referenced as the active approved version. Supersession is explicit.

## Lineage graph

Record parent/child relationships: references → concept → source asset → derived exports → engine import → integrated scene → build → release. Store transformation parameters and hashes. A delivery manifest should allow a reviewer to locate the editable source and understand how the final output was produced.

## Storage tiers

- Git: source code, text specs, schemas, lightweight manifests, test fixtures.
- Git LFS or an artifact store: large binary assets selected for versioning.
- Local content-addressed store: generated intermediates and large assets with retention rules.
- External library/package registry: reusable licensed content and models with pinned versions.
- Cache: disposable model/tool/download/build cache, never treated as source of truth.

## Integrity

Use SHA-256 or stronger accepted digest for artifact identification; store file size and timestamp. Verify copied/exported files against expected hashes. Use atomic temp-write/rename where possible. Never silently overwrite an approved source artifact.

## Provenance fields

At minimum: origin (`human`, `generated`, `third_party`, `derived`), source URI, revision or model ID, creator/tool, license, generation parameters where appropriate, transformations, human edits, approvals, and restrictions. Do not imply that provenance records guarantee legal rights; they provide traceability for review.
