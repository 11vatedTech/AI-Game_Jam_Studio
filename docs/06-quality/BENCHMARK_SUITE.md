# Benchmark Suite and Competitive Evaluation

## Why benchmark

The studio must demonstrate measurable advantage over reference systems. The benchmark compares complete outcomes, not marketing pages or tool counts.

## Benchmark dimensions

- Brief understanding and missing-requirement discovery.
- Planning quality and correct tool selection.
- Output craft and design distinctiveness.
- Functional/technical correctness.
- Cross-application interoperability.
- Number/severity of defects after first pass.
- Repair success and regression rate.
- Human intervention and approval load.
- End-to-end duration and compute/resource cost.
- Failure recovery and reproducibility.
- License/provenance completeness.

## Golden benchmark categories

1. Game engine task: create, integrate, play, repair, package.
2. 3D character: concept-to-rigged-engine asset with animation and evidence.
3. Environment: coherent modular level with materials, lighting, collision and runtime performance.
4. 2D art system: character sheet, sprites, animation, atlas and style consistency.
5. UI/product task: design tokens, responsive UI, working app, accessibility and visual regression.
6. Audio task: SFX/music/dialogue package integrated in engine with metadata and clean mix.
7. Video task: storyboard/shot assembly, timeline, effects, audio, grade and export QC.
8. CAD/technical task: parametric model/assembly, constraints, drawings and exchange validation.
9. Software task: repo understanding, architecture, implementation, tests, security and release packaging.
10. Multi-discipline task: a coherent product that spans at least three domains.

## Comparative protocol

Use the same brief, target environment, reference inputs, acceptance criteria, and compute budget for AI Game Dev, other candidate products, and our studio. Record tool versions, model versions, human interventions, retries, output files, test results, artifact hashes, and reviewer decisions. Blind review visual/audio output where possible. Do not compare a paid cloud model's best output against a constrained local model without disclosing resource differences.

## Key metrics

- Mandatory acceptance pass rate.
- First-pass acceptance rate.
- Defect density and severity distribution.
- Repair loop success rate.
- Regression introduction rate.
- Task completion/recovery rate.
- Human minutes per accepted deliverable.
- Time-to-first-valid and time-to-accepted.
- Cost/resource per accepted result.
- Reproduction success rate.
- Cross-app round-trip fidelity.

Targets must be established from baseline measurements. The non-negotiable certification rule remains 100% pass of mandatory acceptance items in the declared test suite.
