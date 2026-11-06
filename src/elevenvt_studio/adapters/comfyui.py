from __future__ import annotations
import ipaddress, json, os, re, urllib.error, urllib.parse, urllib.request
from pathlib import Path
from .base import AdapterHealth
from ..errors import AdapterUnavailable, ValidationError, PermissionDenied, UncertainSideEffect


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Prevent a local service from redirecting the adapter to a remote host."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _local_opener():
    # Never route loopback application traffic through ambient HTTP proxy settings.
    return urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())


class ComfyUIAdapter:
    """Native ComfyUI HTTP API adapter. Queue acceptance is not generation completion."""
    adapter_id = "comfyui"
    def __init__(self, base_url: str, timeout: float=8.0):
        self.base_url=base_url.rstrip("/"); self.timeout=timeout
        parsed=urllib.parse.urlparse(self.base_url)
        if parsed.scheme not in {"http","https"} or not parsed.hostname or parsed.username or parsed.password:
            raise ValidationError("ComfyUI URL must be an http(s) URL without embedded credentials")
        self.hostname=parsed.hostname
    @property
    def is_loopback(self) -> bool:
        if self.hostname.lower()=="localhost": return True
        try: return ipaddress.ip_address(self.hostname).is_loopback
        except ValueError: return False
    def _request(self, path: str, *, method="GET", body=None, timeout=None, max_response_bytes: int=64*1024*1024):
        if not self.is_loopback: raise PermissionDenied("Non-loopback ComfyUI hosts are unsupported by this release")
        if not path.startswith("/") or path.startswith("//"):
            raise ValidationError("ComfyUI API paths must be absolute paths on the configured loopback origin")
        url=self.base_url+path
        data=None if body is None else json.dumps(body).encode("utf-8")
        req=urllib.request.Request(url,data=data,method=method,headers={"Content-Type":"application/json"})
        try:
            with _local_opener().open(req,timeout=timeout or self.timeout) as response:
                declared=response.headers.get("Content-Length")
                if declared and int(declared)>max_response_bytes:
                    raise AdapterUnavailable("ComfyUI response exceeds the configured safety limit",details={"url":url,"max_bytes":max_response_bytes})
                raw=response.read(max_response_bytes+1)
                if len(raw)>max_response_bytes:
                    raise AdapterUnavailable("ComfyUI response exceeds the configured safety limit",details={"url":url,"max_bytes":max_response_bytes})
                return json.loads(raw) if raw else {}
        except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
            raise AdapterUnavailable(f"ComfyUI request failed: {exc}",details={"url":url}) from exc
    def health(self) -> dict:
        stats=self._request("/system_stats")
        queue=self._request("/queue")
        return {"adapter":self.adapter_id,"status":"CONNECTED","system_stats":stats,"queue":queue}
    def inventory(self) -> dict:
        info=self._request("/object_info",timeout=30)
        if not isinstance(info,dict): raise AdapterUnavailable("ComfyUI /object_info returned an unexpected structure")
        models={}
        for folder in ("checkpoints","loras","vae","controlnet","upscale_models","embeddings"):
            try: models[folder]=self._request("/models/"+folder,timeout=15)
            except AdapterUnavailable as exc: models[folder]={"unavailable":str(exc)}
        return {"adapter":self.adapter_id,"node_count":len(info),"node_types":sorted(info.keys()),"models":models}
    def queue_prompt(self, prompt: dict, client_id: str | None=None) -> dict:
        if not isinstance(prompt,dict) or not prompt: raise ValidationError("ComfyUI prompt must be a non-empty API-format workflow object")
        if len(json.dumps(prompt).encode("utf-8")) > 16*1024*1024: raise ValidationError("ComfyUI workflow exceeds the 16 MiB request limit")
        payload={"prompt":prompt}
        if client_id: payload["client_id"]=client_id
        try:
            result=self._request("/prompt",method="POST",body=payload,timeout=30)
        except AdapterUnavailable as exc:
            raise UncertainSideEffect("ComfyUI submission outcome is uncertain; inspect queue/history before retrying",details=exc.details) from exc
        if not result.get("prompt_id"): raise UncertainSideEffect("ComfyUI returned no prompt_id; inspect its queue before retrying",details={"response":result})
        return result
    def queue(self) -> dict: return self._request("/queue")
    def interrupt(self, *, clear_queue: bool = False) -> dict:
        """Interrupt the running prompt; optionally clear pending queue entries.

        Work the server already finished is preserved; callers must inspect
        history afterwards rather than assume nothing happened.
        """
        before = self.queue()
        self._request("/interrupt", method="POST", body={}, timeout=15)
        if clear_queue:
            self._request("/queue", method="DELETE", timeout=15)
        after = self.queue()
        return {"interrupted": True, "queue_cleared": bool(clear_queue),
                "running_before": len(before.get("queue_running", [])),
                "pending_before": len(before.get("queue_pending", [])),
                "running_after": len(after.get("queue_running", [])),
                "pending_after": len(after.get("queue_pending", []))}
    def validate_workflow(self, prompt: dict) -> dict:
        """Structural validation of an API-format workflow graph, without executing it.

        Checks graph shape, node identity, input/link integrity and unresolved
        placeholders, then compares node classes against the live inventory.
        Unknown classes are warnings (custom nodes exist), never errors.
        """
        errors, warnings = [], []
        if not isinstance(prompt, dict) or not prompt:
            raise ValidationError("ComfyUI prompt must be a non-empty API-format workflow object")
        graph = {k: v for k, v in prompt.items() if not str(k).startswith("_")}
        if not graph:
            errors.append("workflow contains no nodes")
        node_ids = set(graph)
        link_targets = []
        for node_id, node in graph.items():
            if not isinstance(node, dict):
                errors.append(f"node {node_id!r} is not an object"); continue
            class_type = node.get("class_type")
            if not isinstance(class_type, str) or not class_type:
                errors.append(f"node {node_id!r} is missing class_type")
            inputs = node.get("inputs", {})
            if not isinstance(inputs, dict):
                errors.append(f"node {node_id!r} inputs must be an object"); continue
            for key, value in inputs.items():
                if isinstance(value, list) and len(value) == 2 and isinstance(value[0], str):
                    link_targets.append((node_id, key, value[0]))
                elif isinstance(value, str):
                    for token in re.findall(r"__[A-Z0-9_]+__", value):
                        warnings.append(f"node {node_id!r} input {key!r} has unresolved placeholder {token}")
        for node_id, key, target in link_targets:
            if target not in node_ids:
                errors.append(f"node {node_id!r} input {key!r} links to missing node {target!r}")
        known: set[str] = set()
        try:
            info = self._request("/object_info", timeout=30)
            if isinstance(info, dict):
                known = set(info)
        except AdapterUnavailable as exc:
            warnings.append(f"live node inventory unavailable; class check skipped ({exc.code})")
        if known:
            for node_id, node in graph.items():
                class_type = node.get("class_type") if isinstance(node, dict) else None
                if isinstance(class_type, str) and class_type not in known:
                    warnings.append(f"node {node_id!r} class {class_type!r} not in live inventory (custom node?)")
        return {"valid": not errors, "errors": errors, "warnings": warnings,
                "node_count": len(graph), "link_count": len(link_targets)}
    def history(self, prompt_id: str) -> dict:
        if not isinstance(prompt_id,str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,256}",prompt_id): raise ValidationError("Invalid ComfyUI prompt ID")
        return self._request("/history/"+urllib.parse.quote(prompt_id,safe=""))
    def download_output(self, filename: str, subfolder: str, destination: Path, *, max_bytes: int=512*1024*1024) -> dict:
        if not self.is_loopback: raise PermissionDenied("Non-loopback ComfyUI hosts are unsupported by this release")
        if not isinstance(filename,str) or not filename or filename in {".",".."} or "/" in filename or "\\" in filename:
            raise ValidationError("ComfyUI output filename must be a basename")
        if not isinstance(subfolder,str) or Path(subfolder).is_absolute() or ".." in Path(subfolder).parts or "\\" in subfolder:
            raise ValidationError("ComfyUI output subfolder is unsafe")
        params=urllib.parse.urlencode({"filename":filename,"subfolder":subfolder,"type":"output"})
        url=self.base_url+"/view?"+params
        req=urllib.request.Request(url,method="GET")
        destination.parent.mkdir(parents=True,exist_ok=True)
        fd=os.open(destination,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
        written=0
        try:
            with os.fdopen(fd,"wb") as output, _local_opener().open(req,timeout=60) as response:
                declared=response.headers.get("Content-Length")
                if declared and int(declared)>max_bytes:
                    raise ValidationError(f"ComfyUI output exceeds {max_bytes} bytes")
                while True:
                    chunk=response.read(1024*1024)
                    if not chunk: break
                    written+=len(chunk)
                    if written>max_bytes: raise ValidationError(f"ComfyUI output exceeds {max_bytes} bytes")
                    output.write(chunk)
                output.flush(); os.fsync(output.fileno())
        except urllib.error.HTTPError as exc:
            destination.unlink(missing_ok=True)
            raise AdapterUnavailable(f"ComfyUI output retrieval failed with HTTP {exc.code}",details={"url":url,"status":exc.code}) from exc
        except urllib.error.URLError as exc:
            destination.unlink(missing_ok=True)
            raise AdapterUnavailable(f"ComfyUI output retrieval failed: {exc}",details={"url":url}) from exc
        except Exception:
            destination.unlink(missing_ok=True)
            raise
        if written==0:
            destination.unlink(missing_ok=True)
            raise AdapterUnavailable("ComfyUI returned an empty output file",details={"url":url})
        return {"path":str(destination),"size_bytes":written,"url":url}
