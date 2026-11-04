# Agent Runtime and Workflow Framework Evaluation

No single framework should automatically own every concern. Separate model reasoning, tool access, workflow durability, application control, memory, and observability.

## Responsibilities to separate

- **Agent harness:** prompt/context construction, model selection, tool selection, turn loop, handoffs, output validation.
- **Workflow engine:** long-running orchestration, retries, durable state, timers, task dependencies, cancellation, replay.
- **Tool protocol:** schema and transport for invoking tools (MCP, HTTP, SDK, CLI, native plugin).
- **Application adapter:** safe app-specific operations and state inspection.
- **Project memory:** durable decisions, requirements, artifact metadata, user-approved preferences, validated recipes.
- **Observability:** traces, events, token/tool costs, process/resource metrics, failures, evidence.

## Candidates to compare

| Candidate | Likely strength | Risk / question |
|---|---|---|
| LangGraph | Stateful graph-based agent execution and human-in-loop workflows | Does it provide the operational durability and restart semantics required, or does a separate workflow engine remain necessary? |
| Temporal | Durable execution for long-running jobs and retries | More operational infrastructure; keep agent cognition outside the workflow engine where appropriate |
| Microsoft Agent Framework | Agent framework with .NET/Python options | Check stability/version status, cross-provider support, deployment requirements |
| CrewAI | Role-oriented task orchestration | Beware excessive multi-agent chatter, weak artifact contracts, and hidden retries |
| LlamaIndex Workflows | Event-driven workflow composition, especially data/retrieval | Determine fit for DCC/engine stateful tasks |
| OpenAI Agents SDK | Tool/handoff/tracing features | Treat as one provider-specific option behind the agent interface |
| Plain explicit state machine | Small reliable workflow control where complexity is bounded | Do not hand-roll durability if mature engines satisfy requirements |

## Decision experiment

Build an apples-to-apples benchmark: a workflow with dependent and parallel tasks, a 10-minute external operation, forced process crash, cancellation, timeout, human approval, replay, state migration, and a tool that returns an ambiguous/partial result. Measure correctness, recovery, developer friction, observability, versioning, and operational cost. Choose the minimum combination that satisfies requirements.

## Default hypothesis (not locked)

Keep Freebuff or a thin agent harness as the cognitive coordinator; use typed application adapters and capability discovery; evaluate LangGraph for agent/task reasoning and Temporal for durable production jobs only if measured requirements justify both. Avoid two overlapping orchestrators unless their boundary is clear. MCP is an interoperable tool protocol, not a workflow engine or an authorization system by itself.
