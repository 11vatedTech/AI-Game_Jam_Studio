# Research and Technology Selection Method

## Why this research exists

The industry has already solved many of the problems this studio will encounter. Research must precede original implementation. The goal is not to collect popular names; it is to identify the best proven solution for each production outcome and connect those solutions into a coherent system.

## Evidence hierarchy

1. Primary upstream source code at a pinned commit or release.
2. Official technical documentation, API references, format specifications, and migration guides.
3. Official release notes, changelogs, issue/PR history, security advisories, tests, and example projects.
4. Reproducible execution in our own target environment.
5. Maintainer statements and professional case studies with disclosed conditions.
6. Independent technical evaluations and community reports.
7. Search snippets, star counts, social posts, and marketing pages (discovery hints only).

## Candidate evaluation rubric

Evaluate candidates against the following, recording evidence and confidence rather than relying on a single arbitrary weighted score:

- Capability coverage and output depth.
- Quality ceiling for the exact task, not generic reputation.
- Native integration and API completeness.
- Reliability, error handling, undo/transaction behavior, and recovery.
- Security posture and permission granularity.
- Version compatibility and platform coverage.
- License, patent, redistribution, and generated-output terms.
- Release activity, maintainer response, test quality, and dependency health.
- Performance, RAM/VRAM/disk needs, batch throughput, and automation support.
- Offline/local operation and cost.
- Format fidelity, round-trip behavior, and interchange standards.
- Observability, deterministic reproduction, and evidence hooks.

## Reproduction protocol

1. Pin immutable revision and download from upstream.
2. Inspect license, package/dependency manifests, install scripts, postinstall hooks, permissions, network behavior, and executable entrypoints.
3. Build/install in disposable environment. Record OS, app/runtime version, GPU driver, dependency graph, and commands.
4. Run upstream tests and representative task suite.
5. Test negative cases: invalid inputs, app unavailable, timeout, cancellation, concurrent sessions, corrupt files, permission denial, and crash/restart.
6. Measure outputs against golden references and domain-specific craft criteria.
7. Inspect generated output in native application and consuming target.
8. Record result, logs, screenshots/renders, artifact checksums, known limitations, and recommendation.

## Confidence labels

- **High:** upstream source + repeatable local validation + independent evidence.
- **Medium:** official docs/source reviewed, but target environment execution incomplete.
- **Low:** discovery listing or marketing claims without enough technical corroboration.
- **Unknown:** insufficient evidence.

## Decision record format

Each decision includes problem/outcome, candidates, evidence, pinned versions, license/security implications, environment, tests, measured results, recommendation, alternatives rejected, confidence, unresolved risks, owner, review date, and reevaluation trigger.

## Anti-patterns

- Copying tool counts as quality evidence.
- Equating GitHub stars with professional maturity.
- Assuming all plugins in a catalog share the same support level.
- Treating a paper or demo as production software.
- Taking license names from third-party lists without reading upstream license files.
- Adopting an agent framework before defining workflow durability and tool contracts.
- Creating a homegrown replacement when mature technology can be integrated safely.
