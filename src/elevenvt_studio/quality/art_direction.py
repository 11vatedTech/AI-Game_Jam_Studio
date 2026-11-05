"""Load and validate the art-direction contract.

Thresholds are data. Nothing in this module or in the critic may hard-code a
taste decision; every ceiling, band and palette value is read from the versioned
artifact so a change is a reviewable diff with a new hash.

Validation is deliberately strict and fails with a JSON path, because a typo in
a threshold silently changes what the studio accepts as good work.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from ..errors import ValidationError

SCHEMA_PATH = Path(__file__).resolve().parents[3] / "schemas" / "art-direction.schema.json"
PALETTE_ROLES = ("ink", "slate", "mist", "bone", "lantern", "ember")
THRESHOLD_KEYS = (
    "silhouette",
    "warm_share",
    "horizon_roll",
    "delta_e_max",
    "clutter",
    "lantern_dominance",
    "consistency",
)
THRESHOLD_STATUSES = ("provisional", "confirmed")


@dataclass(frozen=True)
class Reference:
    id: str
    path: str
    sha256: str
    reviewer: str | None = None
    notes: str | None = None


@dataclass(frozen=True)
class ArtDirection:
    """Immutable view of a validated contract."""

    revision: str
    schema_version: str
    production: str
    threshold_status: str
    palette: tuple[str, ...]
    roles: Mapping[str, int]
    thresholds: Mapping[str, Mapping[str, Any]]
    capture: Mapping[str, Any]
    references: tuple[Reference, ...]
    path: Path
    sha256: str

    @property
    def is_confirmed(self) -> bool:
        return self.threshold_status == "confirmed"

    def threshold(self, metric: str) -> Mapping[str, Any]:
        try:
            return self.thresholds[metric]
        except KeyError as exc:  # pragma: no cover - guarded by schema
            raise ValidationError(f"Metric '{metric}' is not declared in the art direction") from exc

    def role_hex(self, role: str) -> str:
        return self.palette[self.roles[role]]


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_schema() -> dict:
    if not SCHEMA_PATH.is_file():
        raise ValidationError(f"Art-direction schema is missing: {SCHEMA_PATH}")
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _format_path(error) -> str:
    parts = [str(p) for p in error.absolute_path]
    return "$" + "".join(f"[{p}]" if p.isdigit() else f".{p}" for p in parts)


def validate_document(document: Mapping[str, Any]) -> None:
    """Schema-validate a parsed contract, raising ValidationError with a JSON path."""
    try:
        import jsonschema
    except ModuleNotFoundError as exc:  # pragma: no cover - dependency is declared
        raise ValidationError("jsonschema is required to validate the art direction") from exc

    try:
        jsonschema.validate(instance=document, schema=_load_schema())
    except jsonschema.ValidationError as error:
        raise ValidationError(
            f"Art direction is invalid at {_format_path(error)}: {error.message}",
            details={"path": _format_path(error)},
        ) from error

    _validate_semantics(document)


def _validate_semantics(document: Mapping[str, Any]) -> None:
    palette = document["palette"]
    base = palette["base"]
    roles = palette["roles"]

    if len(set(hex_value.upper() for hex_value in base)) != len(base):
        raise ValidationError(
            "Art direction is invalid at $.palette.base: palette swatches must be unique",
            details={"path": "$.palette.base"},
        )

    indices = list(roles.values())
    if len(set(indices)) != len(indices):
        raise ValidationError(
            "Art direction is invalid at $.palette.roles: each role must map to a distinct swatch",
            details={"path": "$.palette.roles"},
        )
    if sorted(indices) != list(range(len(base))):
        raise ValidationError(
            "Art direction is invalid at $.palette.roles: roles must cover every swatch exactly once",
            details={"path": "$.palette.roles"},
        )

    status = document["threshold_status"]
    if status not in THRESHOLD_STATUSES:
        raise ValidationError(
            f"Art direction is invalid at $.threshold_status: unknown status '{status}'",
            details={"path": "$.threshold_status"},
        )
    if status == "confirmed" and "calibration" not in document:
        raise ValidationError(
            "Art direction is invalid at $.threshold_status: a confirmed contract requires a calibration record",
            details={"path": "$.threshold_status"},
        )

    hue = document["thresholds"]["warm_share"]["hue_deg"]
    if hue[0] >= hue[1]:
        raise ValidationError(
            "Art direction is invalid at $.thresholds.warm_share.hue_deg: hue range must be ascending",
            details={"path": "$.thresholds.warm_share.hue_deg"},
        )

    ids = [reference["id"] for reference in document["references"]]
    if len(set(ids)) != len(ids):
        raise ValidationError(
            "Art direction is invalid at $.references: reference ids must be unique",
            details={"path": "$.references"},
        )

    resolution = document["capture"]["resolution"]
    legibility = document["capture"]["legibility_resolution"]
    if legibility[0] > resolution[0] or legibility[1] > resolution[1]:
        raise ValidationError(
            "Art direction is invalid at $.capture.legibility_resolution: it must not exceed resolution",
            details={"path": "$.capture.legibility_resolution"},
        )


def load(path: Path, *, verify_references: bool = True) -> ArtDirection:
    """Load, validate and hash a contract. Never returns a partially valid object."""
    path = Path(path).expanduser().resolve()
    if not path.is_file():
        raise ValidationError(f"Art direction not found: {path}")

    raw = path.read_bytes()
    try:
        document = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise ValidationError(f"Art direction is not valid JSON: {exc}") from exc

    validate_document(document)

    references = tuple(
        Reference(
            id=entry["id"],
            path=entry["path"],
            sha256=entry["sha256"],
            reviewer=entry.get("reviewer"),
            notes=entry.get("notes"),
        )
        for entry in document["references"]
    )
    direction = ArtDirection(
        revision=document["revision"],
        schema_version=document["schema_version"],
        production=document["production"],
        threshold_status=document["threshold_status"],
        palette=tuple(hex_value.upper() for hex_value in document["palette"]["base"]),
        roles={role: document["palette"]["roles"][role] for role in PALETTE_ROLES},
        thresholds={key: dict(document["thresholds"][key]) for key in THRESHOLD_KEYS},
        capture=dict(document["capture"]),
        references=references,
        path=path,
        sha256=hashlib.sha256(raw).hexdigest(),
    )

    if verify_references:
        assert_reference_hashes(direction, path.parent)
    return direction


def assert_reference_hashes(direction: ArtDirection, base: Path) -> None:
    """A reference frame that no longer matches its declared hash invalidates the review."""
    base = Path(base).resolve()
    problems = []
    for reference in direction.references:
        reference_path = (base / reference.path).resolve()
        if not reference_path.is_file():
            problems.append(f"{reference.id}: missing at {reference_path}")
            continue
        actual = _sha256_file(reference_path)
        if actual != reference.sha256:
            problems.append(f"{reference.id}: sha256 mismatch (declared {reference.sha256}, actual {actual})")
    if problems:
        raise ValidationError(
            "Art-direction references do not match their declared hashes: " + "; ".join(problems),
            details={"path": "$.references", "problems": problems},
        )
