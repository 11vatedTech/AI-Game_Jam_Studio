# Critic benchmark — first measurement

**Date:** 2026-11-05
**Contract:** `Games/emberkeep/art_direction.json` sha256 `4d594759629c9e7edf04d5a21db31b2658a108b155cb1f67c789a2d4b76ac43c`
**Machine:** Windows 11 26200, Intel i9-class (24 logical CPUs), 31.4 GB RAM, Python 3.12.10, numpy 2.5.4, scikit-image 0.26.0, Pillow 13.0.0
**Measured scope:** file read → PNG decode → every metric → report JSON written to disk. Report serialization is inside the timing.

## Result

| Set | Frames | Median | p95 | p99 | Max | Gate (p95 ≤ 3000 ms) |
|---|---|---|---|---|---|---|
| Real captures, 1280×720 | 4 | 445 ms | 495 ms | 1538 ms | 1538 ms | PASS |
| 1080p probe, 1920×1080 | 4 | 732 ms | 1164 ms | 2150 ms | 2150 ms | PASS |

Cold start (separate process, imports included): **4001 ms** for the four-frame set, roughly 1000 ms per frame. Cold is paid once per production run, not per frame; it is recorded here so it is not mistaken for warm performance.

## What this proves, and what it does not

It proves the rung-2 stack (numpy + scikit-image + Pillow) meets the declared 3 s per-frame budget at 1080p under a warm interpreter. **No C++ component is justified by this evidence**, so none was written. That is the correct outcome of the escalation ladder, not a missed opportunity.

It does **not** prove performance on real 1080p captures. The 1080p set is the four real 720p frames upscaled with Lanczos purely to scale pixel count for timing. Real 1080p captures arrive with the P4 capture contract; this benchmark must be re-run on them before acceptance.

The four-frame set is also far below the planned 24 frames, so the p99 and max figures are weak estimates. The 1538 ms and 2150 ms outliers are first-iteration effects in a fresh process, not a repeated tail.

## Profile (where the time goes, 1080p)

| Stage | ms |
|---|---|
| `delta_e_max` (palette drift, k-means + CIEDE2000) | 204 |
| `warm_share` (HSV classification over world mask) | 421 |
| `luminance_floor` (sRGB→linear + percentiles) | 350 |
| `clutter` (Sobel edge density) | 86 |
| decode | 33 |

`warm_share` and `luminance_floor` are both dominated by full-resolution float conversion that is currently float64. A float32 path is the obvious next optimization if the budget tightens; it is not needed yet, and optimising before a real 1080p measurement would be guessing.

## Reproduction

```
.venv/Scripts/python.exe scripts/quality/critic_bench.py --warm 8
.venv/Scripts/python.exe scripts/quality/critic_bench.py --frames reports/evidence/_staging/bench1080 --warm 8 --output reports/evidence/_staging/bench1080.json
```
