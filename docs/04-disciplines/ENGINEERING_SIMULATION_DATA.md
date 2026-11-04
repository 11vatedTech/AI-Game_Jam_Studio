# Software Engineering, Simulation, Data, and Scientific Computing

## Scope

Requirements, systems architecture, code, APIs, databases, security, automation, debugging, profiling, tests, build tools, CI/CD, infrastructure, data engineering, scientific computing, numerical methods, simulation, visualization and technical reports.

## Engineering doctrine

- Use appropriate language/runtime for the application and environment; C++ and Python are preferred where they offer clear advantages, not imposed universally.
- Inspect the existing codebase and toolchain before modifying it.
- Prefer maintained libraries and standards; do not hand-roll cryptography, parsers, protocol stacks, physics engines, or build tools without demonstrated need.
- Use explicit state ownership, RAII/resource lifetime, typed interfaces, error handling, structured logs, reproducible builds and test coverage.
- Avoid global mutable state, hidden dependencies, hardcoded business logic and unbounded dynamic execution.
- Validate inputs at boundaries and treat file formats, tool outputs and external content as untrusted.

## Software delivery pipeline

Requirement → architecture/ADR → implementation → static analysis → unit tests → integration tests → fuzz/property tests where appropriate → build → runtime/e2e tests → security review → profiling → package → clean environment verification → release report.

## Scientific/technical outputs

Record units, assumptions, data source, code version, solver/model parameters, numerical precision, uncertainty, convergence criteria, validation dataset and reproducibility instructions. A plausible-looking plot is not proof of numerical correctness. Use reference solutions, conservation checks, sensitivity analysis, dimensional analysis and uncertainty bounds as appropriate.
