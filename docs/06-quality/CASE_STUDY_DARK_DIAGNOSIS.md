# Case study: a critic that described a symptom and called it a cause

**Date:** 2026-11-05
**Production:** Emberkeep
**Artifacts:** `reports/evidence/productions/emberkeep/02-manufacture/`
**Code:** `src/elevenvt_studio/quality/metrics.py` (`luminance_cause`, `lum-cause-2`)

This is the record of a quality-system failure, its correction, and the rules extracted from it. It is kept because the failure was not a bad measurement. Every measurement below was correct. The failure was a *confident explanation* built on top of correct measurements, by both a human-directed agent and the human reviewing it.

## 1. What happened

The Emberkeep arrival frame failed `luminance_floor` at p5 = 0.00163 against a floor of 0.015. The critic reported the failure and described the pixels: a dead-black lower third, dark share 0.78–0.99 across bands, band p5 between 0.0015 and 0.0042.

That description is consistent with at least three different defects:

- geometry absent (the camera sees past the world),
- geometry present but not lit,
- geometry present and lit but with no albedo or detail.

The critic named none of them, and the report implied the first two.

## 2. The wrong cause, and why it was persuasive

The first explanation offered was: the water plane sat below the terrace slab at y = -1.25, never rendered, and the camera looked past the world edge into the sky's ground hemisphere. The lower quarter of the frame was therefore background.

It was persuasive for three reasons, none of which was evidence about coverage:

1. It fit the pixels — a near-constant very dark value looks like unrendered background.
2. The geometry share in the visible mask rose monotonically from 0.756 to 1.000 down the frame, which appeared to confirm that the world ended partway down.
3. Nothing in the evidence could contradict it. There was no coverage measurement, so both the hypothesis and its negation produced identical data.

It was recorded in `PROJECT_STATUS.md` and in the commit message of `07a8e83` as established fact, and repeated by the human reviewer as fact.

## 3. The experiment that disproved it

Two independent measurements, both cheap:

**Plane extent.** The failing build already contained `plane.size = Vector2(260, 260)` at y = -1.25 — in `254ded1`, not in the fix. The water plane was 260 units across from the beginning.

**Background counterfactual.** Render the failing scene with `background_mode = BG_COLOR` and `background_color = magenta`, then count pixels with (r > 200 & g < 60 & b > 200). A frame with any background visible would light up. The count was **0.000** of the frame, in all eight bands. There was no background in the view at all.

**Coverage pass.** A new render against a background colour the palette cannot produce reported rendered surface at **1.000** of every band.

The dark lower third was water that was present, unlit in appearance, and visually flat. Not absent.

## 4. The second-order failure

The new diagnostic — the one written to prevent exactly this — produced `unlit_flat_surface` at 0.90 confidence on its first run against the failing capture. That output was correct in its first half and wrong in its second, and it was dismissed in favour of the narrative that had already been written.

`unlit` is an illumination claim. It was derived from a local standard-deviation measurement. Low variance is evidence of low detail; it says nothing about whether light reaches the surface. A smooth water surface can be intentionally dark; flat stone can be well lit. The metric had smuggled a cause into a measurement, which is the same error one level down.

The same agent produced both errors within a single session: first a cause from a narrative, then a cause from a proxy.

## 5. What was changed

**The diagnosis was split into independent dimensions**, because they fail independently:

| Dimension | Question | Evidence required |
|---|---|---|
| coverage | Is a rendered surface at this pixel? | a `scene_coverage` mask |
| surface detail | Does the region carry readable variation? | local pixel variance |
| illumination response | Does scene light reach this surface? | a lights-off control at identical exposure |

`luminance_cause` (`lum-cause-2`) reports each dimension separately and composes a kind only from what was measured: `missing_coverage`, `dark_sky`, `dark_low_detail_surface`, `dark_detailed_surface`, `underlit_surface`, `no_darkness`, or `undetermined`. Its `confidence` field is a claim grade (`measured` / `undetermined`), not a probability. Without a control capture, illumination is always `undetermined` and the report says the diagnosis describes the surface, not the lighting rig.

**Coverage became its own role.** `mask_world_visible` cannot answer "is anything there": the visible mask selected 97–100% of the frame because the segmentation includes everything drawn at depth. A new role, `mask_world_occupancy` with semantics `scene_coverage`, renders the scene against a colour the palette cannot produce. The bundle schema now enumerates semantics per role, so a mask cannot silently mean two things.

**Every metric now discloses its arithmetic.** Each finding carries numerator, denominator, denominator semantics, included and excluded regions, hashes of the frame and every mask read, the threshold, the contract revision, and an `assertion` of `measurement` or `inference`. A metric that could not run states why instead of looking like a zero.

**Superseded evidence is archived, not deleted.** `captures/superseded/SUPERSEDED.json` holds each replaced capture with its frame hash, the reason, and what replaced it. The failing first capture `e183e1d3` is preserved specifically because it is the ground truth for this correction.

## 6. What the record now says, and what it does not

Against the passing frame, the critic reports: coverage `present`, surface detail `low_variance`, illumination response `undetermined`, diagnosis `dark_low_detail_surface`, claim grade `measured`.

It does **not** report that the water was underlit, because that was never measured. The lighting fix changed water albedo, ripple normals, ambient, moon and exposure together; the improvement cannot be attributed between material and lighting from that evidence. A lights-off control capture at identical exposure is required, and the capture service does not offer one yet.

## 7. Claims, classified

| Claim | Status |
|---|---|
| Final water shader is repeatable | Demonstrated — three captures, identical digest `29c70bf4ce02a091`, `exact_sha256` |
| Water was absent from the original view | **Disproved** — plane spanned 260 × 260; zero background pixels in a magenta render |
| Original water was present, dark and featureless | Supported — coverage 1.000, 81% of below-floor pixels detail-free |
| The world mask measured meaningful coverage | **Disproved** — it selects 97–100% of the frame |
| The occupancy pass measures rendered surface coverage | Experimentally supported, cross-checked against an independent render |
| The diagnostic separates tested dark-surface and missing-coverage cases | Tested — `tests/test_critic_spatial.py` |
| The diagnostic is reliable across arbitrary scenes | **Not established** |
| The original frame was underlit | **Not established** — no control capture |

## 8. Rules extracted

1. **A metric may not claim a cause more strongly than its evidence permits.** Every inferred cause must name the evidence that would falsify it, and say `undetermined` when that evidence is absent.
2. **Keep measurement and diagnosis in separate fields.** A measured number and a causal claim fail differently and must not look alike in a report.
3. **Measure each dimension with its own instrument.** Coverage, detail and illumination were one number and should never have been.
4. **A failed hypothesis is evidence.** Record it with its artifact hashes and supersede it; deleting it destroys the only proof that the reasoning changed.
5. **A mask is not a claim until its semantics are typed.** "Surface visible" and "surface present" are different assertions, and a mask named for one cannot stand for the other.
6. **Disclose the arithmetic.** A ratio without numerator, denominator, sources and contract version cannot be challenged, only believed.

## 9. Reproduction

```
PYTHONPATH=src .venv/Scripts/python.exe scripts/perception/emberkeep_capture.py
PYTHONPATH=src .venv/Scripts/python.exe -m pytest -q tests/test_critic_spatial.py
```

The failing capture and the counterfactual conclusion are checkable from `captures/superseded/e183e1d3-.../` plus a `BG_COLOR` magenta render of the same scene at the same commit.
