# Quality Evaluation and Calibration

## Why model critique alone is insufficient

A vision or audio model can identify some defects, but its score is not automatically correlated with expert judgments or audience outcomes. It may miss structural issues, overvalue polish, penalize intentional style, or be sensitive to prompts and image scale.

## Calibration protocol
1. Assemble a rights-cleared benchmark set across genres, styles, output sizes and difficulty levels.
2. Include expert-approved examples, borderline examples, and deliberately injected defect examples.
3. Have at least two qualified reviewers independently label each relevant criterion; adjudicate disagreements and document uncertainty.
4. Define criterion-level anchors (e.g., silhouette readability at target gameplay scale; texture stretch; contact correctness; UI hierarchy and legibility), not only global "looks good" scores.
5. Evaluate automated reviewers for precision, recall, false-positive rate, false-negative rate and agreement with the adjudicated labels.
6. Test on held-out styles and tasks. Do not tune and validate on the same examples.
7. Use model output to suggest defects and repair hypotheses. Deterministic validators and expert review own acceptance until the model is sufficiently reliable.
8. Record evaluator/model version, prompt, input resolution, preprocessing, rubric, thresholds and benchmark data revision.
9. Recalibrate after model, workflow, engine, renderer, capture pipeline or rubric changes.

## Gate behavior

P0/P1 failures block certification. A weighted average cannot compensate for a critical defect. Any waived noncritical requirement must identify approver, reason, scope, expiry and residual risk. Unknown/NOT_RUN is not PASS.
