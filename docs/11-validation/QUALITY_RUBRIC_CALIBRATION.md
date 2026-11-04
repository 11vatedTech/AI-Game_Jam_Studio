# Quality Rubric Calibration

## Goal

Build calibrated, discipline-aware evaluation rather than relying on a single LLM score or generic image similarity metric.

## Calibration process

1. Define defect taxonomy and quality dimensions for an artifact class.
2. Collect representative accepted and failed examples with rights/provenance.
3. Have qualified reviewers label criteria and defect locations.
4. Measure reviewer agreement and resolve rubric ambiguity.
5. Evaluate automated metrics/models against human labels on held-out examples.
6. Measure precision, recall, false-positive and false-negative rates by defect severity.
7. Set thresholds appropriate to release risk; severe defects prioritize recall.
8. Recalibrate when tools, models, renderers, formats or content distributions change.

## Separate evaluation axes

Technical correctness, functional behavior, craft quality, consistency, accessibility, performance and compliance remain separate. A high score in one dimension cannot compensate for a critical failure in another.

## Human-review policy

High-impact creative output should receive human review until there is evidence that automated review is calibrated for the relevant artifact type and context. Preserve reviewer examples and feedback as a controlled benchmark dataset, respecting privacy and licenses.
