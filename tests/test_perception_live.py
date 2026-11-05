"""Live session: supervision that works, and authority it cannot obtain.

Properties asserted against a real engine process: authentication precedes every
operation, oversized input and unknown ops are refused and recorded, and a live
capture is verifiable but never gate-eligible.
"""

import json
import os
import shutil
import socket
from pathlib import Path

import pytest

from elevenvt_studio.adapters.godot_capture import GodotCaptureAdapter, LiveSession
from elevenvt_studio.perception.bundle import GateRejected

FIXTURE = Path("tests/godot/mask_fixture")
SERVICE = Path("Games/emberkeep/game/scripts/capture/service.gd")


def godot_executable() -> str:
    candidate = os.environ.get("GODOT_EXECUTABLE", "C:/Users/11vat/tools/ai-game-studio/godot/godot.exe")
    if not Path(candidate).is_file():
        pytest.skip(f"Godot executable not found at {candidate}")
    return candidate


@pytest.fixture(scope="module")
def live(tmp_path_factory):
    """One running game, no pre-authenticated client: each test connects itself."""
    root = tmp_path_factory.mktemp("live_session")
    project = root / "proj"
    shutil.copytree(FIXTURE, project)
    (project / "scripts").mkdir(exist_ok=True)
    shutil.copy(SERVICE, project / "scripts" / "service.gd")
    adapter = GodotCaptureAdapter(
        godot_executable=godot_executable(),
        project_path=project,
        captures_root=root / "captures",
        workspace_root=Path.cwd(),
        name="mask_fixture_live",
        timeout_seconds=180,
    )
    bootstrap = adapter.start_live(timeout=120)
    # The bootstrap connection authenticated us; release the single session slot
    # so each test can exercise its own connection.
    bootstrap.close()
    yield adapter
    try:
        adapter.live_process.terminate()
        adapter.live_process.wait(timeout=10)
    except Exception:
        pass


def session_port(adapter) -> int:
    return int(json.loads((adapter.captures_root / "session.json").read_text())["port"])


def expect_closed(raw: socket.socket) -> None:
    """A refusal may be a clean close or a reset; both mean no response was served."""
    try:
        assert raw.recv(65536) == b""
    except (ConnectionResetError, ConnectionAbortedError):
        pass


def test_unauthenticated_operation_is_refused(live):
    with socket.create_connection(("127.0.0.1", session_port(live)), timeout=10) as raw:
        raw.sendall((json.dumps({"op": "state"}) + "\n").encode())
        expect_closed(raw)


def test_wrong_token_is_refused(live):
    with socket.create_connection(("127.0.0.1", session_port(live)), timeout=10) as raw:
        raw.sendall((json.dumps({"op": "hello", "token": "0" * 64}) + "\n").encode())
        expect_closed(raw)


def test_oversized_line_is_refused(live):
    with socket.create_connection(("127.0.0.1", session_port(live)), timeout=10) as raw:
        raw.sendall(b"x" * 70000)
        expect_closed(raw)


def test_unknown_operation_is_refused_but_session_survives(live):
    with LiveSession.connect(live.captures_root, live.live_token, timeout=30) as session:
        reply = session.request({"op": "evaluate", "python": "print(1)"})
        assert reply["ok"] is False
        assert reply["error"] == "unknown_op"
        assert session.request({"op": "state"})["ok"] is True


def test_live_capture_verifies_but_is_never_gate_eligible(live):
    session = LiveSession.connect(live.captures_root, live.live_token, timeout=30)
    try:
        bundle = session.capture(["frame", "mask_lantern_visible"])
        assert bundle.mode == "live"
        assert bundle.evidence_grade == "supervisory"
        assert bundle.verify().ok
        assert bundle.document.get("qualification") is None
        with pytest.raises(GateRejected) as excinfo:
            bundle.require_authoritative()
        assert excinfo.value.code == "EVIDENCE_NOT_AUTHORITATIVE"
    finally:
        session.close()


def test_refusals_are_recorded(live):
    denials = live.captures_root / "live-denials.jsonl"
    assert denials.is_file()
    reasons = {json.loads(line)["reason"] for line in denials.read_text().splitlines() if line.strip()}
    assert {"auth_required", "bad_token", "line_too_long", "unknown_op"} <= reasons
