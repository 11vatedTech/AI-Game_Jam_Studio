"""Fixtures for perception tests.

Bundles are built by hand here on purpose: a fixture produced by the same code
that writes real bundles would only prove the writer agrees with itself.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from pathlib import Path

from PIL import Image, ImageDraw

from elevenvt_studio.perception.bundle import ROLE_SEMANTICS


def sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_frame(path: Path, size: tuple[int, int] = (320, 180), base: int = 40) -> Path:
    """A gradient frame: uniform images compress unrealistically and hide encoder bugs."""
    image = Image.new("RGB", size)
    draw = ImageDraw.Draw(image)
    for x in range(size[0]):
        value = base + (x * 60) // size[0]
        draw.line([(x, 0), (x, size[1])], fill=(value, value + 20, value + 40))
    image.save(path, format="PNG", optimize=True)
    return path


def write_mask(path: Path, size: tuple[int, int] = (320, 180), box: tuple[int, int, int, int] | None = None) -> Path:
    image = Image.new("L", size, 0)
    draw = ImageDraw.Draw(image)
    x0, y0, x1, y1 = box or (60, 40, 120, 100)
    draw.rectangle([x0, y0, x1, y1], fill=255)
    image.save(path, format="PNG", optimize=True)
    return path


def make_bundle(
    root: Path,
    *,
    mode: str = "deterministic",
    repeatability: str | None = "qualified",
    roles: tuple[str, ...] = ("frame",),
    frame_size: tuple[int, int] = (320, 180),
    frame_base: int = 40,
    mask_size: tuple[int, int] | None = None,
    declared_grade: str | None = None,
    mutate: dict | None = None,
    extra: dict | None = None,
) -> Path:
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)

    grade = declared_grade or ("supervisory" if mode == "live" else "authoritative" if repeatability == "qualified" else "supervisory")
    artifacts = []
    for role in roles:
        if role == "frame":
            path = write_frame(root / "frame.png", frame_size, frame_base)
            semantics = "render"
            mime = "image/png"
        else:
            size = mask_size or frame_size
            path = write_mask(root / f"{role}.png", size)
            semantics = next(iter(ROLE_SEMANTICS[role]))
            mime = "image/png"
        with Image.open(path) as image:
            dimensions = image.size
        artifacts.append(
            {
                "role": role,
                "semantics": semantics,
                "path": path.name,
                "sha256": sha256(path),
                "width": dimensions[0],
                "height": dimensions[1],
                "mime": mime,
                "bytes": path.stat().st_size,
                "derived_from": None,
            }
        )

    document = {
        "schema_version": "2.0",
        "capture_id": str(uuid.uuid4()),
        "mode": mode,
        "evidence_grade": grade,
        "application": {
            "name": "emberkeep",
            "adapter_version": "1.0.0",
            "engine_version": "4.7.2.stable",
            "project_path": "Games/emberkeep/game",
            "rendering_method": "forward_plus",
            "requested_resolution": [1920, 1080],
            "resolution": [frame_size[0], frame_size[1]],
            "msaa_3d": 2,
            "screen_space_aa": 1,
            "stretch_mode": "canvas_items",
        },
        "request": {
            "roles": list(roles),
            "physics_tick": 180,
            "render_frame": 182,
            "camera": {"side": "west"},
            "state": {"lantern_lit": True},
            "seed": 20261105,
        },
        "artifacts": artifacts,
        "provenance": {
            "contract_sha256": "0" * 64,
            "plan_sha256": None,
            "git": {"commit": "0" * 40, "dirty": False, "tree_sha256": None, "untracked_or_patch_sha256": None},
            "engine": {"version": "4.7.2.stable", "executable_sha256": None},
            "gpu": None,
            "settings": {"fixed_fps": 60},
            "host": "win32",
            "started_at": "2026-11-05T00:00:00+00:00",
            "finished_at": "2026-11-05T00:00:01+00:00",
            "duration_ms": 1000,
        },
        "verification": {"status": "unverified", "checks": []},
    }
    if mode == "deterministic":
        document["qualification"] = {
            "repeatability": {
                "status": repeatability,
                "runs": 3 if repeatability else 0,
                "state_digest": None,
                "render_contract": "exact_sha256" if repeatability == "qualified" else None,
                "tolerance": None,
                "measured_max_delta": None,
            }
        }
    if mutate:
        for dotted, value in mutate.items():
            target = document
            parts = dotted.split(".")
            for part in parts[:-1]:
                target = target[int(part)] if isinstance(target, list) else target[part]
            key = parts[-1]
            if isinstance(target, list):
                target[int(key)] = value
            else:
                target[key] = value
    if extra:
        document.update(extra)

    path = root / "bundle.json"
    path.write_text(json.dumps(document, indent=2, sort_keys=True), encoding="utf-8")
    return path
