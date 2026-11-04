# Commercial-Quality and Productization Gate

A serious commercial asset is not proven by code size, agent autonomy claims, a large tools catalog, a high-quality concept render, or a projected valuation. It is established by real customer outcomes, reliable delivery, rights-cleared assets, documented support, security, maintainability, repeatable economics and independently observable quality.

## Product-grade requirements

- Clear supported use cases and documented unsupported cases.
- Reproducible setup on declared OS/hardware/application matrices.
- Stable versioned interfaces and migrations.
- Backward compatibility policy for workflows and artifacts.
- No secret leakage; defined threat model and patch process.
- Dependency/license/SBOM and model/data provenance records.
- Crash recovery, backups, audit and user data retention policy.
- Deterministic behavior where possible; traceable nondeterminism where not.
- Reliable cancellation, timeouts, retries, concurrency locks and compensation.
- Meaningful monitoring and actionable diagnostics.
- Benchmark dataset with rights-cleared inputs and objective expected outputs.
- Human review where quality cannot be objectively determined.
- Clear installation, operator, developer, and troubleshooting documentation.
- Commercial-rights review for code, models, datasets, fonts, textures, audio, code plugins and redistribution.

## Evidence required before a business-value assertion

Do not claim a multi-million-dollar valuation or product value based on a repo. A serious business case needs evidence of sustained customer demand, user retention, revenue or validated willingness-to-pay, cost-to-serve, differentiated performance, IP/rights clarity, operational maturity, defensible distribution and a realistic market. This repository is an engineering asset foundation, not a valuation.

## Release tiers

- **Developer Preview:** can be installed and operated by maintainers; no commercial reliability guarantee.
- **Private Beta:** defined support matrix, user feedback loop, telemetry/privacy controls, security response and known limitation list.
- **Production Candidate:** release-blocking tests, backups/recovery, documented upgrades, vulnerability and license review, performance benchmarks and support process.
- **Production Certified:** exact support matrix passes every mandatory release test; zero unresolved P0/P1; verified evidence; approved rights and security; rollback and incident procedures.

Do not market a lower tier as a higher tier.
