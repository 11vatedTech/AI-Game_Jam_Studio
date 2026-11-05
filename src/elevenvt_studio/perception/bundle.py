"""Capture bundle loading and verification.

The bundle is the only thing that makes a PNG into evidence. Everything here is
adversarial: paths are confined, hashes are recomputed, dimensions are compared
against the declaration, and the evidence grade is derived rather than trusted.
A client that can write a bundle cannot thereby promote one.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping

from ..errors import StudioError, ValidationError

SCHEMA_VERSION = "2.0"


class GateRejected(StudioError):
    """Raised when non-authoritative evidence is offered to a gate.

    The critic still evaluates live and unqualified captures; only the gate is
    allowed to refuse them. Conflating the two would either silence live
    feedback or launder supervision into certification.
    """

    code = "EVIDENCE_NOT_AUTHORITATIVE"

# Role -> the semantics that role is allowed to carry. A silhouette may never be
# labelled a visibility measurement, because that is the exact mistake cull_mask
# invites: it renders objects through walls.
ROLE_SEMANTICS: dict[str, frozenset[str]] = {
    "frame": frozenset({"render"}),
    "mask_world_visible": frozenset({"visible_segmentation"}),
    "mask_player_visible": frozenset({"visible_segmentation"}),
    "mask_lantern_visible": frozenset({"visible_segmentation"}),
    "mask_lantern_silhouette": frozenset({"unoccluded_silhouette"}),
    "mask_lantern_illumination": frozenset({"illumination_delta"}),
    "diff": frozenset({"pixel_difference"}),
}

MASK_ROLES = frozenset(role for role in ROLE_SEMANTICS if role != "frame")
ALLOWED_MIME = frozenset({"image/png", "image/jpeg", "image/webp"})
# p99 linear luminance at or below this is the band the known-broken captures occupy.
BLACK_LUMINANCE = 0.002


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def compute_grade(mode: str, repeatability_status: str | None) -> str:
    """Authority is earned, never declared.

    A live capture is never authoritative. A deterministic capture only becomes
    authoritative once its repeatability qualification says so, because
    ``--fixed-fps`` pins a frame rate rather than frame content.
    """
    if mode == "live":
        return "supervisory"
    if mode == "deterministic" and repeatability_status == "qualified":
        return "authoritative"
    return "supervisory"


@dataclass(frozen=True)
class Check:
    name: str
    ok: bool
    detail: Any = None

    def to_dict(self) -> dict:
        return {"name": self.name, "ok": self.ok, "detail": self.detail}


@dataclass
class Verification:
    status: str
    checks: list[Check] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.status == "verified"

    def to_dict(self) -> dict:
        return {"status": self.status, "checks": [check.to_dict() for check in self.checks]}

    def failures(self) -> list[Check]:
        return [check for check in self.checks if not check.ok]


def _safe_relative(value: str) -> Path:
    """Reject anything that could point outside the capture directory."""
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("Artifact path must be a non-empty string")
    path = Path(value)
    if path.is_absolute() or path.drive or path.root:
        raise ValidationError(f"Artifact path must be relative: {value}")
    if any(part in {"..", ""} for part in path.parts):
        raise ValidationError(f"Artifact path traversal is refused: {value}")
    return path


def _confine(root: Path, relative: str) -> Path:
    relative_path = _safe_relative(relative)
    candidate = (root / relative_path).resolve()
    if root.resolve() not in candidate.parents:
        raise ValidationError(f"Artifact path escapes the capture directory: {relative}")
    return candidate


def _load_schema() -> dict:
    root = Path(__file__).resolve().parents[3]
    schema_path = root / "schemas" / "capture-bundle.schema.json"
    if not schema_path.is_file():
        raise ValidationError(f"Capture bundle schema is missing: {schema_path}")
    return json.loads(schema_path.read_text(encoding="utf-8"))


def validate_document(document: Mapping[str, Any]) -> None:
    import jsonschema

    try:
        jsonschema.validate(document, _load_schema())
    except jsonschema.ValidationError as exc:
        location = "/".join(str(part) for part in exc.absolute_path) or "<root>"
        raise ValidationError(f"Capture bundle schema violation at {location}: {exc.message}") from exc

    mode = document["mode"]
    qualification = document.get("qualification") or {}
    repeatability = (qualification.get("repeatability") or {}).get("status")
    expected = compute_grade(mode, repeatability)
    if document["evidence_grade"] != expected:
        raise ValidationError(
            "Evidence grade does not match its derivation "
            f"(mode={mode}, repeatability={repeatability}, declared={document['evidence_grade']}, expected={expected})"
        )

    seen: set[str] = set()
    for artifact in document["artifacts"]:
        role = artifact["role"]
        if role in seen:
            raise ValidationError(f"Duplicate artifact role: {role}")
        seen.add(role)
        if artifact["semantics"] not in ROLE_SEMANTICS[role]:
            raise ValidationError(
                f"Artifact {role} may not carry semantics {artifact['semantics']}; "
                f"allowed: {sorted(ROLE_SEMANTICS[role])}"
            )
        if artifact["mime"] not in ALLOWED_MIME:
            raise ValidationError(f"Unsupported artifact mime: {artifact['mime']}")
        _safe_relative(artifact["path"])

    declared_roles = set(document["request"]["roles"])
    if not declared_roles <= seen:
        raise ValidationError(f"Requested roles with no artifact: {sorted(declared_roles - seen)}")


class CaptureBundle:
    """A loaded bundle, bound to the directory that contains it."""

    def __init__(self, document: dict, root: Path, path: Path | None = None):
        self.document = document
        self.root = Path(root)
        self.path = path

    @classmethod
    def load(cls, path: Path | str, *, root: Path | str | None = None) -> "CaptureBundle":
        path = Path(path)
        if not path.is_file():
            raise ValidationError(f"Capture bundle does not exist: {path}")
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValidationError(f"Capture bundle is not valid JSON: {exc}") from exc
        validate_document(document)
        return cls(document, Path(root) if root is not None else path.parent, path)

    # -- accessors ---------------------------------------------------------
    @property
    def capture_id(self) -> str:
        return self.document["capture_id"]

    @property
    def mode(self) -> str:
        return self.document["mode"]

    @property
    def evidence_grade(self) -> str:
        return self.document["evidence_grade"]

    @property
    def authoritative(self) -> bool:
        return self.evidence_grade == "authoritative"

    def artifact(self, role: str) -> dict:
        for artifact in self.document["artifacts"]:
            if artifact["role"] == role:
                return artifact
        raise ValidationError(f"Capture {self.capture_id} has no artifact with role {role}")

    def has(self, role: str) -> bool:
        return any(artifact["role"] == role for artifact in self.document["artifacts"])

    def image_path(self, role: str) -> Path:
        return _confine(self.root, self.artifact(role)["path"])

    def roles(self) -> list[str]:
        return [artifact["role"] for artifact in self.document["artifacts"]]

    def require_authoritative(self) -> None:
        """Refuse this evidence at a gate unless authority was earned."""
        if self.authoritative:
            return
        qualification = (self.document.get("qualification") or {}).get("repeatability") or {}
        raise GateRejected(
            f"Capture {self.capture_id} is {self.evidence_grade} and cannot satisfy a gate"
            + (" (live observation is supervision only)" if self.mode == "live" else
               f" (repeatability: {qualification.get('status', 'not_run')})"),
            details={
                "capture_id": self.capture_id,
                "mode": self.mode,
                "evidence_grade": self.evidence_grade,
                "repeatability": qualification.get("status", "not_run"),
            },
        )

    def summary(self) -> dict:
        return {
            "capture_id": self.capture_id,
            "mode": self.mode,
            "evidence_grade": self.evidence_grade,
            "authoritative": self.authoritative,
            "resolution": self.document["application"]["resolution"],
            "physics_tick": self.document["request"]["physics_tick"],
            "render_frame": self.document["request"]["render_frame"],
            "artifacts": [
                {
                    "role": artifact["role"],
                    "semantics": artifact["semantics"],
                    "sha256": artifact["sha256"],
                    "bytes": artifact["bytes"],
                    "width": artifact["width"],
                    "height": artifact["height"],
                }
                for artifact in self.document["artifacts"]
            ],
        }

    # -- verification ------------------------------------------------------
    def verify(self, *, expect_black: bool | None = None) -> Verification:
        from PIL import Image

        checks: list[Check] = []
        declared_width, declared_height = self.document["application"]["resolution"]
        expect_black = (
            self.document["request"].get("expect_black", False) if expect_black is None else expect_black
        )

        sizes: dict[str, tuple[int, int]] = {}
        for artifact in self.document["artifacts"]:
            role = artifact["role"]
            try:
                path = _confine(self.root, artifact["path"])
            except ValidationError as exc:
                checks.append(Check(f"{role}:path", False, str(exc)))
                continue
            if not path.is_file():
                checks.append(Check(f"{role}:exists", False, "missing file"))
                continue

            checks.append(Check(f"{role}:exists", True))
            actual_hash = _sha256_file(path)
            checks.append(
                Check(f"{role}:sha256", actual_hash == artifact["sha256"], {"declared": artifact["sha256"], "actual": actual_hash})
            )
            actual_bytes = path.stat().st_size
            checks.append(Check(f"{role}:bytes", actual_bytes == artifact["bytes"], {"declared": artifact["bytes"], "actual": actual_bytes}))

            try:
                with Image.open(path) as image:
                    image.load()
                    mime = Image.MIME.get(image.format or "", "")
                    size = image.size
                    mode = image.mode
                    pixels = image.convert("L") if role in MASK_ROLES else None
                    histogram = pixels.histogram() if pixels is not None else None
                    rgb = image.convert("RGB") if role == "frame" else None
                    rgb_array = None
                    if rgb is not None:
                        import numpy as np

                        rgb_array = np.asarray(rgb)
            except Exception as exc:  # noqa: BLE001 - reported as a failed check
                checks.append(Check(f"{role}:decodes", False, str(exc)))
                continue

            checks.append(Check(f"{role}:decodes", True, {"format": mime, "mode": mode}))
            checks.append(Check(f"{role}:mime", mime == artifact["mime"], {"declared": artifact["mime"], "actual": mime}))
            checks.append(
                Check(
                    f"{role}:dimensions",
                    size == (artifact["width"], artifact["height"]),
                    {"declared": [artifact["width"], artifact["height"]], "actual": list(size)},
                )
            )
            sizes[role] = size

            if role in MASK_ROLES and histogram is not None:
                non_binary = sum(histogram[3:253])
                checks.append(
                    Check(f"{role}:binary", non_binary == 0, {"non_binary_pixels": non_binary, "rule": "values must be 0 or 255"})
                )

            if role == "frame" and rgb_array is not None:
                from ..quality import metrics

                # metrics.luminance already linearises; doing it twice would shrink every
                # frame towards zero and report real captures as black.
                luminance = metrics.luminance(rgb_array)
                p99 = float(__import__("numpy").percentile(luminance, 99))
                if expect_black:
                    checks.append(Check("frame:blackness", True, {"p99": p99, "expected_black": True}))
                else:
                    checks.append(
                        Check(
                            "frame:blackness",
                            p99 > BLACK_LUMINANCE,
                            {"p99_linear_luminance": round(p99, 6), "floor": BLACK_LUMINANCE},
                        )
                    )

        frame_size = sizes.get("frame")
        for role, size in sizes.items():
            if role in MASK_ROLES and frame_size is not None:
                checks.append(Check(f"{role}:frame_dimensions", size == frame_size, {"mask": list(size), "frame": list(frame_size)}))

        declared_roles = set(self.document["request"]["roles"])
        checks.append(Check("roles:declared", declared_roles <= set(sizes) | {a["role"] for a in self.document["artifacts"]}))

        ok = all(check.ok for check in checks)
        status = "verified" if ok else "failed"
        return Verification(status=status, checks=checks)
