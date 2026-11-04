# Intent Understanding and Routing

## Input model

Convert a request into a structured intent object with:

- User outcome and audience.
- Deliverable classes and target formats.
- Functional/technical requirements.
- Style and craft requirements, references, anti-references, art direction.
- Target applications, platforms, devices, or deployment environment.
- Resource, time, licensing, privacy, cost, and offline constraints.
- Existing files/projects that must be preserved or extended.
- Unknowns, assumptions, confidence, and questions that materially affect the outcome.

## Routing rules

1. Identify the primary deliverable, not only the words used by the user. “Make a game character” may require concept design, modeling, topology, UVs, materials, rigging, animation, engine import, and runtime testing.
2. Determine required craft disciplines and dependencies.
3. Search the capability registry for certified capabilities first; then qualified but uncertified candidates; then research new candidates.
4. Compare tool suitability, quality ceiling, installed versions, permissions, resource load, file formats, round-trip fidelity, and user preferences.
5. Select the narrowest workflow that can meet the target; do not invoke irrelevant tools or create needless agents.
6. Build an explicit dependency graph. Parallelize independent work only when resource constraints and artifact contracts permit.
7. Route quality review to appropriate specialists/reviewers.
8. Maintain traceability from original intent to every important artifact and acceptance result.

## Human questions

Ask only when the answer materially changes the design, licensing, target platform, audience, irreversible operation, privacy exposure, or delivery format. Otherwise state an assumption and continue. Never ask for information already available in the active project state.

## Routing output

Every task plan must identify: chosen toolchain, rejected alternatives and why, prerequisites, estimated resource class, permission level, milestones, artifacts, acceptance tests, failure-recovery path, and evidence outputs.
