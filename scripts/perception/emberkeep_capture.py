"""Run the Emberkeep perception acceptance capture and record its evidence.

Run: PYTHONPATH=src .venv/Scripts/python.exe scripts/perception/emberkeep_capture.py

Produces, under reports/evidence/productions/emberkeep/02-manufacture/:
  captures/<capture_id>/...        the qualified bundle and its artifacts
  CAPTURE_REPORT.json              three-run hashes and the qualification verdict
  CRITIC_REPORT.json               the critic's findings on that frame
  TRANSPORT_REPORT.json            what an agent would actually receive
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from elevenvt_studio.adapters.godot_capture import (  # noqa: E402
    GodotCaptureAdapter,
    apply_qualification,
    qualify,
)
from elevenvt_studio.perception.bundle import CaptureBundle  # noqa: E402
from elevenvt_studio.perception.tools import PerceptionTools  # noqa: E402
from elevenvt_studio.perception.transport import DEFAULT_PROFILE, prepare_all  # noqa: E402
from elevenvt_studio.quality import art_direction, critic  # noqa: E402

GODOT = "C:/Users/11vat/tools/ai-game-studio/godot/godot.exe"
CAPTURES = ROOT / "reports/evidence/_staging/emberkeep-captures"
EVIDENCE = ROOT / "reports/evidence/productions/emberkeep/02-manufacture"
CONTRACT = ROOT / "Games/emberkeep/art_direction.json"

REPORT_ROLES = [
    "frame",
    "mask_world_occupancy",
    "mask_world_visible",
    "mask_lantern_visible",
    "mask_lantern_silhouette",
    "mask_lantern_illumination",
]
# Paired light controls: the same frozen frame with one mechanism held back. Captured
# and qualified with everything else, but kept out of the default per-call transport,
# which carries the six images an agent needs to look at the scene.
CONTROL_ROLES = [
    "light_control_all",
    "light_control_direct",
    "light_control_environment",
    "light_control_emissive",
]
ROLES = REPORT_ROLES + CONTROL_ROLES
RUNS = 3


def make_adapter() -> GodotCaptureAdapter:
    return GodotCaptureAdapter(
        godot_executable=GODOT,
        project_path=ROOT / "Games/emberkeep/game",
        captures_root=CAPTURES,
        workspace_root=ROOT,
        name="emberkeep",
        contract_sha256=hashlib.sha256(CONTRACT.read_bytes()).hexdigest(),
        resolution=(1920, 1080),
        warmup_frames=30,
        timeout_seconds=300,
    )


def main() -> int:
    EVIDENCE.mkdir(parents=True, exist_ok=True)

    bundles: list[CaptureBundle] = []
    for index in range(RUNS):
        bundle = make_adapter().capture(roles=ROLES)
        bundles.append(bundle)
        print(f"run {index + 1}: {bundle.capture_id} frame={bundle.artifact('frame')['sha256'][:16]}")

    qualification = qualify(bundles, runs=RUNS)
    qualified = [apply_qualification(bundle, qualification) for bundle in bundles]
    print("qualification:", json.dumps(qualification, indent=2))

    winner = qualified[0]
    destination = EVIDENCE / "captures" / winner.capture_id
    if destination.exists():
        shutil.rmtree(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(winner.root, destination)

    # Re-verify the copied bundle: a copy that no longer hashes is not evidence.
    copied = CaptureBundle.load(destination / "bundle.json", root=destination)
    verification = copied.verify()

    report = {
        "capture_id": copied.capture_id,
        "evidence_grade": copied.evidence_grade,
        "qualification": qualification,
        "runs": [
            {
                "capture_id": bundle.capture_id,
                "artifacts": {role: bundle.artifact(role)["sha256"] for role in bundle.roles()},
            }
            for bundle in qualified
        ],
        "copied_verification": verification.to_dict(),
        "artifacts": copied.summary()["artifacts"],
        "limitations": [
            "Repeatability is established on this machine only; cross-machine reproducibility is not claimed.",
            "Masks are produced by a two-pass construction derived from documented render semantics, not by an official Godot mask feature.",
            "This capture is not a packaging test: it does not prove the exported game renders at 1080p.",
            (
                "Repeatability is within-batch. The frame and five of the six masks reproduce exactly across separate "
                "capture invocations, but mask_lantern_illumination does not: it is a difference of two renders taken "
                "later in the frozen frame, so any shader that advances with time (volumetric fog) shifts it. Derived "
                "difference artifacts are therefore not yet cross-batch stable, and nothing in the critic depends on "
                "that mask today."
            ),
        ],
    }
    (EVIDENCE / "CAPTURE_REPORT.json").write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")

    direction = art_direction.load(CONTRACT)
    frame = critic.Frame(
        name="frame.png",
        path=copied.image_path("frame"),
        mask_path=copied.image_path("mask_world_visible") if copied.has("mask_world_visible") else None,
        occupancy_mask_path=copied.image_path("mask_world_occupancy")
        if copied.has("mask_world_occupancy")
        else None,
        lantern_mask_path=copied.image_path("mask_lantern_visible") if copied.has("mask_lantern_visible") else None,
        light_controls={
            role.removeprefix("light_control_"): copied.image_path(role)
            for role in CONTROL_ROLES
            if copied.has(role)
        },
    )
    critic_report = critic.evaluate([frame], direction, job_id=f"perception-{copied.capture_id}")
    critic_document = critic_report.to_dict()
    critic_document["evidence_grade"] = copied.evidence_grade
    critic_document["gate_eligible"] = copied.authoritative
    (EVIDENCE / "CRITIC_REPORT.json").write_text(
        json.dumps(critic_document, indent=2, sort_keys=True), encoding="utf-8"
    )

    transport = prepare_all(
        copied,
        REPORT_ROLES,
        out_dir=EVIDENCE / "transport",
        profile=DEFAULT_PROFILE,
        verification=verification.to_dict(),
    )
    transport_report = {
        "profile": DEFAULT_PROFILE.as_dict(),
        "roles_not_transported": {
            role: "light control evidence for the illumination measurement; retrievable by role, not part of the per-call payload"
            for role in CONTROL_ROLES
        },
        "blocks": [
            {"type": block["type"], "mimeType": block["mimeType"], "base64_bytes": len(block["data"])}
            for block in transport.blocks
        ],
        "artifacts": [artifact.as_dict() for artifact in transport.artifacts],
        "response_has_structured_content": False,
        "response_has_audience_annotation": False,
        "text_block": transport.text,
    }
    (EVIDENCE / "TRANSPORT_REPORT.json").write_text(
        json.dumps(transport_report, indent=2, sort_keys=True), encoding="utf-8"
    )

    print("verification:", verification.status)
    print("critic:", critic_report.status, [finding.metric for finding in critic_report.findings])
    print("transport blocks:", len(transport.blocks))
    return 0 if verification.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
