import io
from datetime import datetime, timedelta, timezone

import pytest
from PIL import Image

from elevenvt_studio.perception import probe as probe_module
from elevenvt_studio.perception.probe import CODE_ALPHABET, CODE_LENGTH, ProbeStore, Identity
from elevenvt_studio.perception.tools import PerceptionTools


def test_challenge_image_is_a_real_png_and_code_is_not_in_any_text(tmp_path, service):
    tools = PerceptionTools(service)
    response = tools.probe({"agent_instance": "test-agent"})

    image = Image.open(io.BytesIO(__import__("base64").b64decode(response.images[0]["data"])))
    assert image.format == "PNG"
    assert image.size == (720, 240)

    record = list(json_challenges(tools)["challenges"].values())[0]
    assert len(record["code"]) == CODE_LENGTH
    assert set(record["code"]) <= set(CODE_ALPHABET)
    assert record["code"] not in response.text
    assert "challenge_id" in response.text


def json_challenges(tools):
    import json

    return json.loads(tools.probes.path.read_text())


def test_correct_answer_verifies_and_cannot_be_reused(service):
    tools = PerceptionTools(service)
    response = tools.probe({})
    challenge = list(json_challenges(tools)["challenges"].values())[0]

    first = tools.probe_verify({"challenge_id": challenge["challenge_id"], "answer": challenge["code"].lower()})
    assert first.payload["verified"] is True

    second = tools.probe_verify({"challenge_id": challenge["challenge_id"], "answer": challenge["code"]})
    assert second.payload["verified"] is False
    assert second.payload["reason"] == "reused"


def test_wrong_answer_is_unverified_not_an_error(service):
    tools = PerceptionTools(service)
    tools.probe({})
    challenge = list(json_challenges(tools)["challenges"].values())[0]

    result = tools.probe_verify({"challenge_id": challenge["challenge_id"], "answer": "ZZZZZZ"})
    assert result.payload["verified"] is False
    assert result.payload["reason"] == "mismatch"


def test_expired_challenge_is_unverified(tmp_path, monkeypatch):
    store = ProbeStore(tmp_path)
    challenge, _ = store.issue()

    future = datetime.now(timezone.utc) + timedelta(seconds=probe_module.CHALLENGE_TTL_SECONDS + 5)
    monkeypatch.setattr(probe_module, "_now", lambda: future)

    result = store.verify(challenge.challenge_id, challenge.code)
    assert result == {"verified": False, "reason": "expired", "challenge_id": challenge.challenge_id}


def test_identity_fields_are_kept_separate(tmp_path):
    store = ProbeStore(tmp_path)
    challenge, _ = store.issue(Identity(studio_agent_instance="a1", mcp_client_name="cursor", provider_model="some-model"))
    record = store.get(challenge.challenge_id)
    assert record["identity"]["studio_agent_instance"] == "a1"
    assert record["identity"]["mcp_client_name"] == "cursor"
    assert record["identity"]["provider_model_source"] == "unknown"


def test_challenge_never_leaks_the_code_into_the_image_path_or_id(tmp_path):
    store = ProbeStore(tmp_path)
    challenge, _ = store.issue()
    assert challenge.code not in challenge.challenge_id
