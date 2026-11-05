from __future__ import annotations
import json, sys, traceback
from typing import Any
from ..errors import StudioError
from ..perception.tools import PERCEPTION_TOOL_NAMES, PERCEPTION_TOOL_SPECS, PerceptionTools, content_blocks

TOOLS=[
 {"name":"studio_status","description":"Get runtime status, configured workspace and registered implementation count.","inputSchema":{"type":"object","properties":{},"additionalProperties":False}},
 {"name":"capabilities_list","description":"List capabilities and distinguish implemented runtime operations from planned integrations.","inputSchema":{"type":"object","properties":{"domain":{"type":"string"}},"additionalProperties":False}},
 {"name":"resource_profile","description":"Inspect current system and GPU resource availability.","inputSchema":{"type":"object","properties":{},"additionalProperties":False}},
 {"name":"job_create","description":"Create a durable dependency-ordered production job from a JSON task graph.","inputSchema":{"type":"object","properties":{"job_spec":{"type":"object"}},"required":["job_spec"],"additionalProperties":False}},
 {"name":"job_run","description":"Execute a created job until completion, failure or an approval/resource block. Side effects remain policy-gated.","inputSchema":{"type":"object","properties":{"job_id":{"type":"string"},"approval_id":{"type":"string"}},"required":["job_id"],"additionalProperties":False}},
 {"name":"job_status","description":"Inspect durable job and task states, outputs and failures.","inputSchema":{"type":"object","properties":{"job_id":{"type":"string"}},"required":["job_id"],"additionalProperties":False}},
 {"name":"artifacts_list","description":"List artifacts with hashes, provenance and validation metadata.","inputSchema":{"type":"object","properties":{"job_id":{"type":"string"}},"additionalProperties":False}},
 {"name":"artifact_verify","description":"Recompute an artifact SHA-256 to detect missing or modified files.","inputSchema":{"type":"object","properties":{"artifact_id":{"type":"string"}},"required":["artifact_id"],"additionalProperties":False}},
 {"name":"quality_report","description":"Run deterministic job/artifact integrity gates. Subjective craft review remains explicitly NOT_RUN.","inputSchema":{"type":"object","properties":{"job_id":{"type":"string"}},"required":["job_id"],"additionalProperties":False}},
 {"name":"approval_request","description":"Create a human approval request for a specific exact scope, side-effect class and target.","inputSchema":{"type":"object","properties":{"scope":{"type":"string"},"side_effect":{"type":"string"},"target":{"type":"string"},"reason":{"type":"string"}},"required":["scope","side_effect","target","reason"],"additionalProperties":False}},
 {"name":"workspace_write_text","description":"Create a new file in the controlled workspace. Existing files cannot be overwritten by this operation.","inputSchema":{"type":"object","properties":{"path":{"type":"string"},"content":{"type":"string"}},"required":["path","content"],"additionalProperties":False}}
]+PERCEPTION_TOOL_SPECS

class MCPServer:
    def __init__(self, service): self.service=service; self._initialized=False; self._perception=None
    @property
    def perception(self):
        if self._perception is None: self._perception=PerceptionTools(self.service)
        return self._perception
    def perception_call(self,name: str,args: dict) -> list[dict]:
        handler={"perception_capture":self.perception.capture,"perception_get":self.perception.get,
                 "perception_crop":self.perception.crop,"perception_probe":self.perception.probe,
                 "perception_probe_verify":self.perception.probe_verify}[name]
        return content_blocks(handler(args))
    def tool_call(self,name: str,args: dict) -> Any:
        if not isinstance(args,dict): raise ValueError("Tool arguments must be an object")
        mapping={
            "studio_status":lambda:self.service.status(),
            "capabilities_list":lambda:self.service.registry.list(args.get("domain")),
            "resource_profile":lambda:__import__("elevenvt_studio.resources",fromlist=["profile"]).profile(self.service.config.home),
            "job_create":lambda:self.service.jobs.create(args.get("job_spec",{})),
            "job_run":lambda:self.service.jobs.run(args["job_id"],args.get("approval_id")),
            "job_status":lambda:self.service.jobs.status(args["job_id"]),
            "artifacts_list":lambda:self.service.artifacts.list(args.get("job_id")),
            "artifact_verify":lambda:self.service.artifacts.verify(args["artifact_id"]),
            "quality_report":lambda:self.service.quality_report(args["job_id"]),
            "approval_request":lambda:self.service.policy.request(args["scope"],args["side_effect"],args["target"],args["reason"]),
            "workspace_write_text":lambda:self.service.invoke("workspace.write_text",args),
        }
        if name not in mapping: raise ValueError(f"Unknown tool: {name}")
        return mapping[name]()
    def handle(self,msg: dict) -> dict | None:
        method=msg.get("method"); ident=msg.get("id")
        def result(value): return {"jsonrpc":"2.0","id":ident,"result":value}
        def error(code,message,data=None):
            obj={"jsonrpc":"2.0","id":ident,"error":{"code":code,"message":message}}
            if data is not None: obj["error"]["data"]=data
            return obj
        try:
            if method=="notifications/initialized": self._initialized=True; return None
            if method=="initialize":
                params=msg.get("params",{}); version=params.get("protocolVersion","2025-11-25")
                return result({"protocolVersion":version,"capabilities":{"tools":{"listChanged":False}},
                               "serverInfo":{"name":"11vatedtech-ai-game-jam-studio","version":"0.2.0"},
                               "instructions":"Use capabilities_list before execution. Every side effect is governed by local policy. Human approvals must be granted outside this agent tool surface. A queued generation is not a completed artifact."})
            if method=="ping": return result({})
            if method=="tools/list": return result({"tools":TOOLS})
            if method=="tools/call":
                params=msg.get("params",{}); name=params.get("name"); args=params.get("arguments",{})
                try:
                    if name in PERCEPTION_TOOL_NAMES:
                        # Images travel as content blocks with no structuredContent: a
                        # non-empty structured payload can shadow them in host SDKs.
                        return result({"content":self.perception_call(name,args),"isError":False})
                    output=self.tool_call(name,args); return result({"content":[{"type":"text","text":json.dumps(output,indent=2,sort_keys=True)}],"structuredContent":output,"isError":False})
                except Exception as exc:
                    payload={"code":getattr(exc,"code","TOOL_ERROR"),"message":str(exc),"details":getattr(exc,"details",{})}
                    return result({"content":[{"type":"text","text":json.dumps(payload,indent=2)}],"isError":True})
            if method in {"shutdown","exit"}: return result({})
            if ident is None: return None
            return error(-32601,f"Method not found: {method}")
        except Exception as exc: return error(-32603,str(exc),{"type":type(exc).__name__})
    def serve(self, reader=None, writer=None):
        reader=reader or sys.stdin; writer=writer or sys.stdout
        for line in reader:
            line=line.strip()
            if not line: continue
            try:
                msg=json.loads(line); response=self.handle(msg)
                if response is not None:
                    writer.write(json.dumps(response,separators=(",",":"))+"\n"); writer.flush()
            except Exception as exc:
                writer.write(json.dumps({"jsonrpc":"2.0","id":None,"error":{"code":-32700,"message":"Parse error","data":str(exc)}})+"\n"); writer.flush()
