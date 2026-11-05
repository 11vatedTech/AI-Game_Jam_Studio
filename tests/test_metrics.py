from __future__ import annotations

import numpy as np
import pytest

from elevenvt_studio.quality import metrics

BAND = {"hue_deg": [20, 45], "sat_min": 0.25, "val_min": 0.20, "ceiling": 0.10}
LANTERN = (255, 193, 104)  # the art bible's lantern swatch


def _frame(width=64, height=64, colour=(30, 40, 48)) -> np.ndarray:
    image = np.zeros((height, width, 3), dtype=np.uint8)
    image[:] = colour
    return image


def test_warm_share_is_exactly_the_warm_fraction():
    image = _frame()
    image[20:40, 20:40] = LANTERN  # 400 of 4096 pixels
    mask = np.ones((64, 64), dtype=bool)

    output = metrics.warm_share(image, mask, BAND)

    assert output.value == pytest.approx(400 / 4096)
    assert output.detail["warm_pixels"] == 400
    assert output.detail["world_pixels"] == 4096


def test_warm_share_excludes_masked_out_pixels():
    image = _frame()
    image[:, :32] = LANTERN  # half the frame is warm
    half_world = np.zeros((64, 64), dtype=bool)
    half_world[:, 32:] = True  # but only the cool half counts as world

    output = metrics.warm_share(image, half_world, BAND)
    assert output.value == pytest.approx(0.0)


def test_warm_share_without_mask_is_not_evaluated():
    output = metrics.warm_share(_frame(), None, BAND)
    assert not output.evaluated
    assert output.value is None


def test_cool_blue_is_not_warm():
    output = metrics.warm_share(_frame(colour=(20, 60, 220)), np.ones((64, 64), dtype=bool), BAND)
    assert output.value == pytest.approx(0.0)


def test_luminance_floor_detects_a_dead_black_frame():
    black = metrics.luminance_percentiles(_frame(colour=(0, 0, 0)))
    grey = metrics.luminance_percentiles(_frame(colour=(90, 90, 90)))

    assert black.value == pytest.approx(0.0, abs=1e-6)
    assert grey.value > 0.05
    assert black.detail["p50"] == pytest.approx(0.0, abs=1e-6)


def test_palette_drift_is_near_zero_for_a_palette_colour():
    output = metrics.palette_drift(_frame(colour=LANTERN), ("#0B1016", "#1C2B33", "#3E5A63", "#D8CDBA", "#FFC168", "#FF7A2F"))
    assert output.value is not None
    assert output.value < 1.0


def test_palette_drift_grows_for_an_off_palette_colour():
    on_palette = metrics.palette_drift(_frame(colour=LANTERN), ("#0B1016", "#1C2B33", "#3E5A63", "#D8CDBA", "#FFC168", "#FF7A2F"))
    off_palette = metrics.palette_drift(_frame(colour=(255, 0, 255)), ("#0B1016", "#1C2B33", "#3E5A63", "#D8CDBA", "#FFC168", "#FF7A2F"))
    assert off_palette.value > on_palette.value


def test_silhouette_is_one_when_only_the_player_is_added():
    background = _frame()
    with_player = background.copy()
    with_player[24:40, 24:40] = (220, 220, 210)

    output = metrics.silhouette(with_player, background, None)
    assert output.value is not None
    assert output.value > 0.9


def test_silhouette_is_zero_for_identical_frames():
    background = _frame()
    assert metrics.silhouette(background, background.copy(), None).value == pytest.approx(0.0)


def test_horizon_roll_refuses_to_guess_without_a_transform():
    output = metrics.horizon_roll(None)
    assert not output.evaluated
    assert output.confidence == 0.0
    assert metrics.horizon_roll(-2.5).value == pytest.approx(2.5)


def test_lantern_dominance_measures_the_gap():
    image = _frame(colour=(20, 20, 20))
    mask = np.zeros((64, 64), dtype=bool)
    mask[8:16, 8:16] = True
    image[mask] = LANTERN

    output = metrics.lantern_dominance(image, mask)
    assert output.value > 0.1


def test_every_metric_declares_version_confidence_and_limitations():
    outputs = [
        metrics.luminance_percentiles(_frame()),
        metrics.warm_share(_frame(), np.ones((64, 64), dtype=bool), BAND),
        metrics.palette_drift(_frame(), ("#0B1016", "#1C2B33", "#3E5A63", "#D8CDBA", "#FFC168", "#FF7A2F")),
        metrics.clutter(_frame()),
        metrics.lantern_dominance(_frame(), np.ones((64, 64), dtype=bool)),
        metrics.event_delta(_frame(), _frame(colour=(60, 70, 80))),
        metrics.horizon_roll(1.0),
    ]
    for output in outputs:
        assert output.algorithm_version
        assert 0.0 <= output.confidence <= 1.0
        assert output.limitations, output.algorithm_version
