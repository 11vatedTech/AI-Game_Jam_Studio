# Contribution and Governance Model

## Ownership

Every production-critical component has an owner responsible for maintenance, versions, security updates, compatibility, tests and documentation.

## Change governance

- Requirements and quality gates change through reviewed specification updates.
- Architecture and dependency changes require ADRs.
- Capability changes require schema and acceptance updates.
- Adapter additions require security/license review and conformance tests.
- Golden test baselines require explicit review and rationale.
- Releases include changelog, manifest, SBOM, license notices and regression evidence.

## Upstream-first policy

When a defect is in an adopted dependency, reproduce it against a pinned upstream version. Prefer a contribution or supported extension point over a long-lived private fork. Maintain a patch fork only when necessary and record upstream tracking/rebase policy.

## Documentation maintenance

Every research record has last-reviewed date, source revision, confidence and revalidation triggers. Remove or mark stale references rather than preserving obsolete claims as current facts.
