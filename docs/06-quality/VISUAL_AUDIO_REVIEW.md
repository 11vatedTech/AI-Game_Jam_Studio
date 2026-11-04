# Visual and Audio Review Protocol

## Visual review stages

1. **Brief adherence:** compare output with requirements, style bible and reference intent.
2. **Thumbnail/readability:** inspect at target display size; focal hierarchy and silhouette must work.
3. **Craft detail:** inspect topology, edge quality, texture, material, light, typography, animation or motion as applicable.
4. **Context:** view inside target scene/game/UI/video/cad assembly.
5. **Temporal review:** play animation/video/effect at normal speed and frame-by-frame on problem frames.
6. **Regression:** compare approved golden views after revisions.
7. **Independent review:** separate reviewer records defects, severity, and approval rationale.

## Capture conditions

Record application version, renderer, resolution, aspect ratio, camera, frame/time, color management, lighting, quality settings, GPU/driver, seed, and relevant scene state. Golden comparisons must control or normalize nondeterministic factors.

## Visual metrics

Possible quantitative signals include image similarity, structural similarity, perceptual embeddings, edge/silhouette overlap, OCR/typography checks, color histograms, segmentation, temporal consistency, object/pose detection, and human preference. No one metric determines quality. Metrics should be selected for the specific defect and calibrated against annotated examples.

## Audio review

Listen to original and output under known conditions. Capture loudness, peak/true peak, clipping, DC offset, silence, duration, sample rate, channels, loop seams, phase, noise and codec metadata. Use speech intelligibility/transcription or model metrics only as auxiliary checks. Musical/creative quality needs domain review for arrangement, timbre, mix, emotional fit, structure and originality.

## Evidence outputs

Side-by-side/overlay captures, contact sheets, turntables, waveform/spectrograms, audio exports, reviewer notes, metric report, defect list, approval state, and source artifact IDs.
