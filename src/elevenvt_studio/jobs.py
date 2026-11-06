from __future__ import annotations
import json, uuid, re, logging
from datetime import datetime, timezone
from pathlib import Path
from .errors import ValidationError, NotFound
from .policy import utc_now

TERMINAL={"SUCCEEDED","FAILED","CANCELLED","NEEDS_RECONCILIATION"}

def _resolve_refs(value, outputs):
    if isinstance(value,dict):
        if set(value)=={"$ref"}:
            ref=value["$ref"]
            if not isinstance(ref,str) or "." not in ref: raise ValidationError(f"Invalid output reference: {ref}")
            task_id,key=ref.split(".",1)
            if task_id not in outputs or key not in outputs[task_id]: raise ValidationError(f"Unresolved output reference: {ref}")
            return outputs[task_id][key]
        return {k:_resolve_refs(v,outputs) for k,v in value.items()}
    if isinstance(value,list): return [_resolve_refs(v,outputs) for v in value]
    return value

class JobEngine:
    def __init__(self, db, service): self.db,self.service=db,service
    def create(self, spec: dict) -> dict:
        if not isinstance(spec,dict) or not isinstance(spec.get("tasks"),list) or not spec["tasks"]:
            raise ValidationError("Job spec must contain a non-empty tasks array")
        jid=str(spec.get("id") or uuid.uuid4()); name=str(spec.get("name") or "Untitled production job")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}",jid): raise ValidationError("Job ID must be 1-64 safe alphanumeric/underscore/hyphen characters")
        required_reviews=spec.get("required_reviews",["technical","creative"])
        allowed_reviews={"technical","creative","rights","performance","accessibility","release"}
        if not isinstance(required_reviews,list) or any(r not in allowed_reviews for r in required_reviews):
            raise ValidationError("required_reviews must be a list of supported review types")
        tasks=spec["tasks"]
        if len(tasks)>500: raise ValidationError("A job may contain at most 500 tasks")
        if any(not isinstance(t,dict) for t in tasks): raise ValidationError("Every task must be an object")
        ids=[t.get("id") for t in tasks]
        if any(not isinstance(i,str) or not i for i in ids) or len(set(ids))!=len(ids): raise ValidationError("Task IDs must be unique, non-empty strings")
        known=set(ids)
        for task in tasks:
            if not isinstance(task.get("capability"),str) or not task.get("capability"): raise ValidationError(f"Task {task.get('id')} is missing capability")
            deps=task.get("depends_on",[])
            if not isinstance(deps,list) or any(not isinstance(d,str) or d not in known for d in deps): raise ValidationError(f"Task {task['id']} has invalid dependencies")
            if task["id"] in deps: raise ValidationError(f"Task {task['id']} depends on itself")
            if not isinstance(task.get("inputs",{}),dict): raise ValidationError(f"Task {task['id']} inputs must be an object")
        self._topological(tasks)
        now=utc_now(); workspace=str(self.service.config.workspace)
        with self.db.connect() as c:
            c.execute("INSERT INTO jobs(id,name,status,spec_json,created_at,updated_at,workspace) VALUES(?,?,?,?,?,?,?)",
                      (jid,name,"CREATED",json.dumps(spec,sort_keys=True),now,now,workspace))
            for t in tasks:
                c.execute("INSERT INTO tasks(id,job_id,capability_id,status,inputs_json,depends_on_json) VALUES(?,?,?,?,?,?)",
                          (t["id"],jid,t["capability"],"PENDING",json.dumps(t.get("inputs",{})),json.dumps(t.get("depends_on",[]))))
            self.db.event(c,"job",jid,"JOB_CREATED",{"task_count":len(tasks)},now)
        return {"id":jid,"name":name,"status":"CREATED","task_count":len(tasks)}
    @staticmethod
    def _topological(tasks):
        pending={t["id"]:set(t.get("depends_on",[])) for t in tasks}; ordered=[]
        while pending:
            ready=sorted(k for k,v in pending.items() if not v)
            if not ready: raise ValidationError("Workflow contains a dependency cycle")
            for key in ready:
                ordered.append(key); pending.pop(key)
                for deps in pending.values(): deps.discard(key)
        return ordered
    def cancel(self, job_id: str, *, reason: str = "") -> dict:
        """Operator cancellation: a CANCELLED job never starts and a running job
        stops at the next task boundary; the in-flight task is left for
        crash-reconciliation rather than force-killed."""
        now=utc_now()
        with self.db.connect() as c:
            job=c.execute("SELECT status FROM jobs WHERE id=?",(job_id,)).fetchone()
            if not job: raise NotFound(f"Unknown job: {job_id}")
            if job["status"] in TERMINAL | {"CANCELLED"}:
                raise ValidationError(f"Job is already {job['status']}; cancellation is for live jobs")
            c.execute("UPDATE jobs SET status='CANCELLED',updated_at=?,finished_at=? WHERE id=?",(now,now,job_id))
            self.db.event(c,"job",job_id,"JOB_CANCELLED",{"reason":reason},now)
        return self.status(job_id)
    def _is_cancelled(self, job_id: str) -> bool:
        with self.db.connect() as c:
            row=c.execute("SELECT status FROM jobs WHERE id=?",(job_id,)).fetchone()
            return bool(row) and row["status"]=="CANCELLED"
    def run(self, job_id: str, approval_id: str | None=None) -> dict:
        from .locking import ProcessFileLock
        lock_dir=self.service.config.home/"job-locks"
        with ProcessFileLock(lock_dir/(job_id+".lock")):
            if self._is_cancelled(job_id):
                return self.status(job_id)
            return self._run_locked(job_id,approval_id)
    def _run_locked(self, job_id: str, approval_id: str | None=None) -> dict:
        early_return = False
        with self.db.connect() as c:
            job=c.execute("SELECT * FROM jobs WHERE id=?",(job_id,)).fetchone()
            if not job: raise NotFound(f"Unknown job: {job_id}")
            if job["status"] in TERMINAL:
                early_return = True
            else:
                task_states=c.execute("SELECT id,status FROM tasks WHERE job_id=?",(job_id,)).fetchall()
                unresolved=[r["id"] for r in task_states if r["status"]=="NEEDS_RECONCILIATION"]
                if unresolved:
                    now=utc_now()
                    c.execute("UPDATE jobs SET status='NEEDS_RECONCILIATION',updated_at=? WHERE id=?",(now,job_id))
                    early_return = True
                else:
                    stale=[r["id"] for r in task_states if r["status"]=="RUNNING"]
                    if job["status"]=="RUNNING" and stale:
                        now=utc_now()
                        for task_id in stale:
                            payload={"code":"WORKER_CRASH_RECOVERY_REQUIRED","message":"A previous worker stopped while this task was RUNNING. The external side effect may or may not have occurred; inspect the target application before deciding to mark complete or retry."}
                            c.execute("UPDATE tasks SET status='NEEDS_RECONCILIATION',finished_at=?,error_json=? WHERE job_id=? AND id=?",
                                      (now,json.dumps(payload,sort_keys=True),job_id,task_id))
                            self.db.event(c,"task",f"{job_id}:{task_id}","TASK_NEEDS_RECONCILIATION",payload,now)
                        c.execute("UPDATE jobs SET status='NEEDS_RECONCILIATION',updated_at=?,finished_at=? WHERE id=?",(now,now,job_id))
                        self.db.event(c,"job",job_id,"JOB_RECOVERY_BLOCKED",{"tasks":stale},now)
                        early_return = True
                    elif task_states and all(r["status"]=="SUCCEEDED" for r in task_states):
                        now=utc_now(); c.execute("UPDATE jobs SET status='SUCCEEDED',updated_at=?,finished_at=? WHERE id=?",(now,now,job_id))
                        self.db.event(c,"job",job_id,"JOB_RECOVERED_AS_SUCCEEDED",{},now)
                        early_return = True
                    else:
                        c.execute("UPDATE jobs SET status='RUNNING',started_at=COALESCE(started_at,?),updated_at=?,finished_at=NULL WHERE id=?",(utc_now(),utc_now(),job_id))
                        self.db.event(c,"job",job_id,"JOB_RUNNING",{},utc_now())
        if early_return:
            return self.status(job_id)
        logging.getLogger("elevenvt_studio").info("job started",extra={"job_id":job_id})
        outputs={}; errors=[]
        with self.db.connect() as c: task_rows=c.execute("SELECT * FROM tasks WHERE job_id=?",(job_id,)).fetchall()
        tasks=[dict(r) for r in task_rows]
        spec=json.loads(job["spec_json"]); order=self._topological(spec["tasks"])
        task_map={t["id"]:t for t in tasks}
        task_specs={t["id"]:t for t in spec["tasks"]}
        for task_id in order:
            if self._is_cancelled(job_id):
                with self.db.connect() as c:
                    c.execute("UPDATE jobs SET status='CANCELLED',updated_at=?,finished_at=? WHERE id=?",(utc_now(),utc_now(),job_id))
                    self.db.event(c,"job",job_id,"JOB_CANCELLED_MID_RUN",{"stopped_before":task_id},utc_now())
                return self.status(job_id)
            row=task_map[task_id]; deps=json.loads(row["depends_on_json"])
            failed=[d for d in deps if task_map[d]["status"]!="SUCCEEDED"]
            if failed:
                self._set_task(job_id,task_id,"BLOCKED",error={"code":"DEPENDENCY_FAILED","dependencies":failed}); task_map[task_id]["status"]="BLOCKED"; errors.append(task_id); continue
            if row["status"]=="SUCCEEDED": outputs[task_id]=json.loads(row["outputs_json"] or "{}"); continue
            inputs=_resolve_refs(json.loads(row["inputs_json"]),outputs)
            if approval_id: inputs.setdefault("approval_id",approval_id)
            attempt=int(row["attempt"])+1; self._set_task(job_id,task_id,"RUNNING",attempt=attempt)
            try:
                resource_spec=task_specs[task_id].get("resources",{})
                if resource_spec:
                    from .resources import ResourceGuard
                    allowed,diagnostic=ResourceGuard().check(resource_spec)
                    if not allowed:
                        from .errors import ResourceUnavailable
                        raise ResourceUnavailable("Task denied by conservative resource admission",details=diagnostic)
                result=self.service.invoke(row["capability_id"],inputs,job_id=job_id,task_id=task_id)
                self._set_task(job_id,task_id,"SUCCEEDED",outputs=result)
                task_map[task_id]["status"]="SUCCEEDED"
                outputs[task_id]=result
            except Exception as exc:
                err={"code":getattr(exc,"code","UNKNOWN"),"message":str(exc),"details":getattr(exc,"details",{})}
                failed_state=("BLOCKED" if err["code"] in {"APPROVAL_REQUIRED","RESOURCE_UNAVAILABLE"} else
                              "NEEDS_RECONCILIATION" if err["code"]=="UNCERTAIN_SIDE_EFFECT" else "FAILED")
                self._set_task(job_id,task_id,failed_state,error=err)
                task_map[task_id]["status"]=failed_state
                errors.append(task_id)
                # Do not blindly execute dependants or continue a production sequence after a failed task.
                break
        with self.db.connect() as c:
            states=[r[0] for r in c.execute("SELECT status FROM tasks WHERE job_id=?",(job_id,)).fetchall()]
            status=("SUCCEEDED" if states and all(s=="SUCCEEDED" for s in states) else
                    "NEEDS_RECONCILIATION" if "NEEDS_RECONCILIATION" in states else
                    "BLOCKED" if "BLOCKED" in states and "FAILED" not in states else "FAILED")
            c.execute("UPDATE jobs SET status=?,updated_at=?,finished_at=? WHERE id=?",(status,utc_now(),utc_now(),job_id))
            self.db.event(c,"job",job_id,"JOB_FINISHED",{"status":status,"errors":errors},utc_now())
        logging.getLogger("elevenvt_studio").info("job finished",extra={"job_id":job_id})
        return self.status(job_id)
    def _set_task(self,jid,tid,status,*,attempt=None,outputs=None,error=None):
        now=utc_now()
        with self.db.connect() as c:
            fields=["status=?"]
            vals=[status]
            if attempt is not None: fields.append("attempt=?"); vals.append(attempt)
            if status=="RUNNING": fields.append("started_at=?"); vals.append(now); fields.append("error_json=NULL")
            if status in {"SUCCEEDED","FAILED","BLOCKED","CANCELLED","NEEDS_RECONCILIATION"}: fields.append("finished_at=?"); vals.append(now)
            if outputs is not None: fields.append("outputs_json=?"); vals.append(json.dumps(outputs,sort_keys=True))
            if error is not None: fields.append("error_json=?"); vals.append(json.dumps(error,sort_keys=True))
            vals.extend([jid,tid]); c.execute(f"UPDATE tasks SET {','.join(fields)} WHERE job_id=? AND id=?",vals)
            self.db.event(c,"task",f"{jid}:{tid}","TASK_"+status,{"error":error,"outputs":outputs},now)
    def reconcile(self, job_id: str, task_id: str, *, action: str, reviewer: str, evidence: str, outputs: dict | None=None) -> dict:
        """Human-reviewed resolution of an uncertain in-flight side effect."""
        if action not in {"retry", "mark_succeeded"}: raise ValidationError("Reconciliation action must be retry or mark_succeeded")
        if not reviewer.strip() or not evidence.strip(): raise ValidationError("A named reviewer and evidence-backed rationale are required")
        if action == "mark_succeeded" and not isinstance(outputs, dict):
            raise ValidationError("mark_succeeded requires an explicit outputs JSON object, including {} when no outputs were produced")
        if action == "retry" and outputs is not None:
            raise ValidationError("retry must not supply outputs; the task will execute again")
        if outputs is not None and not isinstance(outputs,dict): raise ValidationError("Reconciled outputs must be a JSON object")
        now=utc_now()
        with self.db.connect() as c:
            job=c.execute("SELECT status FROM jobs WHERE id=?",(job_id,)).fetchone()
            task=c.execute("SELECT status,capability_id FROM tasks WHERE job_id=? AND id=?",(job_id,task_id)).fetchone()
            if not job or not task: raise NotFound(f"Unknown job/task: {job_id}/{task_id}")
            if task["status"]!="NEEDS_RECONCILIATION": raise ValidationError(f"Task is {task['status']}; only NEEDS_RECONCILIATION tasks can be resolved")
            if action=="mark_succeeded":
                c.execute("UPDATE tasks SET status='SUCCEEDED',outputs_json=?,error_json=NULL,finished_at=? WHERE job_id=? AND id=?",
                          (json.dumps(outputs or {},sort_keys=True),now,job_id,task_id))
            else:
                c.execute("UPDATE tasks SET status='PENDING',outputs_json=NULL,error_json=NULL,finished_at=NULL WHERE job_id=? AND id=?",(job_id,task_id))
            self.db.event(c,"task",f"{job_id}:{task_id}","TASK_MANUALLY_RECONCILED",
                          {"action":action,"reviewer":reviewer,"evidence":evidence,"outputs":outputs or {}},now)
            remaining=c.execute("SELECT COUNT(*) FROM tasks WHERE job_id=? AND status='NEEDS_RECONCILIATION'",(job_id,)).fetchone()[0]
            state="NEEDS_RECONCILIATION" if remaining else "BLOCKED"
            c.execute("UPDATE jobs SET status=?,updated_at=?,finished_at=NULL WHERE id=?",(state,now,job_id))
            self.db.event(c,"job",job_id,"JOB_RECONCILIATION_UPDATED",{"task_id":task_id,"action":action,"remaining":remaining},now)
        return self.status(job_id)

    def list(self, status: str | None=None, limit: int=100) -> list[dict]:
        limit=max(1,min(int(limit),500))
        with self.db.connect() as c:
            if status:
                rows=c.execute("SELECT id,name,status,created_at,updated_at FROM jobs WHERE status=? ORDER BY created_at DESC LIMIT ?",(status.upper(),limit)).fetchall()
            else:
                rows=c.execute("SELECT id,name,status,created_at,updated_at FROM jobs ORDER BY created_at DESC LIMIT ?",(limit,)).fetchall()
        return [dict(r) for r in rows]
    def status(self,job_id: str) -> dict:
        with self.db.connect() as c:
            job=c.execute("SELECT * FROM jobs WHERE id=?",(job_id,)).fetchone()
            if not job: raise NotFound(f"Unknown job: {job_id}")
            tasks=c.execute("SELECT * FROM tasks WHERE job_id=? ORDER BY rowid",(job_id,)).fetchall()
        return {"id":job["id"],"name":job["name"],"status":job["status"],"created_at":job["created_at"],"updated_at":job["updated_at"],
                "tasks":[{"id":t["id"],"capability":t["capability_id"],"status":t["status"],"attempt":t["attempt"],
                          "outputs":json.loads(t["outputs_json"]) if t["outputs_json"] else None,
                          "error":json.loads(t["error_json"]) if t["error_json"] else None} for t in tasks]}
