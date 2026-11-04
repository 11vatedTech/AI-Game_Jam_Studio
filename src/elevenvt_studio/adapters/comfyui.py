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
