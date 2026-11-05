"""The critic must say what it measured, how well, and whether it explained anything.

The Emberkeep failure proved the gap: a global p5 named a defect and described it as
"a dead-black lower third", which is equally consistent with unlit geometry, absent
geometry, and a bad exposure. These tests pin each dimension apart — coverage, surface
variation, illumination — keep measurement status separate from the inferred diagnosis,
and refuse a claim when an input that a dimension needs was never captured.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from elevenvt_studio.perception import bundle
from elevenvt_studio.quality import art_direction, critic, metrics

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "Games/emberkeep/art_direction.json"

DARK = 5
LIT = 90
WARM = (204, 122, 41)


def _frame(
    *,
    background_rows: int = 0,
    surface: str | None = None,
    height: int = 200,
    width: int = 200,
):
    """A lit top half over a dark bottom half, plus the coverage mask describing it."""
    rgb = np.zeros((height, width, 3), dtype=np.uint8)
    rgb[: height // 2] = LIT
    rgb[height // 2 :] = DARK
    dark = rgb[height // 2 :]

    if surface == "noise":
        dark[:] = np.random.default_rng(7).integers(0, 30, size=(height // 2, width))[..., None]
    elif surface == "texture":
        # Mid-frequency structure: visible at 8px and still present at 32px.
        cols = np.arange(width) // 24
        rows = np.arange(height // 2) // 24
        checker = ((cols[None, :] + rows[:, None]) % 2) * 24
        dark[:] = (DARK + checker)[..., None]
    elif surface == "gradient":
        # Smooth, deliberate: low variation everywhere despite spanning the frame.
        ramp = np.linspace(DARK, DARK + 40, width).astype(np.uint8)
        dark[:] = ramp[None, :, None]
    elif surface == "highlight":
        # Smooth surface carrying one specular blob: low variation, clearly intentional.
        dark[:] = DARK
        yy, xx = np.mgrid[0 : height // 2, 0:width]
        blob = np.exp(-(((yy - 50) ** 2 + (xx - 100) ** 2) / (2 * 18.0**2)) * 255)
        dark[:] = (DARK + blob)[..., None].astype(np.uint8)

    occupancy = np.ones((height, width), dtype=bool)
    if background_rows:
        occupancy[height - background_rows :] = False
    return rgb, occupancy


# --- the three dimensions, and the status of each ---------------------------


def test_dark_band_over_nothing_is_missing_coverage():
    rgb, occupancy = _frame(background_rows=100)
    out = metrics.luminance_cause(rgb, occupancy, 0.015)

    assert out.detail["coverage"]["value"] == "absent"
    assert out.detail["coverage"]["evidence_status"] == "measured"
    assert out.detail["coverage"]["assertion_type"] == "measurement"
    assert out.detail["diagnosis"]["value"] == "missing_coverage"
    assert out.detail["diagnosis"]["assertion_type"] == "inference"
    assert out.value == pytest.approx(1.0)


def test_a_hole_in_a_covered_band_is_still_missing_coverage():
    # Band averages would swallow a hole; coverage is counted per pixel.
    rgb, occupancy = _frame()
    occupancy[120:140, 40:80] = False
    out = metrics.luminance_cause(rgb, occupancy, 0.015)

    assert 0.0 < out.value < 0.5
    assert out.detail["coverage"]["value"] == "present"
    assert out.detail["coverage"]["dark_share_without_geometry"] == pytest.approx(out.value)


def test_flat_dark_surface_is_described_by_variation_and_only_that():
    rgb, occupancy = _frame()
    out = metrics.luminance_cause(rgb, occupancy, 0.015)

    assert out.detail["coverage"]["value"] == "present"
    variation = out.detail["surface_variation"]
    assert variation["value"] == "low_variation"
    assert variation["evidence_status"] == "measured"
    assert variation["assertion_type"] == "measurement"
    # The point of the split: a variance measurement never becomes a lighting claim.
    assert out.detail["illumination_response"]["value"] == "undetermined"
    assert out.detail["illumination_response"]["evidence_status"] == "not_measured"
    assert out.detail["diagnosis"]["value"] == "dark_low_variation_surface"
    assert out.detail["diagnosis"]["evidence_status"] == "measured_inputs"
    assert "a surface too dark to light from light that never reaches it" in out.detail[
        "diagnosis"
    ]["cannot_distinguish"]


def test_variation_is_measured_at_several_scales():
    rgb, occupancy = _frame(surface="texture")
    out = metrics.luminance_cause(rgb, occupancy, 0.015)
    variation = out.detail["surface_variation"]

    assert set(variation["scales"]) == {"8", "16", "32"}
    assert variation["value"] == "variation_present"
    assert variation["pattern"] == "structure_larger_than_tiles"
    assert variation["scale_growth"] >= 1.5


def test_fine_structure_alone_is_not_called_detail():
    rgb, occupancy = _frame(surface="noise")
    out = metrics.luminance_cause(rgb, occupancy, 0.015)
    variation = out.detail["surface_variation"]

    # Noise spreads the same amount at every patch size. That is not readable surface
    # detail, and pixels cannot say whether it is texture, noise or a denoiser artefact.
    assert variation["pattern"] == "scale_invariant"
    assert variation["value"] == "undetermined"
    assert out.detail["diagnosis"]["value"] == "undetermined"
    assert out.detail["diagnosis"]["evidence_status"] == "insufficient_inputs"
    assert "noise from very fine texture" in " ".join(
        out.detail["diagnosis"]["cannot_distinguish"]
    )


def test_a_smooth_surface_is_never_scored_for_readability():
    # A smooth ramp carries almost no variation and can be exactly right.
    rgb, occupancy = _frame(surface="gradient")
    out = metrics.luminance_cause(rgb, occupancy, 0.015)
    assert out.detail["surface_variation"]["value"] == "low_variation"
    assert out.detail["surface_variation"]["readability"] == "not_established"

    # A specular highlight is variation the surface is supposed to have. Whatever the
    # measurement says, it stays a measurement, and readability stays unclaimed.
    rgb, occupancy = _frame(surface="highlight")
    out = metrics.luminance_cause(rgb, occupancy, 0.015)
    assert out.detail["surface_variation"]["readability"] == "not_established"
    assert out.detail["diagnosis"]["assertion_type"] == "inference"
    assert "Variation is not readability" in " ".join(out.limitations)


# --- illumination needs a controlled experiment -----------------------------


def test_illumination_is_only_claimed_with_an_all_lights_off_control():
    rgb, occupancy = _frame()

    # Every light disabled changes nothing in that region: the surface gets no light.
    out = metrics.luminance_cause(
        rgb, occupancy, 0.015, illumination_controls={"all": rgb.copy()}
    )
    illumination = out.detail["illumination_response"]
    assert illumination["value"] == "low_contribution"
    assert illumination["evidence_status"] == "measured"
    assert out.detail["diagnosis"]["value"] == "underlit_surface"

    dark_control = rgb.copy()
    dark_control[100:] = 0
    out = metrics.luminance_cause(rgb, occupancy, 0.015, illumination_controls={"all": dark_control})
    assert out.detail["illumination_response"]["value"] == "adequate_contribution"
    assert out.detail["illumination_response"]["contribution"] > 0.9


def test_mechanisms_are_separated_and_adequacy_is_not_claimed():
    rgb, occupancy = _frame()
    no_direct = rgb.copy()
    no_direct[100:] = 0  # all the light comes from the direct rig
    no_environment = rgb.copy()  # ambient contributes nothing
    no_emissive = rgb.copy()

    out = metrics.luminance_cause(
        rgb,
        occupancy,
        0.015,
        illumination_controls={
            "all": rgb.copy(),
            "direct": no_direct,
            "environment": no_environment,
            "emissive": no_emissive,
        },
    )
    mechanisms = out.detail["illumination_response"]["mechanisms"]

    assert mechanisms["direct"]["contribution"] == pytest.approx(1.0)
    assert mechanisms["environment"]["contribution"] == pytest.approx(0.0)
    assert mechanisms["indirect"]["available"] is False
    # Contribution is not adequacy: art direction decides whether the amount is right.
    assert out.detail["illumination_response"]["adequacy"] == "not_established"


def test_mechanism_controls_without_an_all_off_capture_stay_partial():
    rgb, occupancy = _frame()
    no_direct = rgb.copy()
    no_direct[100:] = 0
    out = metrics.luminance_cause(rgb, occupancy, 0.015, illumination_controls={"direct": no_direct})
    illumination = out.detail["illumination_response"]

    assert illumination["evidence_status"] == "partially_measured"
    assert illumination["value"] == "undetermined"
    assert "no all-lights-off capture" in illumination["basis"]


def test_without_a_coverage_mask_no_diagnosis_is_claimed():
    rgb, _ = _frame(background_rows=100)
    out = metrics.luminance_cause(rgb, None, 0.015)

    assert out.value is None
    assert out.detail["coverage"]["value"] == "undetermined"
    assert out.detail["coverage"]["evidence_status"] == "not_measured"
    assert out.detail["diagnosis"]["value"] == "undetermined"
    assert out.detail["diagnosis"]["evidence_status"] == "insufficient_inputs"
    assert out.detail["diagnosis"]["assertion_type"] == "inference"


# --- coverage is not quality ------------------------------------------------


def test_full_coverage_does_not_make_an_unacceptable_frame_acceptable(tmp_path):
    # 100% occupancy, and a frame that is almost entirely below the floor.
    rgb = np.full((200, 200, 3), DARK, dtype=np.uint8)
    occupancy = np.ones((200, 200), dtype=bool)
    frame = tmp_path / "void.png"
    Image.fromarray(rgb).save(frame)
    mask = tmp_path / "void.occupancy.png"
    Image.fromarray((occupancy * 255).astype(np.uint8)).save(mask)

    report = critic.evaluate(
        [critic.Frame(name="void.png", path=frame, occupancy_mask_path=mask)],
        art_direction.load(CONTRACT),
    ).to_dict()

    assert report["status"] == "FAIL"
    floor = next(f for f in report["findings"] if f["metric"] == "luminance_floor")
    assert floor["severity"] == "major"
    cause = floor["detail"]["cause"]
    assert cause["coverage"]["value"] == "present"
    assert cause["diagnosis"]["value"] == "dark_low_variation_surface"


# --- warm share: one measurement, one honest absence ------------------------


def test_warm_share_does_not_duplicate_the_frame_share():
    rgb = np.full((100, 100, 3), 20, dtype=np.uint8)
    rgb[:, :50] = WARM
    band = {"hue_deg": [20, 45], "sat_min": 0.4, "val_min": 0.2}

    # No semantic scene region exists, so the scene question is not measured at all.
    scene = metrics.warm_share(rgb, None, band)
    assert scene.value is None
    assert scene.detail["scope"] == "not_established"
    assert scene.detail["semantic_scope"] == "not_established"
    assert scene.detail["scene_region_mask"] == "unavailable"
    assert scene.detail["equivalent_available_measurement"] == "warm_share_frame"

    # The whole-frame share is stated, and only it.
    of_image = metrics.warm_share_frame(rgb, band)
    assert of_image.value == pytest.approx(0.5)
    assert of_image.detail["scope"] == "full_frame"


def test_a_declared_scene_region_measures_the_scene():
    rgb = np.full((100, 100, 3), 20, dtype=np.uint8)
    rgb[:, :50] = WARM
    band = {"hue_deg": [20, 45], "sat_min": 0.4, "val_min": 0.2}
    region = np.zeros((100, 100), dtype=bool)
    region[:, :50] = True

    scene = metrics.warm_share(rgb, region, band, region_semantics="water surface")
    assert scene.value == pytest.approx(1.0)
    assert scene.detail["denominator"] == 5000
    assert scene.detail["scope"] == "scene_region"
    assert "water surface" in scene.detail["denominator_semantics"]


# --- disclosure -------------------------------------------------------------


def test_every_metric_discloses_what_it_divided_and_what_it_read(tmp_path):
    rgb, _ = _frame(background_rows=100)
    path = tmp_path / "frame.png"
    Image.fromarray(rgb).save(path)

    report = critic.evaluate(
        [critic.Frame(name="frame.png", path=path)], art_direction.load(CONTRACT)
    ).to_dict()
    metrics_seen = report["frames"][0]["metrics"]
    assert "luminance_floor" in metrics_seen and "warm_share_frame" in metrics_seen

    for name, record in metrics_seen.items():
        disclosure = record["disclosure"]
        assert disclosure["assertion"] in {"measurement", "inference"}, name
        if disclosure["evaluated"]:
            assert disclosure["denominator_semantics"], name
        else:
            assert disclosure["not_measured_reason"], name
        assert "frame_sha256" in disclosure["sources"], name
        assert disclosure["contract"]["revision"] == report["direction_revision"], name
        assert "limitations" in disclosure, name

    assert metrics_seen["luminance_floor"]["disclosure"]["assertion"] == "measurement"
    assert metrics_seen["luminance_cause"]["disclosure"]["assertion"] == "inference"


def test_coverage_is_its_own_semantics_never_a_visibility_claim():
    # "A surface is here" and "this surface is this thing" are different claims, and
    # the bundle must not let one stand in for the other.
    assert bundle.ROLE_SEMANTICS["mask_world_occupancy"] == frozenset({"scene_coverage"})
    assert "scene_coverage" not in bundle.ROLE_SEMANTICS["mask_world_visible"]
    assert "mask_world_occupancy" in bundle.MASK_ROLES


def test_the_cause_travels_with_the_floor_finding_and_never_decides_it(tmp_path):
    rgb, _ = _frame(background_rows=100)
    frame_path = tmp_path / "frame.png"
    Image.fromarray(rgb).save(frame_path)
    direction = art_direction.load(CONTRACT)

    report = critic.evaluate([critic.Frame(name="frame.png", path=frame_path)], direction).to_dict()
    floor = next(f for f in report["findings"] if f["metric"] == "luminance_floor")
    assert floor["detail"]["cause"]["diagnosis"]["value"] == "undetermined"
    cause_finding = next(f for f in report["findings"] if f["metric"] == "luminance_cause")
    assert cause_finding["severity"] == "note"
    assert report["status"] == "FAIL"

    # A diagnosis never decides a verdict: a frame that clears every gate is a PASS and
    # still carries the note, because a note is not a pass and not a failure.
    lit = np.full((200, 200, 3), (62, 90, 99), dtype=np.uint8)  # the palette's mist
    lit_path = tmp_path / "lit.png"
    Image.fromarray(lit).save(lit_path)
    passing = critic.evaluate([critic.Frame(name="lit.png", path=lit_path)], direction).to_dict()
    assert passing["status"] == "PASS"
    assert any(
        f["metric"] == "luminance_cause" and f["severity"] == "note" for f in passing["findings"]
    )
