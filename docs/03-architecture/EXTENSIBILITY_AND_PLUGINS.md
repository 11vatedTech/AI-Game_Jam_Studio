# Extensibility, Plugins, and Capability Ecosystem

## Extension principles

- Extensions are packages with manifests, declared capabilities, semantic versions, permissions, dependencies, compatibility, license, tests, provenance, and maintenance owner.
- Install into a quarantine area first. Review source, install scripts, binaries, transitive dependencies, network behavior, and data access.
- Require capability discovery and runtime health; do not trust a manifest alone.
- Support pinning, rollback, disable, uninstall, and upgrade tests.
- Keep vendor/application-specific code behind adapters.
- Prefer upstream contribution when a fix benefits everyone and the project's governance is healthy.

## Extension package contents

`manifest`, adapter implementation or mapping, skill docs, schemas, setup/uninstall hooks (declarative where possible), dependency lock, license notices, support matrix, health check, unit/integration/conformance tests, example workflow, threat model notes, changelog, and evidence.

## Capability negotiation

At startup, discover adapter and app versions, then negotiate capabilities and schema versions. Unsupported operations must be unavailable or clearly downgraded—not silently emulated with unsafe behavior. Tool descriptions should be concise and task-oriented; load detailed Skills when relevant.

## Marketplace governance

A future catalog may contain first-party, upstream, and third-party packages. Searchability is not endorsement. Display maturity, last verified date, security/license status, app versions, offline support, and known limitations. Require a signed or checksum-verified package artifact and a review trail for certified entries.
