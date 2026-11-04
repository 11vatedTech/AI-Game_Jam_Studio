from __future__ import annotations
import json, os, urllib.error, urllib.request
from dataclasses import dataclass
from ..errors import AdapterUnavailable, ValidationError

@dataclass
class OpenAICompatibleProvider:
    """Optional local OpenAI-compatible chat endpoint; no provider is mandatory for the runtime."""
    base_url: str
    model: str
    api_key_env: str | None = None
    timeout_seconds: int = 180
    def chat(self, messages: list[dict], *, tools: list[dict] | None=None, temperature: float=0.2) -> dict:
        if not self.model: raise ValidationError("No model configured. Set [models].model in config.toml.")
        payload={"model":self.model,"messages":messages,"temperature":temperature}
        if tools: payload["tools"]=tools
        headers={"Content-Type":"application/json"}
        key=os.environ.get(self.api_key_env) if self.api_key_env else None
        if key: headers["Authorization"]="Bearer "+key
        request=urllib.request.Request(self.base_url.rstrip("/")+"/chat/completions",data=json.dumps(payload).encode(),headers=headers,method="POST")
        try:
            with urllib.request.urlopen(request,timeout=self.timeout_seconds) as response: return json.loads(response.read())
        except (urllib.error.URLError,TimeoutError,OSError,json.JSONDecodeError) as exc: raise AdapterUnavailable(f"Model endpoint request failed: {exc}") from exc
