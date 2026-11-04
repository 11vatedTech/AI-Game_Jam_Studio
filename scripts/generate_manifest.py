#!/usr/bin/env python3
"""Generate a deterministic SHA-256 manifest for repository source and handoff files."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "FILE_MANIFEST.json"
EXCLUDED_PARTS = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", ".ruff_cache", "build", "dist", ".mypy_cache"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    files = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or path == OUTPUT:
            continue
        if any(part in EXCLUDED_PARTS for part in path.relative_to(ROOT).parts):
            continue
        if path.suffix in {".pyc", ".pyo"}:
            continue
        files.append({
            "path": path.relative_to(ROOT).as_posix(),
            "size_bytes": path.stat().st_size,
            "sha256": sha256(path),
        })
    manifest = {
        "repository": "11vatedTech/AI-Game_Jam_Studio",
        "release": (ROOT / "VERSION").read_text(encoding="utf-8").strip(),
        "generated_for": "source and handoff integrity; excludes Git metadata, caches, virtual environments and itself",
        "file_count_excluding_manifest": len(files),
        "file_count_including_manifest": len(files) + 1,
        "files": files,
    }
    OUTPUT.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT.relative_to(ROOT)} with {len(files)} file hashes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
