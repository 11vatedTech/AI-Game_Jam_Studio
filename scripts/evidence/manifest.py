"""Hash-addressed evidence manifest.

Large generation outputs stay out of git; their identity does not. This tool
hashes every file under an evidence directory into a manifest that is
committed, so the bytes can live on disk (or be regenerated) while any change,
loss or substitution is still detectable.

Usage:
    python scripts/evidence/manifest.py build  --root reports/evidence --output reports/evidence/ARTIFACTS.sha256
    python scripts/evidence/manifest.py verify --root reports/evidence --manifest reports/evidence/ARTIFACTS.sha256
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

CHUNK = 1024 * 1024
SKIP_NAMES = {"ARTIFACTS.sha256"}


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(CHUNK), b""):
            digest.update(block)
    return digest.hexdigest()


def iter_files(root: Path, exclude: set[str]):
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        if path.name in SKIP_NAMES or rel in exclude:
            continue
        yield rel, path


def build(root: Path, output: Path, exclude: set[str]) -> dict:
    entries = []
    for rel, path in iter_files(root, exclude):
        entries.append({"path": rel, "size_bytes": path.stat().st_size, "sha256": file_sha256(path)})
    payload = {
        "kind": "evidence-manifest",
        "version": 1,
        "root": root.as_posix(),
        "file_count": len(entries),
        "total_bytes": sum(e["size_bytes"] for e in entries),
        "files": entries,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def verify(root: Path, manifest: Path) -> dict:
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    missing, modified, extra = [], [], []
    recorded = {e["path"]: e for e in payload["files"]}
    for rel, entry in recorded.items():
        path = root / rel
        if not path.is_file():
            missing.append(rel)
        elif file_sha256(path) != entry["sha256"]:
            modified.append(rel)
    for rel, _ in iter_files(root, set()):
        if rel not in recorded:
            extra.append(rel)
    return {
        "status": "PASS" if not missing and not modified else "FAIL",
        "expected_files": len(recorded),
        "missing": missing,
        "modified": modified,
        "unrecorded": extra,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Hash-addressed evidence manifest")
    parser.add_argument("command", choices=["build", "verify"])
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--manifest", type=Path, default=None)
    parser.add_argument("--exclude", action="append", default=[])
    args = parser.parse_args(argv)

    root = args.root.resolve()
    if not root.is_dir():
        print(f"error: evidence root not found: {root}", file=sys.stderr)
        return 2

    if args.command == "build":
        output = (args.output or root / "ARTIFACTS.sha256").resolve()
        payload = build(root, output, set(args.exclude))
        print(json.dumps({"written": str(output), "file_count": payload["file_count"],
                          "total_bytes": payload["total_bytes"]}, indent=2))
        return 0

    manifest = (args.manifest or root / "ARTIFACTS.sha256").resolve()
    if not manifest.is_file():
        print(f"error: manifest not found: {manifest}", file=sys.stderr)
        return 2
    result = verify(root, manifest)
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
