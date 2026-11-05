"""The critic must say *why* a frame is dark, and admit when it cannot tell.

The Emberkeep failure proved the gap: a global p5 named a defect and described it
as "a dead-black lower third", which is equally consistent with unlit geometry,
absent geometry, and a bad exposure. These tests pin the distinctions the
diagnosis has to make, and pin the refusal when the evidence cannot support one.
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


def _frame(*, background_rows: int = 0, structured: bool = False, height: int = 200, width: int = 200):
    """Build a frame with a lit top and a dark band, plus the mask that describes it."""
    rgb = np.zeros((height, width, 3), dtype=np.uint8)
    rgb[: height // 2] = 90
    rgb[height // 2 :] = 5
    if structured:
        noise = np.random.default_rng(7).integers(0, 30, size=(height // 2, width))
        rgb[height // 2 :] = noise[..., None]

    occupancy = np.ones((height, width), dtype=bool)
    if background_rows:
        occupancy[height - background_rows :] = False
    return rgb, occupancy


def test_dark_band_over_nothing_is_missing_coverage():
    rgb, occupancy = _frame(background_rows=100)
    out = metrics.luminance_cause(rgb, occupancy, 0.015)

    diagnosis = out.detail["diagnosis"]
    assert diagnosis["kind"] == "missing_coverage"
    assert diagnosis["confidence"] > 0.5
    assert out.value == pytest.approx(1.0)
    # The bands carrying the failure are named, not just counted.
    assert diagnosis["basis"][0].count("band")


def test_dark_band_over_geometry_is_not_blamed_on_coverage():
    rgb, occupancy = _frame(background_rows=0)
    out = metrics.luminance_cause(rgb, occupancy, 0.015)

    diagnosis = out.detail["diagnosis"]
    assert diagnosis["kind"] == "unlit_flat_surface"
    assert out.value == pytest.approx(0.0)
    assert out.detail["gap_bands"] == []
    assert out.detail["dark_over_geometry_share"] == pytest.approx(1.0)


def test_dark_geometry_with_structure_is_a_shadow_not_a_defect():
    rgb, occupancy = _frame(structured=True)
    out = metrics.luminance_cause(rgb, occupancy, 0.015)

    assert out.detail["diagnosis"]["kind"] == "shadowed_geometry"
    assert out.detail["detail_free_dark_share"] < 0.5


def test_without_a_coverage_mask_the_critic_refuses_to_name_a_cause():
    rgb, _ = _frame(background_rows=100)
    out = metrics.luminance_cause(rgb, None, 0.015)

    assert out.value is None
    assert out.detail["diagnosis"]["kind"] == "undetermined"
    assert out.confidence == 0.0
    assert any("cannot be attributed" in line for line in out.limitations)


def test_the_cause_is_attached_to_the_floor_finding_and_only_ever_a_note(tmp_path):
    rgb, _ = _frame(background_rows=100)
    frame_path = tmp_path / "frame.png"
    Image.fromarray(rgb).save(frame_path)
    direction = art_direction.load(CONTRACT)

    frame = critic.Frame(name="frame.png", path=frame_path)
    report = critic.evaluate([frame], direction).to_dict()

    floor = next(f for f in report["findings"] if f["metric"] == "luminance_floor")
    assert floor["severity"] == "major"
    assert floor["detail"]["cause"]["diagnosis"]["kind"] == "undetermined"

    cause = next(f for f in report["findings"] if f["metric"] == "luminance_cause")
    assert cause["severity"] == "note"
    assert report["status"] == "FAIL"

    # A diagnosis never decides a verdict: a frame that clears every gate still
    # carries the same note, and the note never turns into a finding of its own.
    bright = np.full((200, 200, 3), (62, 90, 99), dtype=np.uint8)  # the palette's mist
    bright_path = tmp_path / "bright.png"
    Image.fromarray(bright).save(bright_path)
    passing = critic.evaluate([critic.Frame(name="bright.png", path=bright_path)], direction).to_dict()
    assert passing["status"] == "PASS"
    assert any(f["metric"] == "luminance_cause" and f["severity"] == "note" for f in passing["findings"])


def test_coverage_is_its_own_semantics_never_a_visibility_claim():
    # "A surface is here" and "this surface is this thing" are different claims, and
    # the bundle must not let one stand in for the other.
    assert bundle.ROLE_SEMANTICS["mask_world_occupancy"] == frozenset({"scene_coverage"})
    assert "scene_coverage" not in bundle.ROLE_SEMANTICS["mask_world_visible"]
    assert "mask_world_occupancy" in bundle.MASK_ROLES
