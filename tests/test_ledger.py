from __future__ import annotations

import json

import pytest

from elevenvt_studio.db import Database
from elevenvt_studio.errors import NotFound, PermissionDenied, ValidationError
from elevenvt_studio.ledger import REDACTED, Ledger, redact
from elevenvt_studio.quality.taxonomy import FailureClass, classify


@pytest.fixture()
def ledger(tmp_path):
    return Ledger(Database(tmp_path / "studio.sqlite3"))


def test_successful_operation_has_no_gap(ledger):
    op_id = ledger.start(kind="generate", boundary="agent", target="comfyui.flux2_klein", inputs={"prompt": "shrine"})
    record = ledger.finish(op_id, outcome="ok", outputs={"artifact": "pylon.glb"})

    assert record["outcome"] == "ok"
    assert record["finished_at"]
    assert record["request_digest"] and record["response_digest"]
    assert ledger.gaps() == []


def test_in_flight_operation_is_a_visible_gap(ledger):
    ledger.start(kind="generate", boundary="engine", target="blender.render", inputs={})
    gaps = ledger.gaps()
    assert len(gaps) == 1
    assert gaps[0]["outcome"] == "uncertain"


def test_context_records_failure_and_reraises(ledger):
    with pytest.raises(ValidationError):
        with ledger.context(kind="mesh", boundary="agent", target="ingest", inputs={"path": "pylon.glb"}):
            raise ValidationError("mesh has no floor face")

    record = ledger.list_operations()[0]
    assert record["outcome"] == "failed"
    assert record["failure_class"] == FailureClass.INPUT_INVALID.value
    assert ledger.gaps() == []


def test_unclassified_failure_stays_unknown(ledger):
    with pytest.raises(RuntimeError):
        with ledger.context(kind="odd", boundary="cli", target="mystery"):
            raise RuntimeError("something specific happened")

    record = ledger.list_operations()[0]
    assert record["failure_class"] == FailureClass.UNKNOWN.value
    assert "UNKNOWN" in record["notes"]


def test_denial_is_recorded_as_denied_not_failed(ledger):
    op_id = ledger.record_denial(kind="write", boundary="agent", target="C:/Windows", reason="outside workspace")
    record = ledger.show(op_id)
    assert record["outcome"] == "denied"
    assert record["failure_class"] == FailureClass.POLICY_DENIED.value
    assert ledger.gaps() == []


def test_secrets_are_redacted_before_storage(ledger):
    op_id = ledger.start(
        kind="call",
        boundary="mcp",
        target="provider",
        inputs={"api_key": "sk-live-abc123", "nested": {"Authorization": "Bearer xyz"}, "model": "local"},
    )
    stored = ledger.show(op_id)["inputs"]

    assert stored["api_key"] == REDACTED
    assert stored["nested"]["Authorization"] == REDACTED
    assert stored["model"] == "local"
    assert "sk-live-abc123" not in json.dumps(stored)


def test_redaction_is_key_based_and_recursive():
    assert redact({"a": [{"token": "t", "keep": 1}]}) == {"a": [{"token": REDACTED, "keep": 1}]}


def test_finishing_an_unknown_operation_fails_loudly(ledger):
    with pytest.raises(NotFound):
        ledger.finish("not-a-real-op", outcome="ok")


@pytest.mark.parametrize(
    "exc, expected",
    [
        (PermissionDenied("no"), FailureClass.POLICY_DENIED),
        (ValidationError("bad input"), FailureClass.INPUT_INVALID),
        (TimeoutError("slow"), FailureClass.TIMEOUT),
        (MemoryError("vram"), FailureClass.RESOURCE_EXHAUSTED),
        (KeyError("missing"), FailureClass.UNKNOWN),
    ],
)
def test_classification(exc, expected):
    assert classify(exc)[0] is expected
