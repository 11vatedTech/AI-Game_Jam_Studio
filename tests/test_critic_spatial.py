"""The critic must say what it measured about darkness, and claim no more than that.

The Emberkeep failure proved the gap: a global p5 named a defect and described it as
"a dead-black lower third", which is equally consistent with unlit geometry, absent
geometry, and a bad exposure. These tests pin each dimension apart — coverage, surface
detail, illumination — and pin the refusal when an input that a dimension needs was
never captured.
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


def _frame(*, background_rows: int = 0, structured: bool = False, height: int = 200, width: int = 200):
    """A lit top half over a dark bottom half, plus the coverage mask describing it."""
    rgb = np.zeros((height, width, 3), dtype=np.uint8)
    rgb[: height // 2] = LIT
    rgb[height // 2 :] = DARK
    if structured:
        noise = np.random.default_rng(7).integers(0, 30, size=(height // 2, width))
        rgb[height // 2 :] = noise[..., None]

    occupancy = np.ones((height, width), dtype=bool)
    if background_rows:
        occupancy[height - background_rows :] = False
    return rgb, occupancy


# --- the three dimensions ---------------------------------------------------


def test_dark_band_over_nothing_is_missing_coverage():
    rgb, occupancy = _frame(background_rows=100)
    out = metrics.luminance_cause(rgb, occupancy, 0.015)

    assert out.detail["coverage"]["state"] == "absent"
    assert out.detail["diagnosis"]["kind"] == "missing_coverage"
    assert out.value == pytest.approx(1.0)
    assert out.detail["diagnosis"]["confidence"] == "measured"


def test_a_hole_in_a_covered_band_is_still_missing_coverage():
    # Band averages would swallow a hole; coverage is counted per pixel.
    rgb, occupancy = _frame()
    occupancy[120:140, 40:80] = False
    out = metrics.luminance_cause(rgb, occupancy, 0.015)

    assert 0.0 < out.value < 0.5
    assert out.detail["coverage"]["state"] == "present"
    assert out.detail["coverage"]["dark_share_without_geometry"] == pytest.approx(out.value)


def test_dark_surface_is_described_by_detail_and_only_that():
    rgb, occupancy = _frame()
    out = metrics.luminance_cause(rgb, occupancy, 0.015)

    assert out.detail["coverage"]["state"] == "present"
    assert out.detail["surface_detail"]["state"] == "low_variance"
    # The point of the split: a variance measurement never becomes a lighting claim.
    assert out.detail["illumination_response"]["state"] == "undetermined"
    assert out.detail["diagnosis"]["kind"] == "dark_low_detail_surface"
    assert out.value == pytest.approx(0.0)
    assert "a surface too dark to light from light that never reaches it" in out.detail[
        "diagnosis"
    ]["cannot_distinguish"]


def test_dark_geometry_with_structure_is_described_as_structured():
    rgb, occupancy = _frame(structured=True)
    out = metrics.luminance_cause(rgb, occupancy, 0.015)

    assert out.detail["surface_detail"]["state"] in {"detailed", "undetermined"}
    assert out.detail["surface_detail"]["detail_free_share"] < 0.5
    assert out.detail["diagnosis"]["kind"] in {"dark_detailed_surface", "undetermined"}


def test_illumination_is_only_claimed_with_a_lights_off_control():
    rgb, occupancy = _frame()

    # Control identical to the frame: enabling the lights changed nothing in that region.
    out = metrics.luminance_cause(rgb, occupancy, 0.015, control_rgb=rgb.copy())
    assert out.detail["illumination_response"]["state"] == "low_contribution"
    assert out.detail["diagnosis"]["kind"] == "underlit_surface"

    # Control with the region unlit: the lights do contribute to it.
    dark_control = rgb.copy()
    dark_control[100:] = 0
    out = metrics.luminance_cause(rgb, occupancy, 0.015, control_rgb=dark_control)
    assert out.detail["illumination_response"]["state"] == "adequate_contribution"
    assert out.detail["illumination_response"]["contribution"] > 0.9


def test_without_a_coverage_mask_no_diagnosis_is_claimed():
    rgb, _ = _frame(background_rows=100)
    out = metrics.luminance_cause(rgb, None, 0.015)

    assert out.value is None
    assert out.detail["coverage"]["state"] == "undetermined"
    assert out.detail["diagnosis"]["kind"] == "undetermined"
    assert out.detail["diagnosis"]["confidence"] == "undetermined"
    assert out.detail["diagnosis"]["basis"] == ["coverage is unknown: no scene_coverage mask was captured"]


# --- coverage is not quality ------------------------------------------------


def test_full_coverage_does_not_make_an_unacceptable_frame_acceptable(tmp_path):
    # 100% occupancy, and a frame that is almost entirely below the floor.
    rgb = np.full((200, 200, 3), DARK, dtype=np.uint8)
    occupancy = np.ones((200, 200), dtype=bool)
    frame = tmp_path / "void.png"
    Image.fromarray(rgb).save(frame)
    mask = tmp_path / "void.occupancy.png"
    Image.fromarray((occupancy * 255).astype(np.uint8)).save(mask)

    direction = art_direction.load(CONTRACT)
    report = critic.evaluate(
        [critic.Frame(name="void.png", path=frame, occupancy_mask_path=mask)], direction
    ).to_dict()

    assert report["status"] == "FAIL"
    floor = next(f for f in report["findings"] if f["metric"] == "luminance_floor")
    assert floor["severity"] == "major"
    cause = floor["detail"]["cause"]
    assert cause["coverage"]["state"] == "present"
    assert cause["diagnosis"]["kind"] == "dark_low_detail_surface"


# --- warm share: two denominators, both stated ------------------------------


def test_warm_share_reports_world_and_frame_denominators_separately():
    warm = (204, 122, 41)
    rgb = np.full((100, 100, 3), 20, dtype=np.uint8)
    rgb[:, :50] = warm  # left half warm
    world = np.zeros((100, 100), dtype=bool)
    world[:, :50] = True  # the scene region is exactly the warm half

    band = {"hue_deg": [20, 45], "sat_min": 0.4, "val_min": 0.2}
    of_scene = metrics.warm_share(rgb, world, band)
    of_image = metrics.warm_share_frame(rgb, band)

    assert of_scene.value == pytest.approx(1.0)
    assert of_image.value == pytest.approx(0.5)
    assert of_scene.detail["denominator"] == 5000
    assert of_image.detail["denominator"] == 10000
    assert "world mask" in of_scene.detail["denominator_semantics"]
    assert "all frame pixels" in of_image.detail["denominator_semantics"]


# --- disclosure -------------------------------------------------------------


def test_every_metric_discloses_what_it_divided_and_what_it_read(tmp_path):
    rgb, _ = _frame(background_rows=100)
    path = tmp_path / "frame.png"
    Image.fromarray(rgb).save(path)

    report = critic.evaluate([critic.Frame(name="frame.png", path=path)], art_direction.load(CONTRACT)).to_dict()
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
    assert floor["detail"]["cause"]["diagnosis"]["kind"] == "undetermined"
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
    assert any(f["metric"] == "luminance_cause" and f["severity"] == "note" for f in passing["findings"])
