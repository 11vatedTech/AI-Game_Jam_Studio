"""Image transport: turn an artifact into something a model can actually receive.

The authoritative original is never re-encoded. Transport copies are derived,
sized against a declared profile, and refused rather than truncated when they
cannot fit — a silently downscaled image is a measurement the agent did not make.
"""

from __future__ import annotations

import base64
import hashlib
import io
import json
import math
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Sequence

from ..errors import StudioError
from .bundle import CaptureBundle, MASK_ROLES

# The fidelity envelope. Below these a transport copy stops being a faithful view
# of the evidence, so the answer is a refusal plus a crop, never a blurrier image.
MIN_SCALE = 0.5
MIN_QUALITY = 60
FRAME_FORMAT = "JPEG"
MASK_FORMAT = "PNG"


class TransportLimitExceeded(StudioError):
    code = "TRANSPORT_LIMIT_EXCEEDED"


@dataclass(frozen=True)
class TransportProfile:
    """A client/model transport profile.

    Named and versioned so a capability qualification can later supply measured
    profiles per agent instead of one invented global maximum.
    """

    id: str
    max_image_bytes: int
    max_width: int
    max_height: int
    max_long_edge: int
    max_visual_tokens: int | None
    supported_formats: tuple[str, ...]
    preferred_frame_format: str
    mask_format: str
    max_images_per_call: int
    max_total_payload_bytes: int

    def as_dict(self) -> dict:
        data = asdict(self)
        data["supported_formats"] = list(self.supported_formats)
        return data

    def fit(self, width: int, height: int) -> tuple[int, int]:
        scale = 1.0
        long_edge = max(width, height)
        if long_edge > self.max_long_edge:
            scale = self.max_long_edge / long_edge
        scale = min(scale, self.max_width / width, self.max_height / height)
        if scale >= 1.0:
            return width, height
        return max(1, int(round(width * scale))), max(1, int(round(height * scale)))


DEFAULT_PROFILE = TransportProfile(
    id="studio-default-v1",
    max_image_bytes=1_572_864,  # 1.5 MiB encoded block
    max_width=2560,
    max_height=2560,
    max_long_edge=2560,
    max_visual_tokens=None,
    supported_formats=("PNG", "JPEG", "WEBP"),
    preferred_frame_format="JPEG",
    mask_format="PNG",
    max_images_per_call=6,
    max_total_payload_bytes=6_291_456,  # 6 MiB of base64 across one call
)


@dataclass
class TransportArtifact:
    role: str
    path: str
    sha256: str
    source_sha256: str
    width: int
    height: int
    format: str
    mime: str
    quality: int | None
    scale: float
    bytes: int
    base64_bytes: int
    profile_id: str

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass
class TransportResult:
    artifacts: list[TransportArtifact] = field(default_factory=list)
    text: str = ""
    blocks: list[dict] = field(default_factory=list)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _encode(image, fmt: str, quality: int | None) -> bytes:
    buffer = io.BytesIO()
    if fmt == "JPEG":
        image.convert("RGB").save(buffer, format="JPEG", quality=quality or 85, optimize=True, subsampling=1)
    elif fmt == "WEBP":
        image.convert("RGB").save(buffer, format="WEBP", quality=quality or 85, method=4)
    else:
        image.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()


def _ladder(role: str) -> Iterable[tuple[float, int | None]]:
    """Ordered attempts within the declared envelope, largest fidelity first."""
    if role in MASK_ROLES:
        # Masks are lossless or they are not measurements. Scale only, never quality.
        for scale in (1.0, 0.85, 0.7, 0.6, MIN_SCALE):
            yield scale, None
        return
    for scale in (1.0, 0.85, 0.7, 0.6, MIN_SCALE):
        for quality in (85, 75, 65, MIN_QUALITY):
            yield scale, quality


def prepare(
    bundle: CaptureBundle,
    role: str,
    *,
    out_dir: Path,
    profile: TransportProfile = DEFAULT_PROFILE,
) -> TransportArtifact:
    from PIL import Image

    artifact = bundle.artifact(role)
    source = bundle.image_path(role)
    source_hash = artifact["sha256"]

    with Image.open(source) as opened:
        opened.load()
        original = opened.copy()

    fmt = MASK_FORMAT if role in MASK_ROLES else FRAME_FORMAT
    if fmt not in profile.supported_formats:
        raise TransportLimitExceeded(
            f"Profile {profile.id} does not support {fmt}",
            details={"role": role, "format": fmt, "supported": list(profile.supported_formats)},
        )

    attempts: list[dict] = []
    chosen: tuple[bytes, int, int, int | None, float] | None = None
    for scale, quality in _ladder(role):
        width = max(1, int(round(original.width * scale)))
        height = max(1, int(round(original.height * scale)))
        # The profile's own long-edge/width/height limits are a hard cap on top of the ladder.
        cap_width, cap_height = profile.fit(width, height)
        if (cap_width, cap_height) != (width, height):
            scale = min(scale, cap_width / width)
            width, height = cap_width, cap_height
        if max(width, height) > profile.max_long_edge:
            attempts.append({"scale": scale, "quality": quality, "skipped": "long edge"})
            continue
        if profile.max_visual_tokens is not None:
            estimated = math.ceil((width * height) / 750)
            if estimated > profile.max_visual_tokens:
                attempts.append({"scale": scale, "quality": quality, "skipped": f"visual tokens {estimated}"})
                continue
        resized = original if (width, height) == (original.width, original.height) else original.resize(
            (width, height), Image.LANCZOS
        )
        data = _encode(resized, fmt, quality)
        attempts.append({"scale": scale, "quality": quality, "bytes": len(data)})
        if len(data) <= profile.max_image_bytes:
            chosen = (data, width, height, quality, scale)
            break

    if chosen is None:
        raise TransportLimitExceeded(
            f"Artifact {role} cannot fit profile {profile.id} within the fidelity envelope "
            f"(scale >= {MIN_SCALE}, quality >= {MIN_QUALITY}, {profile.max_image_bytes} bytes). "
            "Request a crop instead of a lossier image.",
            details={"role": role, "profile": profile.id, "attempts": attempts},
        )

    data, width, height, quality, scale = chosen
    out_dir.mkdir(parents=True, exist_ok=True)
    extension = "jpg" if fmt == "JPEG" else fmt.lower()
    target = out_dir / f"{role}.{extension}"
    target.write_bytes(data)

    encoded = base64.b64encode(data)
    return TransportArtifact(
        role=role,
        path=str(target.name),
        sha256=_sha256(data),
        source_sha256=source_hash,
        width=width,
        height=height,
        format=fmt,
        mime="image/jpeg" if fmt == "JPEG" else f"image/{fmt.lower()}",
        quality=quality,
        scale=round(scale, 4),
        bytes=len(data),
        base64_bytes=len(encoded),
        profile_id=profile.id,
    )


def summarize(bundle: CaptureBundle, transports: Sequence[TransportArtifact], verification: dict) -> str:
    """Compact text block. Contains every hash so the model can cite what it saw."""
    lines = [
        f"capture_id: {bundle.capture_id}",
        f"mode: {bundle.mode}",
        f"evidence_grade: {bundle.evidence_grade}",
        f"authoritative: {str(bundle.authoritative).lower()}",
        f"resolution: {bundle.document['application']['resolution'][0]}x{bundle.document['application']['resolution'][1]}",
        f"physics_tick: {bundle.document['request']['physics_tick']}",
        f"render_frame: {bundle.document['request']['render_frame']}",
        f"verification: {verification.get('status', 'unverified')}",
        "artifacts:",
    ]
    for item in transports:
        lines.append(
            f"  - {item.role} ({bundle.artifact(item.role)['semantics']}): "
            f"source_sha256={item.source_sha256} transport_sha256={item.sha256} "
            f"{item.width}x{item.height} {item.format}"
            + (f" q{item.quality}" if item.quality is not None else "")
            + f" scale={item.scale} bytes={item.bytes}"
        )
        if item.scale != 1.0:
            lines.append(f"    note: downscaled to {item.scale:.0%} of the authoritative pixels; request perception_crop for 1:1 detail")
    if not bundle.authoritative:
        lines.append(
            "authority: this bundle is SUPERVISORY. It may guide iteration and it cannot satisfy a gate."
            if bundle.mode == "live"
            else "authority: this bundle is SUPERVISORY because repeatability is not qualified. It cannot satisfy a gate."
        )
    return "\n".join(lines)


def prepare_all(
    bundle: CaptureBundle,
    roles: Sequence[str],
    *,
    out_dir: Path,
    profile: TransportProfile = DEFAULT_PROFILE,
    verification: dict | None = None,
) -> TransportResult:
    if len(roles) > profile.max_images_per_call:
        raise TransportLimitExceeded(
            f"Requested {len(roles)} images but profile {profile.id} allows {profile.max_images_per_call}",
            details={"roles": list(roles), "max_images_per_call": profile.max_images_per_call},
        )

    artifacts: list[TransportArtifact] = []
    blocks: list[dict] = []
    for role in roles:
        item = prepare(bundle, role, out_dir=out_dir, profile=profile)
        artifacts.append(item)
        data = (out_dir / item.path).read_bytes()
        blocks.append(
            {
                "type": "image",
                "data": base64.b64encode(data).decode("ascii"),
                "mimeType": item.mime,
                # No annotations: audience declares an intended audience, and a
                # user-only image is the wrong signal for content a model must see.
            }
        )

    total = sum(item.base64_bytes for item in artifacts)
    if total > profile.max_total_payload_bytes:
        raise TransportLimitExceeded(
            f"Transport payload {total} bytes exceeds profile {profile.id} limit {profile.max_total_payload_bytes}",
            details={"roles": list(roles), "base64_bytes": total, "limit": profile.max_total_payload_bytes},
        )

    manifest = {
        "profile": profile.as_dict(),
        "capture_id": bundle.capture_id,
        "artifacts": [item.as_dict() for item in artifacts],
        "total_base64_bytes": total,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "transport.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    text = summarize(bundle, artifacts, verification or {})
    return TransportResult(artifacts=artifacts, text=text, blocks=blocks)
