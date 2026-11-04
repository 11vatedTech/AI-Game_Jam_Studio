# ADR-0001: Local, Provider-Neutral Runtime Foundation

- **Status:** Accepted for developer foundation; reassess at production scale.
- **Date:** 2026-11-04

## Context

The studio needs local persistence, predictable tool contracts, durable task records, evidence and permissions while Freebuff remains the reasoning coordinator. The system must work without mandatory API keys or paid hosted dependencies and fit a Windows workstation with limited shared VRAM.

## Decision

Use Python 3.11+ and the standard library for the first local control-plane runtime; SQLite for embedded state; MCP stdio as one agent integration interface; native application APIs/CLIs for tool control; and an optional OpenAI-compatible local model client. Avoid adding mandatory third-party runtime dependencies until a measured requirement exists.

## Rationale

- Python has broad native application automation support (notably Blender and creative tooling).
- SQLite provides durable local transactional state without a separate server.
- MCP allows Freebuff and other compatible hosts to discover typed capabilities without coupling the product to one agent.
- The local runtime does not attempt to replace Freebuff's reasoning or a mature workflow engine before workload measurements justify that complexity.
- Local execution, explicit resource admission and optional local inference align with privacy/cost constraints.

## Consequences

- The first executor is sequential and local. Production concurrency, scheduling, cancellation, crash recovery and distributed work require later evidence and design.
- SQLite migration/backup/restore discipline is mandatory before external production deployment.
- Python is not the high-performance engine for every subsystem; native C++/Rust/engine plugins remain appropriate when profiling proves a need.
- MCP is transport/integration, not the security boundary by itself.
