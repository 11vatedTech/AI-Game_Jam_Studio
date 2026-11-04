from __future__ import annotations
import hashlib, json, os, re, shutil, time, uuid
from pathlib import Path
from .adapters.comfyui import ComfyUIAdapter
from .adapters.process import ProcessAdapter
from .artifacts import ArtifactStore
from .config import StudioConfig, write_default_config
from .db import Database
from .errors import AdapterUnavailable, ValidationError
from .jobs import JobEngine
from .paths import safe_workspace_path
from .policy import PolicyEngine, utc_now
from .registry import CapabilityRegistry
from .resources import profile
from .observability import configure_logging

class StudioService:
    def __init__(self, config: StudioConfig | None=None, *, catalog_dir: Path | None=None):
        self.config=config or StudioConfig.load()
        self.config.ensure_directories()
        self.logger=configure_logging(self.config.home)
        if not self.config.policy_file.exists():
            write_default_config(self.config.home)
            if not self.config.policy_file.exists():
                self.config.policy_file.parent.mkdir(parents=True,exist_ok=True)
                default_policy=self.config.home/"policy.json"
                if default_policy.exists(): shutil.copy2(default_policy,self.config.policy_file)
        self.db=Database(self.config.database)
        self.policy=PolicyEngine(self.config.policy_file,self.db)
        root=Path(__file__).resolve().parents[2]
        source_catalog=root/"catalogs"/"runtime"
        packaged_catalog=Path(__file__).resolve().parent/"data"
        chosen_catalog=catalog_dir or (source_catalog if source_catalog.exists() else packaged_catalog)
        self.registry=CapabilityRegistry(chosen_catalog)
        self.artifacts=ArtifactStore(self.config.artifact_root,self.config.workspace,self.db)
        self.comfyui=ComfyUIAdapter(self.config.comfyui_url)
        self.process=ProcessAdapter(self.config.workspace)
        self.jobs=JobEngine(self.db,self)
        self.handlers={
            "studio.status":self._status,
            "capability.list":self._capability_list,
            "resource.profile":self._resource_profile,
            "workspace.write_text":self._write_text,
            "workspace.read_text":self._read_text,
            "artifact.list":self._artifact_list,
            "artifact.verify":self._artifact_verify,
            "comfyui.health":self._comfyui_health,
            "comfyui.inventory":self._comfyui_inventory,
            "comfyui.queue_prompt":self._comfyui_queue,
            "comfyui.queue_status":self._comfyui_status,
            "comfyui.await_completion":self._comfyui_await,
            "comfyui.retrieve_outputs":self._comfyui_retrieve,
            "blender.health":self._blender_health,
            "blender.execute_script":self._blender_run,
            "godot.health":self._godot_health,
            "godot.validate_project":self._godot_validate,
        }
    def invoke(self, capability_id: str, inputs: dict, *, job_id: str | None=None, task_id: str | None=None) -> dict:
        cap=self.registry.get(capability_id)
        if capability_id.startswith("comfyui.") and not self.comfyui.is_loopback:
            from .errors import PermissionDenied
            raise PermissionDenied("Non-loopback ComfyUI endpoints are unsupported by this release")
        if cap.get("status") not in {"IMPLEMENTED","EXPERIMENTAL"}:
            raise ValidationError(f"Capability is not executable in this build: {capability_id} ({cap.get('status')})")
        if capability_id not in self.handlers: raise ValidationError(f"No handler is registered for {capability_id}")
        if not isinstance(inputs,dict): raise ValidationError("Capability inputs must be an object")
        approval_id=inputs.get("approval_id")
        default_target={"comfyui.queue_prompt":self.config.comfyui_url,"blender.execute_script":str(inputs.get("script_path","workspace")),
                        "godot.validate_project":str(inputs.get("project_path","workspace"))}.get(capability_id,"workspace")
        self.policy.authorize(cap["scope"],cap["side_effect"],str(inputs.get("target",default_target)),approval_id=approval_id)
        inputs=dict(inputs)
        if job_id: inputs.setdefault("job_id",job_id)
        if task_id: inputs.setdefault("task_id",task_id)
        result=self.handlers[capability_id](inputs)
        result.setdefault("capability_id",capability_id)
        result.setdefault("executed_at",utc_now())
        return result
    def status(self) -> dict:
        return {"product":"11vatedTech AI Game Jam Studio","runtime_version":"0.2.0","spec_version":"0.1.0",
                "state":"FOUNDATION_OPERATIONAL","home":str(self.config.home),"workspace":str(self.config.workspace),
                "registered_capabilities":len(self.registry.list()),"executable_capabilities":sum(x["status"]=="IMPLEMENTED" for x in self.registry.list()),
                "database":str(self.config.database)}
    def doctor(self) -> dict:
        apps={}
        for key,exe in (("blender",self.config.blender_executable),("godot",self.config.godot_executable)):
            found=shutil.which(exe) or (str(Path(exe).resolve()) if Path(exe).is_file() else None)
            apps[key]={"configured":exe,"found":bool(found),"path":found}
        try: comfy=self.comfyui.health(); comfy_status="CONNECTED"
        except Exception as exc: comfy={"error":str(exc)}; comfy_status="NOT_CONNECTED"
        return {"status":"DIAGNOSTIC_ONLY","system":profile(self.config.home),"applications":apps,
                "comfyui":{"status":comfy_status,"details":comfy},"notes":["Application presence does not certify an adapter.","A ComfyUI health response does not prove image quality or workflow correctness."]}
    def _status(self,inputs): return self.status()
    def _capability_list(self,inputs): return {"capabilities":self.registry.list(inputs.get("domain"))}
    def _resource_profile(self,inputs): return profile(self.config.home)
    def _write_text(self,inputs):
        path=safe_workspace_path(self.config.workspace,inputs.get("path",""))
        if path.exists(): raise ValidationError(f"Refusing to overwrite existing file: {path.relative_to(self.config.workspace)}")
        content=inputs.get("content")
        if not isinstance(content,str): raise ValidationError("content must be a string")
        if len(content.encode("utf-8")) > 5*1024*1024: raise ValidationError("workspace.write_text is limited to 5 MiB; use a typed binary/media adapter for assets")
        path.parent.mkdir(parents=True,exist_ok=True)
        # Exclusive creation prevents concurrent agents from silently overwriting one another.
        import os as _os
        fd=_os.open(path,_os.O_CREAT|_os.O_EXCL|_os.O_WRONLY,0o600)
        try:
            with _os.fdopen(fd,"w",encoding="utf-8",newline="") as stream:
                stream.write(content); stream.flush(); _os.fsync(stream.fileno())
        except Exception:
            try: path.unlink(missing_ok=True)
            finally: raise
        artifact=self.artifacts.register(path,name=path.name,job_id=inputs.get("job_id"),task_id=inputs.get("task_id"),
          provenance={"creator":"workspace.write_text","content_source":"job_or_agent_input"},validation={"status":"NOT_RUN"})
        return {"created":True,"path":str(path.relative_to(self.config.workspace)),"artifact_id":artifact["id"],"sha256":artifact["sha256"],"artifact":artifact}
    def _read_text(self,inputs):
        path=safe_workspace_path(self.config.workspace,inputs.get("path",""))
        if not path.is_file(): raise ValidationError(f"File does not exist: {inputs.get('path')}")
        max_bytes=max(1,min(int(inputs.get("max_bytes",1_000_000)),5*1024*1024))
        if path.stat().st_size>max_bytes: raise ValidationError(f"File exceeds max_bytes={max_bytes}")
        return {"path":str(path.relative_to(self.config.workspace)),"content":path.read_text(encoding="utf-8"),"size_bytes":path.stat().st_size}
    def _artifact_list(self,inputs): return {"artifacts":self.artifacts.list(inputs.get("job_id"))}
    def _artifact_verify(self,inputs): return self.artifacts.verify(inputs.get("artifact_id",""))
    def _comfyui_health(self,inputs): return self.comfyui.health()
    def _comfyui_queue(self,inputs):
        prompt=inputs.get("prompt")
        result=self.comfyui.queue_prompt(prompt,inputs.get("client_id"))
        workflow_hash=hashlib.sha256(json.dumps(prompt,sort_keys=True,separators=(",", ":")).encode("utf-8")).hexdigest()
        # Queue acceptance is a side effect, not proof that generation completed.
        return {"queued":True,"completion_verified":False,"workflow_sha256":workflow_hash,**result}
    def _comfyui_status(self,inputs):
        pid=inputs.get("prompt_id")
        if not pid: raise ValidationError("prompt_id is required")
        return {"prompt_id":pid,"queue":self.comfyui.queue(),"history":self.comfyui.history(pid)}
    def _comfyui_inventory(self,inputs):
        return self.comfyui.inventory()
    def _comfyui_await(self,inputs):
        pid=inputs.get("prompt_id")
        if not pid: raise ValidationError("prompt_id is required")
        timeout=max(5.0,min(float(inputs.get("timeout_seconds",900)),3600.0))
        interval=max(0.5,min(float(inputs.get("poll_interval_seconds",2.0)),10.0))
        deadline=time.monotonic()+timeout
        last_record=None
        while time.monotonic() < deadline:
            history=self.comfyui.history(pid)
            record=history.get(pid) if isinstance(history,dict) else None
            if record is None and isinstance(history,dict) and "outputs" in history:
                record=history
            if isinstance(record,dict):
                last_record=record
                status=record.get("status") or {}
                status_text=str(status.get("status_str", "")).lower() if isinstance(status,dict) else ""
                completed=bool(status.get("completed",False)) if isinstance(status,dict) else False
                messages=status.get("messages",[]) if isinstance(status,dict) else []
                if status_text in {"error","failed"}:
                    raise AdapterUnavailable("ComfyUI workflow execution failed",details={"prompt_id":pid,"status":status,"messages":messages})
                if completed:
                    return {"prompt_id":pid,"completed":True,"status":status,"outputs":record.get("outputs",{}),
                            "output_node_count":len(record.get("outputs",{})) if isinstance(record.get("outputs",{}),dict) else 0}
            time.sleep(interval)
        raise AdapterUnavailable("Timed out waiting for ComfyUI workflow completion",details={"prompt_id":pid,"timeout_seconds":timeout,"last_history":last_record})
    def _comfyui_retrieve(self,inputs):
        pid=inputs.get("prompt_id")
        if not pid: raise ValidationError("prompt_id is required")
        history=self.comfyui.history(pid)
        record=history.get(pid) if isinstance(history,dict) else None
        if record is None and isinstance(history,dict) and "outputs" in history:
            record=history
        if not isinstance(record,dict): raise ValidationError("ComfyUI history does not contain the requested prompt")
        status=record.get("status") or {}
        if not (isinstance(status,dict) and status.get("completed")):
            raise ValidationError("Refusing to retrieve outputs before ComfyUI reports completion")
        if str(status.get("status_str", "")).lower() in {"error","failed"}:
            raise AdapterUnavailable("Cannot retrieve outputs from a failed ComfyUI workflow",details={"prompt_id":pid,"status":status})
        raw_outputs=record.get("outputs")
        if not isinstance(raw_outputs,dict): raise ValidationError("ComfyUI history has no output-node map")
        discovered=[]
        def visit(value,node_id):
            if isinstance(value,dict):
                if isinstance(value.get("filename"),str) and value.get("type")=="output":
                    discovered.append((node_id,value))
                    return
                for child in value.values(): visit(child,node_id)
            elif isinstance(value,list):
                for child in value: visit(child,node_id)
        for node_id,payload in raw_outputs.items(): visit(payload,str(node_id))
        # Preserve first-seen order while suppressing duplicate references emitted under multiple keys.
        unique=[]; seen=set()
        for node_id,metadata in discovered:
            key=(metadata.get("filename"),metadata.get("subfolder", ""),node_id)
            if key not in seen: unique.append((node_id,metadata)); seen.add(key)
        if not unique: raise ValidationError("Completed ComfyUI workflow produced no retrievable output files")
        artifacts=[]
        for index,(node_id,metadata) in enumerate(unique,1):
            filename=metadata["filename"]
            safe_node=re.sub(r"[^A-Za-z0-9_-]", "_", node_id)[:80] or "node"
            rel=f"generated/comfyui/{pid}/{safe_node}-{index:03d}-{filename}"
            destination=safe_workspace_path(self.config.workspace,rel)
            self.comfyui.download_output(filename,str(metadata.get("subfolder", "")),destination)
            artifact=self.artifacts.register(destination,name=filename,job_id=inputs.get("job_id"),task_id=inputs.get("task_id"),
                provenance={"creator":"comfyui","prompt_id":pid,"node_id":node_id,"workflow_sha256":inputs.get("workflow_sha256"),
                            "output_metadata":metadata,"runtime_endpoint":self.config.comfyui_url},
                validation={"status":"NOT_RUN","checks":[],"note":"File integrity only; semantic/image/audio/video quality has not been evaluated."})
            artifacts.append({"artifact_id":artifact["id"],"path":rel,"sha256":artifact["sha256"],"size_bytes":artifact["size_bytes"],
                              "media_type":artifact["media_type"],"node_id":node_id,"filename":filename})
        return {"prompt_id":pid,"retrieved_count":len(artifacts),"artifact_id":artifacts[0]["artifact_id"],"artifacts":artifacts,
                "semantic_validation":"NOT_RUN","rights_status":"UNKNOWN"}
    def _blender_health(self,inputs):
        result=self.process.run(self.config.blender_executable,["--version"],cwd=self.config.workspace,timeout=15)
        if not result["success"]: raise AdapterUnavailable("Blender version check failed",details=result)
        return result
    def _blender_run(self,inputs):
        rel=inputs.get("script_path")
        script=safe_workspace_path(self.config.workspace,rel or "")
        if not script.is_file() or script.suffix.lower()!=".py": raise ValidationError("script_path must reference an existing .py file inside the workspace")
        timeout=max(10,min(int(inputs.get("timeout_seconds",900)),7200))
        result=self.process.run(self.config.blender_executable,["--background","--python",str(script)],cwd=self.config.workspace,timeout=timeout)
        evidence=self._write_evidence("blender-run",result)
        if not result["success"]: raise AdapterUnavailable("Blender script execution failed",details={"process":result,"evidence":evidence})
        return {"process":result,"evidence":evidence,"application_state_verified":False,"note":"Process success is not asset-quality acceptance; inspect .blend, exports, logs, and rendered evidence."}
    def _godot_health(self,inputs):
        result=self.process.run(self.config.godot_executable,["--version"],cwd=self.config.workspace,timeout=15)
        if not result["success"]: raise AdapterUnavailable("Godot version check failed",details=result)
        return result
    def _godot_validate(self,inputs):
        project=safe_workspace_path(self.config.workspace,inputs.get("project_path",""),allow_root=True)
        if not project.is_dir() or not (project/"project.godot").is_file(): raise ValidationError("project_path must contain project.godot")
        timeout=max(10,min(int(inputs.get("timeout_seconds",600)),3600))
        result=self.process.run(self.config.godot_executable,["--headless","--path",str(project),"--editor","--quit"],cwd=self.config.workspace,timeout=timeout)
        evidence=self._write_evidence("godot-validation",result)
        if not result["success"]: raise AdapterUnavailable("Godot headless editor validation failed",details={"process":result,"evidence":evidence})
        return {"process":result,"evidence":evidence,"runtime_verified":False,"note":"Editor import/parse check only; a packaged runtime test is still required."}
    def _write_evidence(self,kind,result):
        name=f"{kind}-{uuid.uuid4().hex[:12]}.json"; p=self.config.evidence_root/name
        p.write_text(json.dumps(result,indent=2,sort_keys=True),encoding="utf-8")
        import hashlib
        return {"path":str(p),"sha256":hashlib.sha256(p.read_bytes()).hexdigest()}
    def record_quality_review(self, job_id: str, *, review_type: str, verdict: str, reviewer: str,
                              rationale: str, evidence: list[str] | None=None) -> dict:
        allowed_types={"technical","creative","rights","performance","accessibility","release"}
        verdict=verdict.upper()
        if review_type not in allowed_types: raise ValidationError(f"Unsupported review type: {review_type}")
        if verdict not in {"PASS","FAIL"}: raise ValidationError("Review verdict must be PASS or FAIL")
        if not reviewer.strip() or not rationale.strip(): raise ValidationError("Reviewer and rationale are required")
        import uuid
        review_id=str(uuid.uuid4()); now=utc_now()
        with self.db.connect() as c:
            if not c.execute("SELECT 1 FROM jobs WHERE id=?",(job_id,)).fetchone(): raise ValidationError(f"Unknown job: {job_id}")
            c.execute("INSERT INTO reviews(id,job_id,review_type,verdict,reviewer,rationale,evidence_json,created_at) VALUES(?,?,?,?,?,?,?,?)",
                      (review_id,job_id,review_type,verdict,reviewer,rationale,json.dumps(evidence or []),now))
            self.db.event(c,"job",job_id,"QUALITY_REVIEW_RECORDED",{"review_id":review_id,"review_type":review_type,"verdict":verdict,"reviewer":reviewer},now)
        return {"id":review_id,"job_id":job_id,"review_type":review_type,"verdict":verdict,"reviewer":reviewer,"rationale":rationale,"evidence":evidence or [],"created_at":now}
    def quality_report(self,job_id: str) -> dict:
        status=self.jobs.status(job_id); artifacts=self.artifacts.list(job_id); verified=[self.artifacts.verify(a["id"]) for a in artifacts]
        failed_hashes=[v for v in verified if v["status"]!="PASS"]
        with self.db.connect() as c:
            job_row=c.execute("SELECT spec_json FROM jobs WHERE id=?",(job_id,)).fetchone()
            review_rows=c.execute("SELECT * FROM reviews WHERE job_id=? ORDER BY created_at",(job_id,)).fetchall()
        if not job_row: raise ValidationError(f"Unknown job: {job_id}")
        job_spec=json.loads(job_row["spec_json"])
        required_reviews=job_spec.get("required_reviews",["technical","creative"])
        review_map={}
        for r in review_rows:
            review_map[r["review_type"]]={"verdict":r["verdict"],"reviewer":r["reviewer"],"rationale":r["rationale"],"evidence":json.loads(r["evidence_json"]),"created_at":r["created_at"]}
        missing_reviews=[r for r in required_reviews if r not in review_map]
        failed_reviews=[r for r in required_reviews if r in review_map and review_map[r]["verdict"]=="FAIL"]
        licenses=[a.get("provenance",{}).get("license",{}).get("status","unknown") for a in artifacts]
        rights_status=("FAIL" if any(x in {"restricted","blocked"} for x in licenses) else
                       "NOT_RUN" if not artifacts or any(x!="cleared" for x in licenses) else "PASS")
        semantic_status=("FAIL" if any(a.get("validation",{}).get("status")=="FAIL" for a in artifacts) else
                         "NOT_RUN" if not artifacts or any(a.get("validation",{}).get("status")!="PASS" for a in artifacts) else "PASS")
        review_status="FAIL" if failed_reviews else "NOT_RUN" if missing_reviews else "PASS"
        checks=[{"id":"ARTIFACT-EXPECTED","status":"PASS" if artifacts else "FAIL","detail":{"artifact_count":len(artifacts)}},
                {"id":"JOB-SUCCEEDED","status":"PASS" if status["status"]=="SUCCEEDED" else "FAIL","detail":status["status"]},
                {"id":"ARTIFACT-INTEGRITY","status":"PASS" if not failed_hashes else "FAIL","detail":verified},
                {"id":"LICENSE-PROVENANCE","status":rights_status,"detail":{"license_states":licenses,"rule":"All artifacts must have explicit cleared rights before a release can pass."}},
                {"id":"SEMANTIC-VALIDATION","status":semantic_status,"detail":"Every artifact needs domain-specific validation; hash integrity is not semantic correctness."},
                {"id":"REQUIRED-HUMAN-REVIEWS","status":review_status,"detail":{"required":required_reviews,"missing":missing_reviews,"failed":failed_reviews,"reviews":review_map}}]
        states={x["status"] for x in checks}
        report_status="FAIL" if "FAIL" in states else "PASS_ALL_CHECKS" if states=={"PASS"} else "PASS_PENDING_REVIEW"
        report={"job_id":job_id,"status":report_status,"checks":checks,"artifacts":artifacts,
                "generated_at":utc_now(),"certified":False,
                "certification_note":"Passing this job report does not certify the adapter, model, platform support matrix or entire studio release."}
        p=self.config.evidence_root/f"quality-{job_id}.json"; p.write_text(json.dumps(report,indent=2,sort_keys=True),encoding="utf-8")
        report["report_path"]=str(p)
        return report
