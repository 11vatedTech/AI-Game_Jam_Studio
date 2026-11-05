import json
from pathlib import Path

import pytest
from PIL import Image

from elevenvt_studio.errors import ValidationError
from elevenvt_studio.perception.bundle import CaptureBundle, compute_grade
from perception_support import make_bundle, sha256


def test_authoritative_bundle_loads_and_verifies(tmp_path: Path):
    path = make_bundle(tmp_path, roles=("frame", "mask_lantern_visible"))
    bundle = CaptureBundle.load(path)

    assert bundle.evidence_grade == "authoritative"
    assert bundle.authoritative is True
    verification = bundle.verify()
    assert verification.ok, [check.to_dict() for check in verification.failures()]
    assert bundle.summary()["artifacts"][0]["role"] == "frame"


def test_live_bundle_can_never_claim_authority(tmp_path: Path):
    path = make_bundle(tmp_path, mode="live", declared_grade="authoritative")
    with pytest.raises(ValidationError, match="Evidence grade does not match"):
        CaptureBundle.load(path)


def test_deterministic_bundle_without_qualification_is_supervisory(tmp_path: Path):
    path = make_bundle(tmp_path, repeatability="unqualified", declared_grade="supervisory")
    bundle = CaptureBundle.load(path)
    assert bundle.evidence_grade == "supervisory"
    assert not bundle.authoritative


def test_deterministic_bundle_cannot_declare_authority_unqualified(tmp_path: Path):
    path = make_bundle(tmp_path, repeatability="not_run", declared_grade="authoritative")
    with pytest.raises(ValidationError, match="Evidence grade does not match"):
        CaptureBundle.load(path)


@pytest.mark.parametrize(
    "mode,repeatability,expected",
    [
        ("live", "qualified", "supervisory"),
        ("deterministic", "qualified", "authoritative"),
        ("deterministic", "unqualified", "supervisory"),
        ("deterministic", None, "supervisory"),
    ],
)
def test_grade_derivation(mode, repeatability, expected):
    assert compute_grade(mode, repeatability) == expected


def test_path_traversal_is_refused(tmp_path: Path):
    (tmp_path / "bundle.json").unlink(missing_ok=True)
    root = tmp_path / "capture"
    root.mkdir()
    path = make_bundle(root, mutate={"artifacts.0.path": "../../escape.png"})
    with pytest.raises(ValidationError, match="traversal"):
        CaptureBundle.load(path)


def test_absolute_path_is_refused(tmp_path: Path):
    (tmp_path / "bundle.json").unlink(missing_ok=True)
    root = tmp_path / "capture"
    root.mkdir()
    path = make_bundle(root, mutate={"artifacts.0.path": "C:/Windows/system32/x.png"})
    with pytest.raises(ValidationError, match="relative"):
        CaptureBundle.load(path)


def test_duplicate_role_is_refused(tmp_path: Path):
    path = make_bundle(tmp_path)
    document = json.loads(path.read_text())
    document["artifacts"].append(dict(document["artifacts"][0]))
    path.write_text(json.dumps(document))
    with pytest.raises(ValidationError, match="Duplicate artifact role"):
        CaptureBundle.load(path)


def test_silhouette_cannot_be_labelled_visible_segmentation(tmp_path: Path):
    path = make_bundle(tmp_path, roles=("frame", "mask_lantern_silhouette"))
    document = json.loads(path.read_text())
    for artifact in document["artifacts"]:
        if artifact["role"] == "mask_lantern_silhouette":
            artifact["semantics"] = "visible_segmentation"
    path.write_text(json.dumps(document))
    with pytest.raises(ValidationError, match="may not carry semantics"):
        CaptureBundle.load(path)


def test_tampered_artifact_fails_verification(tmp_path: Path):
    path = make_bundle(tmp_path)
    Image.new("RGB", (320, 180), (10, 10, 10)).save(tmp_path / "frame.png", format="PNG")
    bundle = CaptureBundle.load(path)
    verification = bundle.verify()
    assert verification.status == "failed"
    names = {check.name for check in verification.failures()}
    assert {"frame:sha256", "frame:bytes"} <= names


def test_black_frame_fails_verification(tmp_path: Path):
    path = make_bundle(tmp_path)
    Image.new("RGB", (320, 180), (1, 1, 1)).save(tmp_path / "frame.png", format="PNG", optimize=True)
    document = json.loads(path.read_text())
    frame = tmp_path / "frame.png"
    document["artifacts"][0]["sha256"] = sha256(frame)
    document["artifacts"][0]["bytes"] = frame.stat().st_size
    path.write_text(json.dumps(document))

    verification = CaptureBundle.load(path).verify()
    assert verification.status == "failed"
    assert any(check.name == "frame:blackness" for check in verification.failures())


def test_expected_black_allows_a_deliberately_black_frame(tmp_path: Path):
    path = make_bundle(tmp_path)
    Image.new("RGB", (320, 180), (1, 1, 1)).save(tmp_path / "frame.png", format="PNG", optimize=True)
    document = json.loads(path.read_text())
    frame = tmp_path / "frame.png"
    document["artifacts"][0]["sha256"] = sha256(frame)
    document["artifacts"][0]["bytes"] = frame.stat().st_size
    document["request"]["expect_black"] = True
    path.write_text(json.dumps(document))

    assert CaptureBundle.load(path).verify().ok


def test_mask_dimensions_must_match_frame(tmp_path: Path):
    path = make_bundle(tmp_path, roles=("frame", "mask_lantern_visible"), mask_size=(100, 100))
    verification = CaptureBundle.load(path).verify()
    assert verification.status == "failed"
    assert any(check.name == "mask_lantern_visible:frame_dimensions" for check in verification.failures())


def test_non_binary_mask_fails(tmp_path: Path):
    path = make_bundle(tmp_path, roles=("frame", "mask_lantern_visible"))
    mask = tmp_path / "mask_lantern_visible.png"
    Image.new("L", (320, 180), 128).save(mask, format="PNG", optimize=True)
    document = json.loads(path.read_text())
    for artifact in document["artifacts"]:
        if artifact["role"] == "mask_lantern_visible":
            artifact["sha256"] = sha256(mask)
            artifact["bytes"] = mask.stat().st_size
    path.write_text(json.dumps(document))

    verification = CaptureBundle.load(path).verify()
    assert verification.status == "failed"
    assert any(check.name == "mask_lantern_visible:binary" for check in verification.failures())
