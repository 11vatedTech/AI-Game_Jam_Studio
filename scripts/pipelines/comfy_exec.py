"""Bounded ComfyUI workflow runner for studio pipeline work.

This is a thin, auditable driver: it expands declared placeholders in an API-format
workflow, submits it, polls history, and downloads declared outputs. It intentionally
does not perform quality judgement; that belongs to the evidence/review layer.

Usage:
    python scripts/pipelines/comfy_exec.py --workflow workflows/generation/flux2_klein_txt2img.api.json \
        --set PROMPT="..." --set WIDTH=1024 --set HEIGHT=1024 --set SEED=7 \
        --set STEPS=8 --set CFG=1.0 --set PREFIX=studio/hero \
        --out-dir reports/evidence/runs/<run-id>
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BASE = os.environ.get("COMFYUI_URL", "http://127.0.0.1:8188").rstrip("/")
_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def _request(path: str, *, method: str = "GET", body: dict | None = None, timeout: float = 30.0):
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(BASE + path, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    with _OPENER.open(req, timeout=timeout) as response:
        raw = response.read()
    return json.loads(raw) if raw else {}


def load_workflow(path: Path) -> dict:
    raw = json.loads(path.read_text(encoding="utf-8"))
    graph = {k: v for k, v in raw.items() if not k.startswith("_")}
    if not graph:
        raise SystemExit(f"Workflow {path} contains no nodes")
    return graph


def substitute(graph: dict, values: dict[str, str]) -> dict:
    """Replace string placeholders such as '__WIDTH__' with typed JSON values."""
    def cast(token: str, value: str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value

    def walk(node):
        if isinstance(node, dict):
            return {k: walk(v) for k, v in node.items()}
        if isinstance(node, list):
            return [walk(v) for v in node]
        if isinstance(node, str):
            for key, value in values.items():
                token = f"__{key}__"
                if node == token:
                    return cast(key, value)
            out = node
            for key, value in values.items():
                out = out.replace(f"__{key}__", str(value))
            return out
        return node

    return walk(graph)


def unresolved(graph: dict) -> list[str]:
    found: set[str] = set()

    def walk(node):
        if isinstance(node, dict):
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)
        elif isinstance(node, str):
            found.update(re.findall(r"__[A-Z0-9_]+__", node))

    walk(graph)
    return sorted(found)


def upload_image(path: Path) -> str:
    """Upload an image into ComfyUI's input folder via its multipart endpoint."""
    import uuid
    if not path.is_file():
        raise SystemExit(f"Input image not found: {path}")
    boundary = "----studio" + uuid.uuid4().hex
    body = bytearray()
    body += f"--{boundary}\r\n".encode()
    body += f'Content-Disposition: form-data; name="image"; filename="{path.name}"\r\n'.encode()
    body += b"Content-Type: application/octet-stream\r\n\r\n"
    body += path.read_bytes()
    body += (f"\r\n--{boundary}\r\n"
             'Content-Disposition: form-data; name="overwrite"\r\n\r\ntrue\r\n'
             f"--{boundary}--\r\n").encode()
    req = urllib.request.Request(BASE + "/upload/image", data=bytes(body), method="POST",
                                 headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    with _OPENER.open(req, timeout=120) as response:
        result = json.loads(response.read() or b"{}")
    name = result.get("name")
    if not name:
        raise SystemExit(f"ComfyUI upload failed: {result}")
    subfolder = result.get("subfolder") or ""
    return f"{subfolder}/{name}" if subfolder else name


def submit(graph: dict, client_id: str = "11vatedtech-studio") -> str:
    result = _request("/prompt", method="POST", body={"prompt": graph, "client_id": client_id}, timeout=60)
    prompt_id = result.get("prompt_id")
    if not prompt_id:
        raise SystemExit(f"ComfyUI rejected the workflow: {json.dumps(result)[:2000]}")
    return prompt_id


def wait(prompt_id: str, timeout: float, interval: float = 1.5) -> dict:
    deadline = time.monotonic() + timeout
    last: dict = {}
    while time.monotonic() < deadline:
        history = _request(f"/history/{urllib.parse.quote(prompt_id)}", timeout=30)
        record = history.get(prompt_id) if isinstance(history, dict) else None
        if isinstance(record, dict):
            last = record
            status = record.get("status") or {}
            state = str(status.get("status_str", "")).lower()
            if state in {"error", "failed"}:
                raise SystemExit(f"Workflow failed: {json.dumps(status)[:3000]}")
            if status.get("completed"):
                return record
        time.sleep(interval)
    raise SystemExit(f"Timed out after {timeout}s: {json.dumps(last)[:2000]}")


def outputs(record: dict) -> list[dict]:
    found: list[dict] = []

    def walk(node, node_id="?"):
        if isinstance(node, dict):
            if isinstance(node.get("filename"), str) and node.get("type") == "output":
                found.append({"node_id": node_id, **node})
                return
            for v in node.values():
                walk(v, node_id)
        elif isinstance(node, list):
            for v in node:
                walk(v, node_id)

    for node_id, payload in (record.get("outputs") or {}).items():
        walk(payload, str(node_id))
    return found


def download(item: dict, out_dir: Path) -> Path:
    params = urllib.parse.urlencode({
        "filename": item["filename"],
        "subfolder": item.get("subfolder", ""),
        "type": item.get("type", "output"),
    })
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / item["filename"]
    with _OPENER.open(BASE + "/view?" + params, timeout=120) as response:
        data = response.read()
    target.write_bytes(data)
    return target


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workflow", required=True, type=Path)
    parser.add_argument("--set", action="append", default=[], metavar="KEY=VALUE")
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--timeout", type=float, default=1800.0)
    parser.add_argument("--interval", type=float, default=1.5)
    parser.add_argument("--image", action="append", default=[], metavar="NAME=PATH",
                        help="Upload a local image into ComfyUI input and bind NAME to it")
    parser.add_argument("--no-wait", action="store_true",
                        help="Submit and print the prompt id without polling (long reconstructions)")
    args = parser.parse_args()

    values: dict[str, str] = {}
    for item in args.set:
        if "=" not in item:
            raise SystemExit(f"--set expects KEY=VALUE, got {item!r}")
        key, value = item.split("=", 1)
        values[key.upper()] = value

    uploads = []
    for item in args.image:
        if "=" not in item:
            raise SystemExit(f"--image expects NAME=PATH, got {item!r}")
        key, source = item.split("=", 1)
        uploaded = upload_image(Path(source))
        values[key.upper()] = uploaded
        uploads.append(uploaded)

    graph = substitute(load_workflow(args.workflow), values)
    missing = unresolved(graph)
    if missing:
        raise SystemExit(f"Unresolved placeholders: {missing}")

    workflow_sha = hashlib.sha256(json.dumps(graph, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    started = time.time()
    prompt_id = submit(graph)
    if args.no_wait:
        print(json.dumps({"prompt_id": prompt_id, "workflow_sha256": workflow_sha, "submitted": True}))
        return 0
    record = wait(prompt_id, args.timeout, args.interval)
    elapsed = round(time.time() - started, 2)

    files = []
    for item in outputs(record):
        path = download(item, args.out_dir)
        files.append({
            "path": str(path),
            "bytes": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "node_id": item["node_id"],
        })

    manifest = {
        "workflow": str(args.workflow),
        "workflow_sha256": workflow_sha,
        "prompt_id": prompt_id,
        "elapsed_seconds": elapsed,
        "values": values,
        "uploads": uploads,
        "outputs": files,
    }
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "run.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
