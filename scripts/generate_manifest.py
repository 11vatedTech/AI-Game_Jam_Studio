#!/usr/bin/env python3
"""Generate a deterministic SHA-256 manifest for repository source and handoff files.

The manifest covers exactly the Git-tracked files (``git ls-files``), so local-only
scratch, virtual environments and gitignored machine output can never leak into
a committed integrity record. A filesystem walk is not used: it previously
absorbed scratch directories and ~116 MiB of gitignored local ComfyUI output.
"""
from __future__ import annotations
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "FILE_MANIFEST.json"
# Kept as documentation of what must never appear in the manifest; the tracked-
# file enumeration below already excludes all of these.
EXCLUDED_PARTS = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", ".ruff_cache", "build", "dist", ".mypy_cache"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _tracked_files() -> list[Path]:
    """Return the sorted tracked files under ROOT, excluding the manifest itself."""
    proc = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, check=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    paths = []
    for entry in proc.stdout.split(b"\0"):
        if not entry:
            continue
        rel = entry.decode("utf-8")
        if rel == OUTPUT.name:
            continue
        candidate = ROOT / rel
        # ls-files can list submodules as gitlinks; hash only real files.
        if candidate.is_file() and not candidate.is_symlink():
            paths.append(candidate)
    return sorted(paths, key=lambda p: p.relative_to(ROOT).as_posix())


def main() -> int:
    files = []
    for path in _tracked_files():
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
