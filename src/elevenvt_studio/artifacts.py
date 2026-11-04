from __future__ import annotations
import hashlib, json, mimetypes, uuid
from datetime import datetime, timezone
from pathlib import Path
from .errors import NotFound, ValidationError
from .paths import safe_workspace_path
from .policy import utc_now

class ArtifactStore:
    def __init__(self, root: Path, workspace: Path, db):
        self.root=root; self.workspace=workspace; self.db=db
        self.root.mkdir(parents=True,exist_ok=True)
    def register(self, path: Path, *, name: str | None=None, job_id: str | None=None, task_id: str | None=None,
                 provenance: dict | None=None, validation: dict | None=None) -> dict:
        path=path.resolve()
        if not path.is_file(): raise ValidationError(f"Artifact is not a regular file: {path}")
        digest=_file_sha256(path); size=path.stat().st_size
        artifact_id=str(uuid.uuid4()); now=datetime.now(timezone.utc).isoformat()
        rel=str(path.relative_to(self.workspace.resolve())) if path.is_relative_to(self.workspace.resolve()) else str(path)
        source_provenance=dict(provenance or {})
        source_provenance.setdefault("origin","generated")
        source_provenance.setdefault("license",{"status":"unknown","review_required":True})
        record={"id":artifact_id,"job_id":job_id,"task_id":task_id,"name":name or path.name,"relative_path":rel,
                "sha256":digest,"size_bytes":size,"media_type":mimetypes.guess_type(path.name)[0],
                "provenance":source_provenance,"license":source_provenance.get("license",{"status":"unknown"}),
                "validation":validation or {"status":"NOT_RUN"},"created_at":now}
        manifest_dir=self.root/"manifests"; manifest_dir.mkdir(parents=True,exist_ok=True)
        manifest_path=manifest_dir/f"{artifact_id}.json"
        record["manifest_path"]=str(manifest_path)
        manifest_path.write_text(json.dumps(record,indent=2,sort_keys=True),encoding="utf-8")
        with self.db.connect() as c:
            c.execute("INSERT INTO artifacts(id,job_id,task_id,name,relative_path,sha256,size_bytes,media_type,provenance_json,validation_json,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (artifact_id,job_id,task_id,record["name"],rel,digest,size,record["media_type"],json.dumps(record["provenance"]),json.dumps(record["validation"]),now))
        return record
    def list(self, job_id: str | None=None) -> list[dict]:
        with self.db.connect() as c:
            rows=c.execute("SELECT * FROM artifacts"+(" WHERE job_id=?" if job_id else "")+" ORDER BY created_at",((job_id,) if job_id else ())).fetchall()
        return [self._decode(r) for r in rows]
    def review(self, artifact_id: str, *, reviewer: str, license_status: str | None=None,
               license_identifier: str | None=None, license_source_url: str | None=None,
               validation_status: str | None=None, notes: str="") -> dict:
        if not reviewer.strip(): raise ValidationError("A named human reviewer is required")
        if license_status is None and validation_status is None: raise ValidationError("Provide a license and/or validation review result")
        allowed_license={"cleared","restricted","unknown","blocked"}
        allowed_validation={"NOT_RUN","PASS","FAIL"}
        with self.db.connect() as c:
            row=c.execute("SELECT * FROM artifacts WHERE id=?",(artifact_id,)).fetchone()
            if not row: raise NotFound(f"Artifact not found: {artifact_id}")
            provenance=json.loads(row["provenance_json"]); validation=json.loads(row["validation_json"])
            if license_status:
                if license_status not in allowed_license: raise ValidationError(f"Invalid license status: {license_status}")
                if license_status=="cleared" and not (license_identifier or license_source_url or notes.strip()):
                    raise ValidationError("License clearance requires a license identifier, source URL or documented rationale")
                provenance["license"]={"status":license_status,"identifier":license_identifier,"source_url":license_source_url,
                                        "reviewer":reviewer,"reviewed_at":utc_now(),"notes":notes,"review_required":license_status!="cleared"}
            if validation_status:
                if validation_status not in allowed_validation: raise ValidationError(f"Invalid validation status: {validation_status}")
                if validation_status in {"PASS","FAIL"} and not notes.strip(): raise ValidationError("A validation PASS/FAIL requires review notes/evidence rationale")
                validation={"status":validation_status,"reviewer":reviewer,"reviewed_at":utc_now(),"notes":notes}
            c.execute("UPDATE artifacts SET provenance_json=?,validation_json=? WHERE id=?",
                      (json.dumps(provenance,sort_keys=True),json.dumps(validation,sort_keys=True),artifact_id))
            self.db.event(c,"artifact",artifact_id,"ARTIFACT_REVIEWED",{"reviewer":reviewer,"license_status":license_status,"validation_status":validation_status,"notes":notes},utc_now())
        manifest=self.root/"manifests"/f"{artifact_id}.json"
        if manifest.exists():
            data=json.loads(manifest.read_text(encoding="utf-8")); data["provenance"]=provenance; data["license"]=provenance.get("license",{"status":"unknown"}); data["validation"]=validation
            manifest.write_text(json.dumps(data,indent=2,sort_keys=True),encoding="utf-8")
        return {"artifact_id":artifact_id,"reviewer":reviewer,"license":provenance.get("license"),"validation":validation}
    def verify(self, artifact_id: str) -> dict:
        with self.db.connect() as c: row=c.execute("SELECT * FROM artifacts WHERE id=?",(artifact_id,)).fetchone()
        if not row: raise NotFound(f"Artifact not found: {artifact_id}")
        stored=Path(row["relative_path"])
        if stored.is_absolute(): path=stored
        else: path=safe_workspace_path(self.workspace,row["relative_path"])
        if not path.exists(): return {"id":artifact_id,"status":"FAIL","reason":"FILE_MISSING","path":str(path)}
        digest=_file_sha256(path)
        return {"id":artifact_id,"status":"PASS" if digest==row["sha256"] else "FAIL","expected_sha256":row["sha256"],"actual_sha256":digest,"size_bytes":path.stat().st_size}
    @staticmethod
    def _decode(row):
        d=dict(row); d["provenance"]=json.loads(d.pop("provenance_json")); d["validation"]=json.loads(d.pop("validation_json")); return d


def _file_sha256(path: Path) -> str:
    digest=hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b""): digest.update(chunk)
    return digest.hexdigest()
