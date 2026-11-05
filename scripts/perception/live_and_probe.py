"""Record live-session and probe evidence for the perception subsystem.

Run: PYTHONPATH=src .venv/Scripts/python.exe scripts/perception/live_and_probe.py

Writes LIVE_CAPTURE_REPORT.json and PROBE_REPORT.json next to the deterministic
capture evidence. Nothing here claims a model can see: no vision-capable client
is connected in this environment, and the reports say so.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from elevenvt_studio.adapters.godot_capture import GodotCaptureAdapter  # noqa: E402
from elevenvt_studio.perception.bundle import GateRejected  # noqa: E402
from elevenvt_studio.perception.probe import Identity, ProbeStore, render_challenge_image  # noqa: E402

GODOT = "C:/Users/11vat/tools/ai-game-studio/godot/godot.exe"
STAGING = ROOT / "reports/evidence/_staging/emberkeep-live"
EVIDENCE = ROOT / "reports/evidence/productions/emberkeep/02-manufacture"
CONTRACT = ROOT / "Games/emberkeep/art_direction.json"


def live_capture() -> dict:
    adapter = GodotCaptureAdapter(
        godot_executable=GODOT,
        project_path=ROOT / "Games/emberkeep/game",
        captures_root=STAGING,
        workspace_root=ROOT,
        name="emberkeep",
        contract_sha256=hashlib.sha256(CONTRACT.read_bytes()).hexdigest(),
        resolution=(1920, 1080),
        timeout_seconds=180,
    )
    session = adapter.start_live(timeout=120)
    try:
        state_before = session.state()
        bundle = session.capture(["frame", "mask_lantern_visible"])
        gate_rejected = None
        try:
            bundle.require_authoritative()
            gate_rejected = {"rejected": False, "note": "GATE ACCEPTED LIVE EVIDENCE"}
        except GateRejected as exc:
            gate_rejected = {"rejected": True, "code": exc.code, "message": str(exc)}

        destination = EVIDENCE / "live"
        destination.mkdir(parents=True, exist_ok=True)
        shutil.copytree(bundle.root, destination / bundle.capture_id, dirs_exist_ok=True)

        return {
            "capture_id": bundle.capture_id,
            "mode": bundle.mode,
            "evidence_grade": bundle.evidence_grade,
            "state_before_capture": state_before,
            "verification": bundle.verify().to_dict(),
            "artifacts": bundle.summary()["artifacts"],
            "gate": gate_rejected,
            "token_acl": getattr(adapter, "live_acl", None),
            "limitations": [
                "A live bundle guides iteration and cannot satisfy a gate; this is enforced by the gate, not by the critic.",
                "The critic evaluates live captures too, but none of its findings on this bundle would be certifiable.",
            ],
        }
    finally:
        session.quit()


def probe_evidence() -> dict:
    store = ProbeStore(EVIDENCE / "probes")
    identity = Identity(studio_agent_instance="harness", mcp_client_name=None, provider_model=None)

    challenge, image = store.issue(identity)
    reuse = store.verify(challenge.challenge_id, challenge.code.upper())
    reuse_again = store.verify(challenge.challenge_id, challenge.code.upper())

    failure, failure_image = store.issue(identity)
    wrong = store.verify(failure.challenge_id, "ZZZZZZ")

    return {
        "issued": [
            {
                "challenge_id": challenge.challenge_id,
                "image_sha256": hashlib.sha256(image).hexdigest(),
                "code_never_in_text": True,
                "expires_at": challenge.expires_at,
            },
            {
                "challenge_id": failure.challenge_id,
                "image_sha256": hashlib.sha256(failure_image).hexdigest(),
            },
        ],
        "correct_answer_submitted_by": "harness, not an agent",
        "correct_answer_result": reuse,
        "reuse_attempt": reuse_again,
        "deliberate_failure": wrong,
        "interpretation": "NOT ESTABLISHED",
        "interpretation_note": (
            "The probe proves the mechanism records delivery and refusal. No vision-capable client is "
            "connected here, so no model readback has been demonstrated. A passing agent result requires "
            "a connected agent and would be recorded against its identity tuple."
        ),
        "limitations": [
            "A harness-submitted correct answer is not evidence that a model can read the image.",
            "MCP identifies the client application, not the model; model identity remains self-reported until registered.",
        ],
    }


def main() -> int:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    live = live_capture()
    (EVIDENCE / "LIVE_CAPTURE_REPORT.json").write_text(json.dumps(live, indent=2, sort_keys=True), encoding="utf-8")
    print("live:", live["capture_id"], live["evidence_grade"], live["gate"])

    probe = probe_evidence()
    (EVIDENCE / "PROBE_REPORT.json").write_text(json.dumps(probe, indent=2, sort_keys=True), encoding="utf-8")
    print("probe:", probe["deliberate_failure"], probe["reuse_attempt"])

    return 0 if live["verification"]["status"] == "verified" and live["gate"]["rejected"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
