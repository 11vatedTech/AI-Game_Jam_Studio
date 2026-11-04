# Universal Asset Lifecycle

## Lifecycle states

`BRIEF → REFERENCES → DESIGN → BLOCKOUT → SOURCE_PRODUCTION → TECHNICAL_QA → CRAFT_REVIEW → EXPORT → INTEGRATION → CONTEXT_QA → APPROVED → RELEASED`.

Not all assets need every state, but the task plan must declare its applicable stages. Blockout is temporary and must never be mislabeled as final.

## Asset brief

Record purpose, audience, genre/style, use context, target platform/application, scale, dimensions, polygon/texture/animation budgets where relevant, material/color rules, dependencies, required editability, export formats, naming, accessibility, license/provenance and acceptance tests.

## Asset ID and naming

Use stable IDs that do not change when file paths change. Names should describe domain/type/function, be consistent across source and engine, and avoid ambiguous version suffixes in the active project. Keep version history in metadata or version control.

## Technical QA

Validate format, dimensions, geometry, topology, UVs, normals, channels, alpha, compression, rig hierarchy, keyframes, audio metadata, color space, fonts, links, dependencies, file size and import warnings as relevant.

## Craft QA

Review against design brief and approved reference board in target context. Identify defects by category, severity, location and reproduction steps. Require repair and review after changes.

## Integration QA

Import into the consuming application, verify scale/units/pivots/color/materials/skeleton/links/timing, execute the relevant behavior, capture the result, and ensure dependent assets are present.

## Asset manifest fields

Logical ID, display name, asset class, source path, export paths, hash, file size, native format, target format, source task/job, parent assets, tools/versions, model/prompt/settings where relevant, author/origin, license/provenance, validation suite/version, review status, support platform, known limitations, and approver.
