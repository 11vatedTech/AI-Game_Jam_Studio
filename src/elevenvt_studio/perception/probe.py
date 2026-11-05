"""Cooperative perception probe.

An image reaching the MCP boundary proves nothing about the model. The probe
issues a code inside an image that never appears in any text block, then accepts
the answer through a separate call. It is the only claim this subsystem makes
about delivery: bytes arrived and were processed into output.

Identity is recorded as separate fields and never merged. A model that names
itself has told us what it was configured to say; only the probe result is
evidence about seeing.
"""

from __future__ import annotations

import hmac
import json
import secrets
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from ..errors import NotFound, ValidationError

CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no I, O, 0, 1: misreading is not a perception result
CODE_LENGTH = 6
CHALLENGE_TTL_SECONDS = 180
STORE_NAME = "probes.json"


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class Identity:
    """Provenance fields, kept distinct so none can impersonate another."""

    studio_agent_instance: str | None = None
    mcp_client_name: str | None = None
    mcp_client_version: str | None = None
    provider_model: str | None = None
    model_version: str | None = None
    provider_model_source: str = "unknown"  # registered | self_reported | unknown

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass
class Challenge:
    challenge_id: str
    code: str
    created_at: str
    expires_at: str
    identity: dict
    used: bool = False
    result: dict | None = None


def _atomic_write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    temporary.replace(path)


def render_challenge_image(code: str, width: int = 720, height: int = 240) -> bytes:
    """Draw the code large and high-contrast.

    The code is the only thing in the image. Nothing decodable is hidden in it, so
    a model that answers correctly has read pixels rather than metadata.
    """
    import io

    from PIL import Image, ImageDraw, ImageFont

    image = Image.new("RGB", (width, height), (8, 12, 16))
    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.load_default(size=110)
    except TypeError:  # pragma: no cover - older Pillow
        font = ImageFont.load_default()

    spacing = 18
    widths = []
    for character in code:
        box = draw.textbbox((0, 0), character, font=font)
        widths.append(box[2] - box[0])
    total = sum(widths) + spacing * (len(code) - 1)
    x = (width - total) // 2
    for character, character_width in zip(code, widths):
        draw.text((x, height // 2 - 70), character, font=font, fill=(242, 236, 222))
        x += character_width + spacing
    draw.rectangle([0, 0, width - 1, height - 1], outline=(90, 110, 120), width=2)

    buffer = io.BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()


class ProbeStore:
    """File-backed challenge store.

    Small enough to avoid a schema migration, strict enough that a challenge
    cannot be reused, guessed by repetition, or answered after it expires.
    """

    def __init__(self, root: Path | str):
        self.root = Path(root)
        self.path = self.root / STORE_NAME

    def _read(self) -> dict:
        if not self.path.is_file():
            return {"challenges": {}}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            # A corrupted store must not silently become an empty one: that would
            # turn every outstanding challenge into an unexplained pass.
            raise ValidationError(f"Probe store is corrupt: {self.path}")

    def _write(self, payload: dict) -> None:
        _atomic_write(self.path, payload)

    def issue(self, identity: Identity | None = None) -> tuple[Challenge, bytes]:
        identity = identity or Identity()
        code = "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))
        created = _now()
        challenge = Challenge(
            challenge_id=str(uuid.uuid4()),
            code=code,
            created_at=created.isoformat(),
            expires_at=(created + timedelta(seconds=CHALLENGE_TTL_SECONDS)).isoformat(),
            identity=identity.as_dict(),
        )
        payload = self._read()
        payload["challenges"][challenge.challenge_id] = asdict(challenge)
        self._write(payload)
        return challenge, render_challenge_image(code)

    def verify(self, challenge_id: str, answer: str) -> dict:
        payload = self._read()
        record = payload["challenges"].get(challenge_id)
        if record is None:
            raise NotFound(f"Unknown probe challenge: {challenge_id}")

        challenge = Challenge(**record)
        if challenge.used:
            return {"verified": False, "reason": "reused", "challenge_id": challenge_id}

        challenge.used = True
        if _now() > datetime.fromisoformat(challenge.expires_at):
            challenge.result = {"verified": False, "reason": "expired"}
            payload["challenges"][challenge_id] = asdict(challenge)
            self._write(payload)
            return {"verified": False, "reason": "expired", "challenge_id": challenge_id}

        supplied = (answer or "").strip().upper()
        matched = hmac.compare_digest(supplied, challenge.code)
        challenge.result = {
            "verified": matched,
            "reason": "match" if matched else "mismatch",
            "answered_at": _now().isoformat(),
        }
        payload["challenges"][challenge_id] = asdict(challenge)
        self._write(payload)
        return {
            "verified": matched,
            "reason": challenge.result["reason"],
            "challenge_id": challenge_id,
            "identity": challenge.identity,
        }

    def get(self, challenge_id: str) -> dict:
        payload = self._read()
        record = payload["challenges"].get(challenge_id)
        if record is None:
            raise NotFound(f"Unknown probe challenge: {challenge_id}")
        return record
