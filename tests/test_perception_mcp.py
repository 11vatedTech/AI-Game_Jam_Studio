"""Phase A: the image must survive the real tool-call path.

These tests are the gate from the plan. They assert the wire shape, not the
internal return value: text plus image blocks, no structuredContent, no audience
annotation, and a hash the model can cite.
"""

import base64
import json
import re
import uuid
from pathlib import Path

import pytest
from PIL import Image

from elevenvt_studio.mcp.server import MCPServer
from elevenvt_studio.perception.tools import to_call_tool_result
from perception_support import make_bundle


def install(service, **kwargs) -> str:
    capture_id = str(uuid.uuid4())
    directory = Path(service.config.evidence_root) / "captures" / capture_id
    make_bundle(directory, mutate={"capture_id": capture_id}, **kwargs)
    return capture_id


def call(service, name, arguments):
    server = MCPServer(service)
    response = server.handle(
        {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": name, "arguments": arguments}}
    )
    assert "error" not in response, response
    return response["result"]


def test_tools_list_advertises_perception_tools(service):
    server = MCPServer(service)
    listed = server.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})["result"]["tools"]
    names = {tool["name"] for tool in listed}
    assert {
        "perception_capture",
        "perception_get",
        "perception_crop",
        "perception_probe",
        "perception_probe_verify",
    } <= names


def test_real_tool_call_returns_an_image_block_and_no_structured_content(service):
    capture_id = install(service)
    result = call(service, "perception_get", {"capture_id": capture_id, "role": "frame"})

    assert "structuredContent" not in result
    assert result["isError"] is False
    assert result["content"][0]["type"] == "text"
    assert "capture_id" in result["content"][0]["text"]

    images = [block for block in result["content"] if block["type"] == "image"]
    assert len(images) == 1
    image = images[0]
    assert "annotations" not in image
    assert image["mimeType"] in {"image/jpeg", "image/png"}

    decoded = base64.b64decode(image["data"])
    assert decoded[:2] in {b"\xff\xd8", b"\x89P"}
    with Image.open(__import__("io").BytesIO(decoded)) as opened:
        assert opened.size[0] > 0

    transport_sha = re.search(r"transport_sha256=([0-9a-f]{64})", result["content"][0]["text"]).group(1)
    import hashlib

    assert hashlib.sha256(decoded).hexdigest() == transport_sha


def test_text_block_cites_the_authoritative_source_hash(service):
    capture_id = install(service)
    result = call(service, "perception_get", {"capture_id": capture_id, "role": "frame"})
    text = result["content"][0]["text"]
    bundle = json.loads((Path(service.config.evidence_root) / "captures" / capture_id / "bundle.json").read_text())
    assert bundle["artifacts"][0]["sha256"] in text


def test_authoritative_bundle_is_labelled_authoritative(service):
    capture_id = install(service, roles=("frame",))
    result = call(service, "perception_get", {"capture_id": capture_id, "role": "frame"})
    text = result["content"][0]["text"]
    assert "evidence_grade: authoritative" in text
    assert "authoritative: true" in text


def test_live_bundle_is_labelled_supervisory_in_the_text_block(service):
    capture_id = install(service, mode="live", declared_grade="supervisory")
    result = call(service, "perception_get", {"capture_id": capture_id, "role": "frame"})
    text = result["content"][0]["text"]
    assert "evidence_grade: supervisory" in text
    assert "SUPERVISORY" in text
    assert "cannot satisfy a gate" in text


def test_verification_failure_is_reported_without_hiding_the_image(service):
    capture_id = install(service)
    Image.new("RGB", (320, 180), (1, 1, 1)).save(
        Path(service.config.evidence_root) / "captures" / capture_id / "frame.png", format="PNG"
    )
    result = call(service, "perception_get", {"capture_id": capture_id, "role": "frame"})
    text = result["content"][0]["text"]
    assert "verification: FAILED" in text
    assert "frame:sha256" in text
    assert any(block["type"] == "image" for block in result["content"])


def test_probe_round_trip_through_the_tool_surface(service):
    result = call(service, "perception_probe", {"agent_instance": "phase-a"})
    text = result["content"][0]["text"]
    challenge_id = re.search(r"challenge_id: (\S+)", text).group(1)
    assert "structuredContent" not in result

    store = json.loads((Path(service.config.evidence_root) / "probes" / "probes.json").read_text())
    code = store["challenges"][challenge_id]["code"]
    assert code not in text

    verified = call(service, "perception_probe_verify", {"challenge_id": challenge_id, "answer": code})
    payload = json.loads(verified["content"][0]["text"])
    assert payload["verified"] is True


def test_unknown_capture_is_a_tool_error_not_an_empty_success(service):
    server = MCPServer(service)
    response = server.handle(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": "perception_get", "arguments": {"capture_id": str(uuid.uuid4()), "role": "frame"}},
        }
    )
    assert response["result"]["isError"] is True


def test_explicit_call_tool_result_has_no_structured_content_and_no_annotations(service):
    capture_id = install(service)
    from elevenvt_studio.perception.tools import PerceptionTools

    response = PerceptionTools(service).get({"capture_id": capture_id, "role": "frame"})
    result = to_call_tool_result(response)

    assert result.structured_content is None
    assert result.content[0].type == "text"
    assert result.content[1].type == "image"
    assert getattr(result.content[1], "annotations", None) is None


def test_sdk_server_registers_perception_tools(service):
    pytest.importorskip("mcp")
    from elevenvt_studio.mcp.sdk_server import build_server

    server = build_server(service)
    manager = getattr(server, "_tool_manager", None) or getattr(server, "tool_manager", None)
    assert manager is not None, "cannot locate the SDK tool registry"
    names = set(manager._tools)
    assert "perception_get" in names
    assert "perception_probe_verify" in names
