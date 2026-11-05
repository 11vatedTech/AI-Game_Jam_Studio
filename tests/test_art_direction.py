from __future__ import annotations

import copy
import hashlib
import json
import sqlite3
from pathlib import Path

import pytest

from elevenvt_studio.db import Database
from elevenvt_studio.errors import ValidationError
from elevenvt_studio.quality import art_direction, binding

REPO = Path(__file__).resolve().parents[1]
CONTRACT = REPO / "Games" / "emberkeep" / "art_direction.json"


def _document() -> dict:
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


def _write(tmp_path: Path, document: dict) -> Path:
    path = tmp_path / "art_direction.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


def test_contract_loads_and_hashes() -> None:
    direction = art_direction.load(CONTRACT)
    assert direction.production == "emberkeep"
    assert direction.revision == "1.0.0"
    assert direction.threshold_status == "provisional"
    assert direction.role_hex("lantern") == "#FFC168"
    assert len(direction.sha256) == 64
    # The spec's warm band, straight from the art bible's 90/10 law.
    assert direction.threshold("warm_share")["hue_deg"] == [20, 45]


def test_hash_changes_with_content(tmp_path: Path) -> None:
    document = _document()
    first = art_direction.load(_write(tmp_path, document), verify_references=False)
    document["thresholds"]["warm_share"]["ceiling"] = 0.12
    second = art_direction.load(_write(tmp_path, document), verify_references=False)
    assert first.sha256 != second.sha256


@pytest.mark.parametrize(
    "mutate, fragment",
    [
        (lambda d: d.pop("thresholds"), "thresholds"),
        (lambda d: d["palette"]["base"].pop(), "palette"),
        (lambda d: d["palette"]["roles"].update({"ember": 9}), "roles"),
        (lambda d: d.update({"extra_key": 1}), "extra_key"),
        (lambda d: d["thresholds"]["warm_share"].update({"hue_deg": [45, 20]}), "hue_deg"),
        (lambda d: d["thresholds"]["delta_e_max"].pop("max"), "delta_e_max"),
    ],
)
def test_invalid_contracts_fail_with_a_path(tmp_path: Path, mutate, fragment) -> None:
    document = _document()
    mutate(document)
    with pytest.raises(ValidationError) as error:
        art_direction.load(_write(tmp_path, document), verify_references=False)
    message = str(error.value)
    assert "$" in message, message
    assert fragment in message, message


def test_duplicate_role_mapping_is_rejected(tmp_path: Path) -> None:
    document = _document()
    document["palette"]["roles"]["ember"] = document["palette"]["roles"]["lantern"]
    with pytest.raises(ValidationError, match="distinct"):
        art_direction.load(_write(tmp_path, document), verify_references=False)


def test_confirmed_status_requires_calibration(tmp_path: Path) -> None:
    document = _document()
    document["threshold_status"] = "confirmed"
    with pytest.raises(ValidationError):
        art_direction.load(_write(tmp_path, document), verify_references=False)

    document["calibration"] = {
        "reviewed_by": "founder",
        "reviewed_at": "2026-11-05T00:00:00Z",
        "report_path": "reports/quality/calibration.json",
    }
    direction = art_direction.load(_write(tmp_path, document), verify_references=False)
    assert direction.is_confirmed


def test_reference_hash_mismatch_blocks_loading(tmp_path: Path) -> None:
    frame = tmp_path / "frame.png"
    frame.write_bytes(b"frame-a")
    document = _document()
    document["references"] = [
        {
            "id": "ref-test",
            "path": "frame.png",
            "sha256": hashlib.sha256(b"frame-a").hexdigest(),
        }
    ]
    art_direction.load(_write(tmp_path, document))  # matching frame is accepted

    frame.write_bytes(b"frame-b")  # content changed without a contract revision
    with pytest.raises(ValidationError, match="sha256 mismatch"):
        art_direction.load(_write(tmp_path, document))


def test_legibility_may_not_exceed_capture(tmp_path: Path) -> None:
    document = _document()
    document["capture"]["legibility_resolution"] = [2560, 1440]
    with pytest.raises(ValidationError, match="legibility"):
        art_direction.load(_write(tmp_path, document), verify_references=False)


def _db(tmp_path: Path):
    return Database(tmp_path / "studio.sqlite3").connect()


def _job(conn) -> str:
    """Reviews reference a job; a review without one is a foreign-key violation, not a fixture detail."""
    conn.execute(
        "INSERT INTO jobs(id,name,status,spec_json,created_at,updated_at,workspace)"
        " VALUES(?,?,?,?,?,?,?)",
        ("job1", "emberkeep", "running", "{}", "2026-11-05T00:00:00Z", "2026-11-05T00:00:00Z", str(REPO)),
    )
    return "job1"


def test_approval_survives_unrelated_change_and_dies_on_frame_edit(tmp_path: Path) -> None:
    direction = art_direction.load(CONTRACT, verify_references=False)
    frames = [binding.FrameRef(name="shot_00.png", sha256="a" * 64)]

    with _db(tmp_path) as conn:
        job_id = _job(conn)
        evidence = binding.review_evidence(
            gate=1, direction=direction, frames=frames, method="cli-interactive", confirmation="abc12345"
        )
        conn.execute(
            "INSERT INTO reviews(id,job_id,review_type,verdict,reviewer,rationale,evidence_json,created_at)"
            " VALUES(?,?,?,?,?,?,?,?)",
            ("r1", job_id, "gate-1", "approved", "founder", "locked", json.dumps(evidence), "2026-11-05T00:00:00Z"),
        )

        valid, reason = binding.approval_status(conn, 1, direction, frames)
        assert valid, reason

        # Same direction and frames, different metric colours: approval is unaffected.
        assert binding.approval_status(conn, 1, direction, frames)[0]

        valid, reason = binding.approval_status(
            conn, 1, direction, [binding.FrameRef(name="shot_00.png", sha256="b" * 64)]
        )
        assert not valid and "frames changed" in reason

        assert not binding.approval_status(conn, 2, direction, frames)[0]


def test_revision_change_invalidates_approval(tmp_path: Path) -> None:
    document = _document()
    (tmp_path / "v1").mkdir()
    original = art_direction.load(_write(tmp_path / "v1", document), verify_references=False)
    frames = [binding.FrameRef(name="shot_00.png", sha256="a" * 64)]

    with _db(tmp_path) as conn:
        job_id = _job(conn)
        evidence = binding.review_evidence(
            gate=1, direction=original, frames=frames, method="cli-interactive", confirmation="abc12345"
        )
        conn.execute(
            "INSERT INTO reviews(id,job_id,review_type,verdict,reviewer,rationale,evidence_json,created_at)"
            " VALUES(?,?,?,?,?,?,?,?)",
            ("r1", job_id, "gate-1", "approved", "founder", "locked", json.dumps(evidence), "2026-11-05T00:00:00Z"),
        )

        bumped = copy.deepcopy(document)
        bumped["revision"] = "1.1.0"
        (tmp_path / "v2").mkdir()
        new_direction = art_direction.load(_write(tmp_path / "v2", bumped), verify_references=False)

        valid, reason = binding.approval_status(conn, 1, new_direction, frames)
        assert not valid and "art direction changed" in reason


def test_transcribed_chat_approval_is_labelled_weak(tmp_path: Path) -> None:
    direction = art_direction.load(CONTRACT, verify_references=False)
    frames = [binding.FrameRef(name="shot_00.png", sha256="a" * 64)]

    with pytest.raises(ValidationError, match="quote"):
        binding.review_evidence(gate=1, direction=direction, frames=frames, method="chat-transcription")

    evidence = binding.review_evidence(
        gate=2,
        direction=direction,
        frames=frames,
        method="chat-transcription",
        confirmation="looks good, ship it",
    )
    assert evidence["confidence"] == "weak"
    assert evidence["method"] == "chat-transcription"
