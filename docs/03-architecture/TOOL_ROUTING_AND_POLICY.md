# Tool Routing, Selection, and Policy Enforcement

## Routing is a decision, not a hardcoded preference

Choose tools by task fit, verified support, output quality, permissions, context availability, resource requirements, cost and recoverability. A familiar tool is not automatically the best tool.

## Selection sequence

1. Parse task and target artifact.
2. Load applicable discipline Skill and quality rubric.
3. Discover certified capabilities.
4. Filter by application version, OS, format, license, permissions and resources.
5. Compare alternatives by quality ceiling and actual benchmark evidence.
6. Select workflow and define fallbacks.
7. Reserve resources and lock conflicting project state.
8. Execute only within granted permissions.
9. Inspect postconditions and attach evidence.
10. Update confidence/maturity only after validation—not after a single success.

## Policy enforcement outside the model

The model may propose tool calls. A deterministic policy layer must validate identity, schema, permission, path, operation class, resource budget, network target, payload size and approval requirements before execution. Do not rely on prompt instructions alone to enforce permissions.

## Fallback policy

Fallbacks must preserve the acceptance criteria. A CPU-only or lower-resolution path is acceptable only if the required quality and output constraints still pass. If not, report the blocker rather than silently lower quality. A GUI automation fallback is permitted only when stable APIs are unavailable and the interaction is observable, scoped, and tested.
