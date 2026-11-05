"""Capture one frame and print the critic's metrics against the contract.

Run: PYTHONPATH=src .venv/Scripts/python.exe scripts/perception/preview_lighting.py

This is the tuning loop for grade work. It is deliberately not evidence: one
unqualified run in a temporary directory proves nothing about repeatability.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from elevenvt_studio.adapters.godot_capture import GodotCaptureAdapter  # noqa: E402
from elevenvt_studio.quality import art_direction, critic  # noqa: E402

GODOT = "C:/Users/11vat/tools/ai-game-studio/godot/godot.exe"
CONTRACT = ROOT / "Games/emberkeep/art_direction.json"
STAGING = ROOT / "reports/evidence/_staging/emberkeep-preview"


def main() -> int:
    adapter = GodotCaptureAdapter(
        godot_executable=GODOT,
        project_path=ROOT / "Games/emberkeep/game",
        captures_root=STAGING,
        workspace_root=ROOT,
        name="emberkeep-preview",
        contract_sha256=hashlib.sha256(CONTRACT.read_bytes()).hexdigest(),
        resolution=(1280, 720),
        warmup_frames=30,
        timeout_seconds=300,
    )
    bundle = adapter.capture(
        roles=["frame", "mask_world_visible", "mask_lantern_visible"]
    )
    direction = art_direction.load(CONTRACT)
    frame = critic.Frame(
        name="frame.png",
        path=bundle.image_path("frame"),
        mask_path=bundle.image_path("mask_world_visible"),
        lantern_mask_path=bundle.image_path("mask_lantern_visible"),
    )
    report = critic.evaluate([frame], direction, job_id="preview").to_dict()
    metrics = report["frames"][0]["metrics"]

    print(f"{'metric':22s} {'value':>10s} {'budget':>10s}  status")
    for name, entry in sorted(metrics.items()):
        threshold = direction.thresholds.get(name)
        budget = threshold.get("p5_min") if name == "luminance_floor" else None
        if budget is None and isinstance(threshold, dict):
            for key in ("max", "ceiling", "edge_density_max", "max_deg"):
                if key in threshold:
                    budget = threshold[key]
                    break
        value = entry["value"]
        shown = "n/a" if value is None else f"{value:.4f}"
        limit = "n/a" if budget is None else f"{float(budget):.4f}"
        state = "refused" if entry["value"] is None else ""
        print(f"{name:22s} {shown:>10s} {limit:>10s}  {state}")

    findings = {f["metric"]: f["severity"] for f in report["findings"]}
    print("\nstatus:", report["status"], "| findings:", json.dumps(findings, sort_keys=True))
    detail = report["frames"][0]["metrics"]["luminance_floor"]["detail"]
    print("luminance p5:", round(detail["p5"], 5), "p50:", round(detail["p50"], 5))
    print("frame:", bundle.image_path("frame"))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
