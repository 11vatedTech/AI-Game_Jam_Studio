"""Bind human approvals to exact content.

An approval is meaningful only for the bytes that were actually reviewed. This
module derives a binding digest from the art-direction hash plus every frame
hash, then answers whether a stored review still covers the current content. No
mutable "valid" flag exists, so an edited frame or a bumped revision cannot
silently inherit yesterday's sign-off.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Iterable, Sequence

from ..errors import ValidationError
from .art_direction import ArtDirection


@dataclass(frozen=True)
class FrameRef:
    name: str
    sha256: str


def frames_digest(frames: Iterable[FrameRef]) -> str:
    """Order-independent digest of a frame set."""
    entries = sorted({"name": frame.name, "sha256": frame.sha256} for frame in frames)
    payload = json.dumps(entries, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def bind(direction: ArtDirection, frames: Iterable[FrameRef]) -> dict[str, Any]:
    """The exact content identity a gate review must match."""
    return {
        "direction_sha256": direction.sha256,
        "direction_revision": direction.revision,
        "threshold_status": direction.threshold_status,
        "frames_digest": frames_digest(frames),
    }


def approval_status(
    conn, gate: int, direction: ArtDirection, frames: Iterable[FrameRef]
) -> tuple[bool, str]:
    """Return (still valid, human-readable reason). Never raises on a stale review."""
    if gate not in (1, 2):
        raise ValidationError(f"Unknown gate: {gate}")

    binding = bind(direction, frames)
    row = conn.execute(
        "SELECT evidence_json, reviewer, created_at FROM reviews"
        " WHERE review_type=? ORDER BY created_at DESC LIMIT 1",
        (f"gate-{gate}",),
    ).fetchone()
    if row is None:
        return False, f"no gate-{gate} review is on record"

    try:
        evidence = json.loads(row["evidence_json"])
    except (TypeError, json.JSONDecodeError):
        return False, f"gate-{gate} review evidence is unreadable"

    if evidence.get("direction_sha256") != binding["direction_sha256"]:
        return False, (
            f"art direction changed since gate-{gate} approval "
            f"({evidence.get('direction_sha256')} -> {binding['direction_sha256']})"
        )
    if evidence.get("frames_digest") != binding["frames_digest"]:
        return False, f"approved frames changed since gate-{gate} approval"

    return True, f"covered by gate-{gate} review from {row['created_at']}"


def review_evidence(
    *,
    gate: int,
    direction: ArtDirection,
    frames: Sequence[FrameRef],
    method: str,
    confirmation: str | None = None,
    operator: str | None = None,
) -> dict[str, Any]:
    """Evidence payload written when a human records a gate decision."""
    if method not in ("cli-interactive", "chat-transcription"):
        raise ValidationError(f"Unknown approval method: {method}")
    if method == "chat-transcription" and not confirmation:
        raise ValidationError("A transcribed chat approval must quote the operator verbatim")

    payload = {
        "gate": gate,
        "method": method,
        # A transcribed approval is weaker evidence and is labelled as such rather than hidden.
        "confidence": "strong" if method == "cli-interactive" else "weak",
        "operator": operator,
        "confirmation": confirmation,
    }
    payload |= bind(direction, frames)
    return payload
