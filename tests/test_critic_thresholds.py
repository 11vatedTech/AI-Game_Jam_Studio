from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from elevenvt_studio.quality import art_direction, critic

REPO = Path(__file__).resolve().parents[1]
CONTRACT = REPO / "Games" / "emberkeep" / "art_direction.json"
LANTERN = (255, 193, 104)


@pytest.fixture()
def frames(tmp_path):
    image = np.zeros((64, 64, 3), dtype=np.uint8)
    # Slate from the declared palette: bright enough to clear the luminance floor and
    # on-palette, so this test isolates warm share instead of tripping palette drift.
    image[:] = (28, 43, 51)
    image[12:52, 12:52] = LANTERN  # 1600/4096 ≈ 39% warm: far above any sane ceiling
    Image.fromarray(image).save(tmp_path / "frame.png")
    Image.fromarray(np.ones((64, 64), np.uint8) * 255).save(tmp_path / "frame.mask.png")
    return critic.frames_from_directory(tmp_path)


def _direction(tmp_path: Path, ceiling: float):
    document = json.loads(CONTRACT.read_text(encoding="utf-8"))
    document["thresholds"]["warm_share"]["ceiling"] = ceiling
    document["thresholds"]["warm_share"]["blocker_above"] = min(1.0, ceiling * 2)
    document["thresholds"]["warm_share"]["major_above"] = ceiling
    path = tmp_path / "contract.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    return art_direction.load(path, verify_references=False)


def test_the_same_frame_fails_or_passes_according_to_the_contract(tmp_path, frames):
    strict = critic.evaluate(frames, _direction(tmp_path, 0.05))
    lenient = critic.evaluate(frames, _direction(tmp_path, 0.90))

    assert strict.status == "FAIL"
    assert lenient.status == "PASS"

    strict_warm = [f for f in strict.findings if f.metric == "warm_share"]
    lenient_warm = [f for f in lenient.findings if f.metric == "warm_share"]
    assert strict_warm and strict_warm[0].severity == "blocker"
    assert not lenient_warm


def test_findings_carry_the_evidence_needed_to_disagree_with_them(tmp_path, frames):
    report = critic.evaluate(frames, _direction(tmp_path, 0.05))
    finding = next(f for f in report.findings if f.metric == "warm_share")

    assert finding.algorithm_version == "warm-share-1"
    assert 0.0 <= finding.confidence <= 1.0
    assert finding.limitations
    assert finding.threshold["ceiling"] == 0.05
    assert finding.value == pytest.approx(1600 / 4096, rel=0.01)


def test_absent_inputs_are_notes_not_passes(tmp_path, frames):
    report = critic.evaluate(frames, _direction(tmp_path, 0.90))
    notes = {f.metric for f in report.findings if f.severity == "note"}
    assert "lantern_dominance" in notes or "horizon_roll" in notes
    # A note never silently becomes a pass: the metric reports evaluated=False.
    lan = next(m for m in report.frames[0]["metrics"].values() if "lantern" in str(m))
    assert lan["evaluated"] is False


def test_metrics_module_knows_nothing_about_thresholds():
    """The metric measures; only the contract decides what the measurement means."""
    source = (REPO / "src" / "elevenvt_studio" / "quality" / "metrics.py").read_text(encoding="utf-8")
    for contract_key in ("ceiling", "iou_min", "p5_min", "blocker_above", "edge_density_max"):
        assert contract_key not in source, f"metrics.py refers to contract key {contract_key}"
