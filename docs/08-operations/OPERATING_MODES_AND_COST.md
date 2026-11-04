# Operating Modes, Cost, and Local-First Policy

## Operating modes

- **Offline local:** no external network required; only locally installed applications/models/assets.
- **Local with controlled research:** local production with explicit online research/source retrieval.
- **Optional hosted acceleration:** user-authorized hosted model/API or remote render capability.
- **Hybrid professional:** local project control with selected commercial applications/services.

Every capability declares which modes it supports. A baseline workflow must not depend on a hidden cloud endpoint or subscription.

## Cost classification

Tag every application/model/API/plugin as: free/open-source; free but restricted; freemium; paid one-time; subscription; usage-based cloud; enterprise/licensed; or unknown. Identify what data leaves the machine and whether a paid tier is required for the claimed feature.

## Cost controls

- Default to local/free path where it meets quality.
- Make paid cloud calls opt-in and disclose expected billing dimension before execution.
- Do not activate a subscription or purchase without explicit approval.
- Track actual usage when possible; use quotas and caps.
- Provide equivalent alternatives and clearly state the quality/performance tradeoff.

## Local-first does not mean local-at-any-cost

If a local model cannot meet the task quality or hardware constraints, explain the measurable gap and provide a higher-quality optional path. Do not pretend a weak local path is equivalent to a proven professional tool. The user chooses whether to accept cost, time, or quality tradeoffs.
