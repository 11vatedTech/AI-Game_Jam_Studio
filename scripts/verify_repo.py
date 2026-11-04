#!/usr/bin/env python3
"""Repository integrity checks; all checks are local and read-only."""
from __future__ import annotations
import json, pathlib, re, sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
errors=[]; json_count=0; md_count=0; link_count=0
for path in ROOT.rglob("*.json"):
    if ".git" in path.parts or ".venv" in path.parts: continue
    try: json.loads(path.read_text(encoding="utf-8")); json_count+=1
    except Exception as exc: errors.append(f"JSON {path.relative_to(ROOT)}: {exc}")
for path in ROOT.rglob("*.md"):
    if ".git" in path.parts or ".venv" in path.parts: continue
    md_count+=1; content=path.read_text(encoding="utf-8")
    for match in re.finditer(r"(?<!!)\[[^\]]*\]\(([^)]+)\)",content):
        target=match.group(1).strip().split()[0].strip("<>")
        if target.startswith(("http://","https://","mailto:","#")): continue
        target=target.split("#",1)[0]
        if not target: continue
        link_count+=1
        candidate=(path.parent/target).resolve()
        if not candidate.exists(): errors.append(f"Broken Markdown link in {path.relative_to(ROOT)}: {target}")
cap=json.loads((ROOT/"catalogs/runtime/capabilities.json").read_text(encoding="utf-8"))["capabilities"]
ids=[item["id"] for item in cap]
if len(ids)!=len(set(ids)): errors.append("Duplicate runtime capability IDs")
required={"id","domain","description","side_effect","scope","status","version"}
for item in cap:
    missing=required-set(item)
    if missing: errors.append(f"Capability {item.get('id')}: missing {sorted(missing)}")
try:
    import yaml
    for path in ROOT.rglob("*.yaml"):
        if ".git" in path.parts or ".venv" in path.parts: continue
        yaml.safe_load(path.read_text(encoding="utf-8"))
except ImportError:
    print("NOTE: PyYAML not installed; YAML parse skipped")
except Exception as exc: errors.append(f"YAML parse: {exc}")
if errors:
    print("FAIL: repository verification")
    for item in errors: print(" -",item)
    raise SystemExit(1)
print(f"PASS: {json_count} JSON files, {md_count} Markdown files, {link_count} local Markdown links, {len(cap)} runtime capability records")
