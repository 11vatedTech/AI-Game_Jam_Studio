import json
from pathlib import Path

import pytest

from elevenvt_studio.perception.bundle import CaptureBundle
from elevenvt_studio.perception.transport import (
    DEFAULT_PROFILE,
    TransportLimitExceeded,
    TransportProfile,
    prepare,
    prepare_all,
)
from perception_support import make_bundle


def test_frame_is_transported_without_touching_the_original(tmp_path: Path):
    bundle = CaptureBundle.load(make_bundle(tmp_path / "capture"))
    source_before = (bundle.root / "frame.png").read_bytes()

    item = prepare(bundle, "frame", out_dir=bundle.root / "transport")

    assert item.format == "JPEG"
    assert item.source_sha256 == bundle.artifact("frame")["sha256"]
    assert (bundle.root / "frame.png").read_bytes() == source_before
    assert item.bytes <= DEFAULT_PROFILE.max_image_bytes
    assert json.loads((bundle.root / "transport" / "transport.json").read_text())["profile"]["id"] if (bundle.root / "transport" / "transport.json").exists() else True


def test_masks_stay_lossless(tmp_path: Path):
    bundle = CaptureBundle.load(make_bundle(tmp_path / "capture", roles=("frame", "mask_lantern_visible")))
    item = prepare(bundle, "mask_lantern_visible", out_dir=bundle.root / "transport")
    assert item.format == "PNG"
    assert item.mime == "image/png"
    assert item.quality is None


def test_large_frame_is_downscaled_within_the_profile(tmp_path: Path):
    bundle = CaptureBundle.load(make_bundle(tmp_path / "capture", frame_size=(4000, 3000)))
    item = prepare(bundle, "frame", out_dir=bundle.root / "transport")
    assert max(item.width, item.height) <= DEFAULT_PROFILE.max_long_edge
    assert item.scale < 1.0


def test_exhausted_envelope_is_a_named_refusal(tmp_path: Path):
    bundle = CaptureBundle.load(make_bundle(tmp_path / "capture"))
    tiny = TransportProfile(
        id="tiny-test",
        max_image_bytes=200,
        max_width=2560,
        max_height=2560,
        max_long_edge=2560,
        max_visual_tokens=None,
        supported_formats=("PNG", "JPEG", "WEBP"),
        preferred_frame_format="JPEG",
        mask_format="PNG",
        max_images_per_call=6,
        max_total_payload_bytes=1_000_000,
    )
    with pytest.raises(TransportLimitExceeded) as excinfo:
        prepare(bundle, "frame", out_dir=bundle.root / "transport", profile=tiny)
    assert "crop" in str(excinfo.value)
    assert excinfo.value.details["attempts"]


def test_too_many_images_for_profile_is_refused(tmp_path: Path):
    bundle = CaptureBundle.load(
        make_bundle(tmp_path / "capture", roles=("frame", "mask_lantern_visible"))
    )
    with pytest.raises(TransportLimitExceeded, match="allows 1"):
        prepare_all(bundle, ["frame", "mask_lantern_visible"], out_dir=bundle.root / "transport", profile=DEFAULT_PROFILE.__class__(**{**DEFAULT_PROFILE.as_dict(), "max_images_per_call": 1}))


def test_blocks_carry_images_and_no_audience_annotation(tmp_path: Path):
    bundle = CaptureBundle.load(make_bundle(tmp_path / "capture", roles=("frame", "mask_lantern_visible")))
    result = prepare_all(bundle, ["frame", "mask_lantern_visible"], out_dir=bundle.root / "transport")

    assert len(result.blocks) == 2
    for block in result.blocks:
        assert block["type"] == "image"
        assert block["mimeType"] in {"image/jpeg", "image/png"}
        assert block["data"]
        assert "annotations" not in block

    manifest = json.loads((bundle.root / "transport" / "transport.json").read_text())
    assert manifest["profile"]["id"] == "studio-default-v1"
    assert len(manifest["artifacts"]) == 2
    assert manifest["total_base64_bytes"] > 0


def test_summary_states_supervisory_authority_and_hashes(tmp_path: Path):
    bundle = CaptureBundle.load(make_bundle(tmp_path / "capture", mode="live", declared_grade="supervisory"))
    result = prepare_all(bundle, ["frame"], out_dir=bundle.root / "transport", verification={"status": "verified"})
    assert "SUPERVISORY" in result.text
    assert bundle.artifact("frame")["sha256"] in result.text
    assert "evidence_grade: supervisory" in result.text


def test_downscale_is_visible_in_the_summary(tmp_path: Path):
    bundle = CaptureBundle.load(make_bundle(tmp_path / "capture", frame_size=(4000, 3000)))
    result = prepare_all(bundle, ["frame"], out_dir=bundle.root / "transport")
    assert "downscaled" in result.text
