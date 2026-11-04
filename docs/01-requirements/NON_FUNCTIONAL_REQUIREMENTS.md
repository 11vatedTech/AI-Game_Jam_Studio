# Non-Functional Requirements

## Reliability and recoverability

- All long-running actions expose state, progress, cancellation, and timeout behavior.
- Jobs checkpoint at safe boundaries; retries do not duplicate irreversible work.
- Tool crashes and model failures are isolated from the coordinator where practical.
- Recovery must state which artifacts are committed, temporary, or uncertain.

## Performance

- Measure planning latency, tool latency, artifact throughput, render duration, queue wait, GPU/VRAM/RAM, disk IO, and end-to-end task duration.
- Resource admission control must prevent jobs from overcommitting host memory or GPU memory based on estimates alone.
- Low-memory operation must be a supported execution mode where tools permit it.
- Performance targets are defined per task class and hardware support matrix, not as an arbitrary global number.

## Maintainability

- Modular boundaries, typed interfaces, dependency injection, versioned schemas, tests, structured logs, and ADRs are mandatory.
- Prefer mature language/runtime ecosystems already used by the integrated application rather than forcing one implementation language across every adapter.
- Avoid global mutable state and hidden side effects.

## Portability

- Windows 11 is the first-class development target, but architecture must not make other platforms impossible.
- Use path normalization, explicit environment detection, process isolation, and compatibility tests.
- Declare any Windows-only capabilities honestly.

## Security and privacy

- Least privilege, workspace containment, secret isolation, dependency review, network policy, user approval for destructive actions, and audit logs are mandatory.
- User project contents and reference media remain local by default.

## Usability

- The user must be able to inspect plans, see progress, review visual outputs, approve consequential operations, and understand failures.
- Progress reporting must reflect actual states and cannot imply that background work is happening when it is not.

## Reproducibility

- Pin application/plugin/model/workflow versions where feasible.
- Capture seeds, model hashes, sampler/scheduler, prompts, control inputs, render settings, environment, and build options where applicable.
- Reproduction instructions must state nondeterministic components and expected tolerance.
