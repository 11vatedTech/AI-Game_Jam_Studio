#!/usr/bin/env python3
"""Local SBOM and license audit from installed distribution metadata.

Reads importlib.metadata for every installed distribution in the current
environment and records name, version, declared license and the license files
shipped with the distribution. This is a workstation inventory, not a claim
about what a clean install would contain; regenerate after dependency changes.

Usage:
    .venv/Scripts/python.exe scripts/release/sbom.py --out reports/validation/sbom-<date>.json
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.metadata
import json
import sys
from pathlib import Path


def _license(dist: importlib.metadata.Distribution) -> str:
    expression = (dist.metadata.get("License-Expression") or "").strip()
    if expression:
        return expression
    declared = dist.metadata.get("License") or ""
    classifiers = dist.metadata.get_all("Classifier") or []
    osi = sorted({c.split("::", 2)[-1].strip() for c in classifiers if "License :: OSI Approved" in c})
    if osi:
        return "; ".join(osi)
    return declared.strip() or "UNKNOWN"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    packages = []
    for dist in sorted(importlib.metadata.distributions(), key=lambda d: (d.metadata["Name"] or "").lower()):
        name = dist.metadata["Name"] or "UNKNOWN"
        files = []
        try:
            for item in (dist.files or []):
                text = str(item)
                if text.endswith((".dist-info/LICENSE", ".dist-info/LICENCE", ".dist-info/LICENSE.txt",
                                   ".dist-info/LICENCE.txt", ".dist-info/COPYING")):
                    files.append(text)
        except Exception:
            pass
        packages.append({"name": name, "version": dist.version, "license": _license(dist),
                         "license_files": sorted(files)})

    direct = {"mcp", "pytest", "jsonschema", "numpy", "pillow", "scikit-image", "psutil"}
    unknown = [p["name"] for p in packages if p["license"] == "UNKNOWN"]

    report = {"generator": "scripts/release/sbom.py",
              "python": sys.version.split()[0],
              "package_count": len(packages),
              "direct_runtime_dependencies": sorted(direct),
              "packages": packages,
              "unknown_license": unknown}
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(payload, encoding="utf-8")
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    print(f"Wrote {args.out} with {len(packages)} packages "
          f"({len(unknown)} unknown licenses) sha256={digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
