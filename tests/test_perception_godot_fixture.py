"""Mask correctness against a controlled scene.

A mask with correct dimensions and a valid hash can still be completely wrong.
This fixture puts one target behind a wall and one in the open, then asserts the
pixels rather than the provenance.
"""

import os
import shutil
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from elevenvt_studio.adapters.godot_capture import GodotCaptureAdapter

SERVICE = Path("Games/emberkeep/game/scripts/capture/service.gd")
FIXTURE = Path("tests/godot/mask_fixture")


def godot_executable() -> str:
    candidate = os.environ.get("GODOT_EXECUTABLE", "C:/Users/11vat/tools/ai-game-studio/godot/godot.exe")
    if not Path(candidate).is_file():
        pytest.skip(f"Godot executable not found at {candidate}")
    return candidate


@pytest.fixture(scope="module")
def captured(tmp_path_factory):
    root = tmp_path_factory.mktemp("mask_fixture")
    project = root / "proj"
    shutil.copytree(FIXTURE, project)
    (project / "scripts").mkdir(exist_ok=True)
    shutil.copy(SERVICE, project / "scripts" / "service.gd")

    adapter = GodotCaptureAdapter(
        godot_executable=godot_executable(),
        project_path=project,
        captures_root=root / "captures",
        workspace_root=Path.cwd(),
        name="mask_fixture",
        warmup_frames=10,
        timeout_seconds=240,
    )
    bundle = adapter.capture(
        roles=[
            "frame",
            "mask_world_visible",
            "mask_lantern_visible",
            "mask_lantern_silhouette",
            "mask_lantern_illumination",
        ]
    )
    return bundle


def white_mask(bundle, role) -> np.ndarray:
    return np.asarray(Image.open(bundle.image_path(role)).convert("L")) > 127


def test_capture_verifies_but_grants_no_authority(captured):
    assert captured.verify().ok
    # The game is not allowed to grant authority to its own output.
    assert captured.evidence_grade == "supervisory"
    assert captured.document["qualification"]["repeatability"]["status"] == "not_run"


def test_visible_segmentation_respects_occlusion(captured):
    visible = white_mask(captured, "mask_lantern_visible")
    height, width = visible.shape
    centre = visible[:, int(width * 0.36) : int(width * 0.68)]

    assert visible.sum() > 0, "the open target should be visible"
    assert centre.sum() == 0, "the target behind the wall must not appear in a visibility mask"


def test_silhouette_includes_what_visibility_excludes(captured):
    visible = white_mask(captured, "mask_lantern_visible")
    silhouette = white_mask(captured, "mask_lantern_silhouette")
    height, width = silhouette.shape
    centre = silhouette[:, int(width * 0.36) : int(width * 0.68)]

    assert centre.sum() > 0, "the silhouette ignores occlusion and must include the hidden target"
    assert silhouette.sum() > visible.sum()
    assert not np.any(visible & ~silhouette), "visible pixels must be a subset of the silhouette"


def test_world_mask_covers_the_wall(captured):
    world = white_mask(captured, "mask_world_visible")
    height, width = world.shape
    centre = world[:, int(width * 0.36) : int(width * 0.68)]
    assert centre.sum() > width * height * 0.1


def test_illumination_mask_is_not_vacuous(captured):
    illumination = white_mask(captured, "mask_lantern_illumination")
    # A light placed inside a closed hull produces an all-zero difference; that is
    # a broken fixture, not a passing measurement.
    assert illumination.sum() > 1000
