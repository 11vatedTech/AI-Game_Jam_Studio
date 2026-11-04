# Product Requirements

The product is a local-first, provider-neutral agentic studio. Requirements below are normative. `MUST` is mandatory for certification; `SHOULD` is expected unless a documented exception is approved; `MAY` is optional.

## Intent and planning

- PR-INT-001 MUST accept incomplete natural-language intent and attached reference material.
- PR-INT-002 MUST extract outcomes, users, constraints, style, target medium, platform, quality level, deadlines, dependencies, and uncertainties.
- PR-INT-003 MUST identify hidden requirements and propose improvements without silently changing the user's core intent.
- PR-INT-004 MUST produce a traceable brief, assumption register, and acceptance matrix before consequential production.
- PR-INT-005 SHOULD offer alternative directions with tradeoffs when meaningful.

## Intelligence and orchestration

- PR-AGT-001 MUST support provider-neutral model/agent interfaces.
- PR-AGT-002 MUST route tasks to specialist skills and suitable tools based on declared capability and measured outcomes.
- PR-AGT-003 MUST support long-running jobs, checkpoint/resume, cancellation, retries, idempotency, and failure recovery.
- PR-AGT-004 MUST preserve project context, approved decisions, and artifact lineage across sessions.
- PR-AGT-005 SHOULD use multi-agent collaboration only when it improves quality or parallel throughput; role proliferation is not a goal.

## Tool and application integration

- PR-INTG-001 MUST discover capabilities at runtime and expose version/health/support metadata.
- PR-INTG-002 MUST support native API, CLI, SDK, scripting, MCP, plugin, file interchange, and workflow-server integration where appropriate.
- PR-INTG-003 MUST use the application's authoritative main-thread/editor APIs for operations requiring them.
- PR-INTG-004 MUST support transaction boundaries, postconditions, and undo/rollback where possible.
- PR-INTG-005 MUST expose application logs, runtime output, screenshots/renders, and test state to the evaluating agent.

## Production

- PR-PROD-001 MUST create genuine editable artifacts in required native/interchange formats.
- PR-PROD-002 MUST enforce pipeline-specific preconditions and postconditions.
- PR-PROD-003 MUST support coherent cross-discipline project assembly.
- PR-PROD-004 MUST retain source files, production settings, exports, and provenance when required.
- PR-PROD-005 MUST distinguish blockout, prototype, beta, and final assets.

## Quality and trust

- PR-QA-001 MUST associate every completion claim with acceptance criteria and evidence.
- PR-QA-002 MUST separate technical correctness, integration, functional behavior, craft quality, performance, accessibility, and compliance.
- PR-QA-003 MUST prevent release when mandatory criteria fail.
- PR-QA-004 MUST retain failures and test history; no silent deletion of negative evidence.
- PR-QA-005 MUST expose uncertainty, unsupported environments, and untested criteria.

## Operations and extensibility

- PR-OPS-001 MUST run without mandatory paid API keys or hosted subscriptions for baseline workflows.
- PR-OPS-002 SHOULD prioritize local inference and local applications when quality and performance are acceptable.
- PR-OPS-003 MUST detect actual host resources and schedule accordingly.
- PR-EXT-001 MUST permit third-party extensions with capability schemas, permissions, versioning, tests, and uninstall paths.
- PR-EXT-002 MUST preserve provider/tool neutrality and avoid hard-wiring a single LLM vendor into domain adapters.
