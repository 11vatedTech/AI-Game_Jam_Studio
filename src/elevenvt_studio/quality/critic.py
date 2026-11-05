"""Critic v1.

Judges captured frames against the art-direction contract and records findings
with their evidence. It is deliberately boring about taste: it can only say
whether a declared, versioned threshold was met, and it says "not evaluated"
rather than "passed" when the inputs for a metric are absent.

A critic that cannot be wrong is not a critic. Everything here is falsifiable by
re-running against a human-labelled frame.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Sequence

from ..policy import utc_now
from . import metrics
from .art_direction import ArtDirection

SEVERITY_ORDER = {"blocker": 3, "major": 2, "minor": 1, "note": 0}


@dataclass
class Frame:
    """One captured frame plus the sidecar facts the engine asserted about it."""

    name: str
    path: Path
    mask_path: Path | None = None
    occupancy_mask_path: Path | None = None
    lantern_mask_path: Path | None = None
    focal_mask_path: Path | None = None
    camera_roll_deg: float | None = None
    timeline_event: str | None = None
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class Finding:
    frame: str
    metric: str
    value: float | None
    severity: str
    algorithm_version: str
    confidence: float
    limitations: tuple[str, ...]
    threshold: dict[str, Any]
    detail: dict[str, Any]

    def to_row(self, job_id: str) -> dict:
        return {
            "id": str(uuid.uuid4()),
            "job_id": job_id,
            "frame": self.frame,
            "metric": self.metric,
            "value": self.value,
            "severity": self.severity,
            "algorithm_version": self.algorithm_version,
            "confidence": self.confidence,
            "threshold_json": json.dumps(self.threshold, sort_keys=True),
            "limitations_json": json.dumps(list(self.limitations)),
            "evidence_json": json.dumps(self.detail, sort_keys=True),
            "created_at": utc_now(),
        }


@dataclass
class CriticReport:
    job_id: str
    direction_revision: str
    direction_sha256: str
    threshold_status: str
    frames: list[dict]
    status: str
    findings: list[Finding]

    def to_dict(self) -> dict:
        counts = {severity: 0 for severity in SEVERITY_ORDER}
        for finding in self.findings:
            counts[finding.severity] = counts.get(finding.severity, 0) + 1
        return {
            "job_id": self.job_id,
            "direction_revision": self.direction_revision,
            "direction_sha256": self.direction_sha256,
            "threshold_status": self.threshold_status,
            "status": self.status,
            "severity_counts": counts,
            "frames": self.frames,
            "findings": [
                {
                    "frame": f.frame,
                    "metric": f.metric,
                    "value": f.value,
                    "severity": f.severity,
                    "algorithm_version": f.algorithm_version,
                    "confidence": f.confidence,
                    "threshold": f.threshold,
                    "limitations": list(f.limitations),
                    "detail": f.detail,
                }
                for f in self.findings
            ],
        }


def evaluate(frames: Sequence[Frame], direction: ArtDirection, *, job_id: str = "unassigned") -> CriticReport:
    findings: list[Finding] = []
    frame_reports: list[dict] = []

    previous: Frame | None = None
    for frame in frames:
        rgb = metrics.load_rgb(frame.path)
        world = _load_mask(frame.mask_path)
        # Coverage, not visibility: the visible-segmentation pass draws the sky and
        # therefore reports "surface" where nothing exists.
        occupancy = _load_mask(frame.occupancy_mask_path)
        lantern = _load_mask(frame.lantern_mask_path)
        focal = _load_mask(frame.focal_mask_path)

        floor = direction.threshold("luminance_floor").get("p5_min")
        values: dict[str, Any] = {}
        values["luminance_floor"] = metrics.luminance_percentiles(rgb)
        # Diagnosis travels with the measurement: a percentile can say a frame is
        # dark, never why. When the cause cannot be established it says so.
        values["luminance_cause"] = metrics.luminance_cause(rgb, occupancy, floor)
        values["warm_share"] = metrics.warm_share(rgb, world, direction.threshold("warm_share"))
        values["horizon_roll"] = metrics.horizon_roll(frame.camera_roll_deg)
        values["delta_e_max"] = metrics.palette_drift(rgb, direction.palette)
        values["clutter"] = metrics.clutter(rgb, focal)
        values["lantern_dominance"] = metrics.lantern_dominance(rgb, lantern)

        if previous is not None and previous.meta.get("pair_of") != frame.name:
            values["consistency"] = metrics.event_delta(metrics.load_rgb(previous.path), rgb)
        previous = frame

        frame_values = {}
        for metric_name, output in values.items():
            frame_values[metric_name] = {
                "value": output.value,
                "evaluated": output.evaluated,
                "algorithm_version": output.algorithm_version,
                "confidence": output.confidence,
                "limitations": list(output.limitations),
                "detail": output.detail,
            }
            threshold = direction.thresholds.get(metric_name)
            if threshold is None:
                continue
            severity = _severity(metric_name, output.value, threshold)
            if severity is None:
                continue
            findings.append(
                Finding(
                    frame=frame.name,
                    metric=metric_name,
                    value=output.value,
                    severity=severity,
                    algorithm_version=output.algorithm_version,
                    confidence=output.confidence,
                    limitations=output.limitations,
                    threshold=dict(threshold),
                    detail={
                        **output.detail,
                        "cause": values["luminance_cause"].detail
                        if metric_name == "luminance_floor"
                        else None,
                    }
                    if metric_name == "luminance_floor"
                    else output.detail,
                )
            )

        cause = values["luminance_cause"]
        findings.append(
            Finding(
                frame=frame.name,
                metric="luminance_cause",
                value=cause.value,
                severity="note",
                algorithm_version=cause.algorithm_version,
                confidence=cause.confidence,
                limitations=cause.limitations,
                threshold={},
                detail=cause.detail,
            )
        )
        frame_reports.append({"frame": frame.name, "metrics": frame_values})

    worst = max((SEVERITY_ORDER[f.severity] for f in findings), default=-1)
    status = "PASS" if worst < SEVERITY_ORDER["major"] else "FAIL"
    return CriticReport(
        job_id=job_id,
        direction_revision=direction.revision,
        direction_sha256=direction.sha256,
        threshold_status=direction.threshold_status,
        frames=frame_reports,
        status=status,
        findings=findings,
    )


def _severity(metric: str, value: float | None, threshold: dict) -> str | None:
    """Thresholds decide the verdict; absence of a value is never a pass."""
    if value is None:
        return "note"

    if metric == "luminance_floor":
        floor = threshold.get("p5_min")
        return None if floor is None or value >= floor else "major"

    if metric == "lantern_dominance":
        gap = threshold.get("min_luminance_gap", 0.0)
        if threshold.get("brightest_must_be_lantern") and value < gap:
            return "blocker" if value <= 0 else "major"
        return None

    if metric == "consistency":
        low, high = threshold.get("event_delta_min"), threshold.get("event_delta_max")
        if low is not None and value < low:
            return "major"
        if high is not None and value > high:
            return "major"
        return None

    if metric in ("silhouette", "warm_share", "horizon_roll", "delta_e_max", "clutter"):
        if metric == "silhouette":
            target, direction = threshold.get("iou_min"), "below"
        elif metric == "warm_share":
            target, direction = threshold.get("ceiling"), "above"
        elif metric == "horizon_roll":
            target, direction = threshold.get("max_deg"), "above"
        elif metric == "delta_e_max":
            target, direction = threshold.get("max"), "above"
        else:
            target, direction = threshold.get("edge_density_max"), "above"
        if target is None:
            return None
        breached = value < target if direction == "below" else value > target
        if not breached:
            return None
        blocker_key = f"blocker_{direction}"
        major_key = f"major_{direction}"
        blocker = threshold.get(blocker_key)
        if blocker is not None and (value < blocker if direction == "below" else value > blocker):
            return "blocker"
        major = threshold.get(major_key)
        if major is not None and (value < major if direction == "below" else value > major):
            return "major"
        return "minor"
    return None


def _load_mask(path: Path | None):
    if path is None:
        return None
    import numpy as np
    from PIL import Image

    with Image.open(path) as image:
        return np.asarray(image.convert("L")) > 127


def persist(db, report: CriticReport, *, job_id: str) -> None:
    """Write findings as ledger-adjacent rows; the report itself goes to evidence."""
    with db.connect() as conn:
        for finding in report.findings:
            row = finding.to_row(job_id)
            conn.execute(
                "INSERT INTO critic_findings(id,job_id,frame,metric,value,threshold_json,severity,"
                "algorithm_version,confidence,limitations_json,evidence_json,created_at)"
                " VALUES(:id,:job_id,:frame,:metric,:value,:threshold_json,:severity,"
                ":algorithm_version,:confidence,:limitations_json,:evidence_json,:created_at)",
                row,
            )


def load_sidecar(path: Path) -> dict:
    sidecar = path.with_suffix(".json")
    if sidecar.is_file():
        return json.loads(sidecar.read_text(encoding="utf-8"))
    return {}


def frames_from_directory(directory: Path, names: Iterable[str] | None = None) -> list[Frame]:
    directory = Path(directory)
    candidates = sorted(directory.glob("*.png"))
    if names:
        wanted = set(names)
        candidates = [path for path in candidates if path.name in wanted]

    frames = []
    for path in candidates:
        if path.name.endswith(".mask.png"):
            continue
        sidecar = load_sidecar(path)
        mask_path = _optional(directory / f"{path.stem}.mask.png")
        occupancy_path = _optional(directory / f"{path.stem}.occupancy.png")
        lantern_path = _optional(directory / f"{path.stem}.lantern.png")
        focal_path = _optional(directory / f"{path.stem}.focal.png")
        frames.append(
            Frame(
                name=path.name,
                path=path,
                mask_path=mask_path,
                occupancy_mask_path=occupancy_path,
                lantern_mask_path=lantern_path,
                focal_mask_path=focal_path,
                camera_roll_deg=sidecar.get("camera_roll_deg"),
                timeline_event=sidecar.get("timeline_event"),
                meta=sidecar,
            )
        )
    return frames


def _optional(path: Path) -> Path | None:
    return path if path.is_file() else None
