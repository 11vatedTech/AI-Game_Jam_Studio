import json
from elevenvt_studio.errors import ValidationError

def test_status_and_registry(service):
    status=service.status()
    assert status["product"]=="11vatedTech AI Game Jam Studio"
    assert status["registered_capabilities"] >= 10
    assert any(c["id"]=="comfyui.health" for c in service.registry.list())

def test_foundation_job_persists_and_verifies_artifact(service):
    spec={"name":"smoke","tasks":[
      {"id":"write","capability":"workspace.write_text","inputs":{"path":"test/asset.txt","content":"real file payload"}},
      {"id":"verify","capability":"artifact.verify","depends_on":["write"],"inputs":{"artifact_id":{"$ref":"write.artifact_id"}}}
    ]}
    job=service.jobs.create(spec)
    result=service.jobs.run(job["id"])
    assert result["status"]=="SUCCEEDED"
    assert [t["status"] for t in result["tasks"]]==["SUCCEEDED","SUCCEEDED"]
    artifacts=service.artifacts.list(job["id"])
    assert len(artifacts)==1
    assert service.artifacts.verify(artifacts[0]["id"])["status"]=="PASS"

def test_job_graph_cycle_rejected(service):
    with __import__("pytest").raises(ValidationError):
        service.jobs.create({"name":"cycle","tasks":[
          {"id":"a","capability":"workspace.write_text","depends_on":["b"],"inputs":{}},
          {"id":"b","capability":"workspace.write_text","depends_on":["a"],"inputs":{}}
        ]})

def test_ref_resolver_rejects_missing_output(service):
    from elevenvt_studio.jobs import _resolve_refs
    with __import__("pytest").raises(ValidationError): _resolve_refs({"x":{"$ref":"missing.value"}}, {})

def test_policy_default_deny(service):
    from elevenvt_studio.errors import PermissionDenied
    with __import__("pytest").raises(PermissionDenied): service.policy.authorize("arbitrary.shell","EXECUTE","workspace")

def test_approval_is_bound_to_exact_target(service):
    from elevenvt_studio.errors import ApprovalRequired
    req=service.policy.request("comfyui.queue","NETWORK","workspace","Run a named workflow")
    service.policy.decide(req["id"],True,"human-operator")
    service.policy.authorize("comfyui.queue","NETWORK","workspace",approval_id=req["id"])
    with __import__("pytest").raises(ApprovalRequired):
        service.policy.authorize("comfyui.queue","NETWORK","different-target",approval_id=req["id"])

def test_existing_file_cannot_be_overwritten(service):
    from elevenvt_studio.errors import ValidationError
    service.invoke("workspace.write_text",{"path":"same.txt","content":"first"})
    with __import__("pytest").raises(ValidationError): service.invoke("workspace.write_text",{"path":"same.txt","content":"second"})

def test_manifest_has_explicit_unreviewed_rights_and_hash(service):
    service.invoke("workspace.write_text",{"path":"license-test.txt","content":"unreviewed source"})
    artifact=service.artifacts.list()[0]
    assert artifact["provenance"]["license"]["status"]=="unknown"
    manifest=list((service.config.artifact_root/"manifests").glob("*.json"))
    assert len(manifest)==1
    data=json.loads(manifest[0].read_text())
    assert data["sha256"]==artifact["sha256"]
    assert data["license"]["status"]=="unknown"

def test_database_backup_and_integrity(service,tmp_path):
    backup=service.db.backup(tmp_path/"backup"/"studio.sqlite3")
    assert backup["integrity"]=="PASS" and backup["sha256"]
    assert service.db.integrity_check()["integrity"]=="PASS"

def test_job_list(service):
    job=service.jobs.create({"name":"listed","tasks":[{"id":"one","capability":"workspace.write_text","inputs":{"path":"list.txt","content":"x"}}]})
    assert service.jobs.list()[0]["id"]==job["id"]

def test_rejects_unsafe_job_id(service):
    from elevenvt_studio.errors import ValidationError
    with __import__("pytest").raises(ValidationError):
        service.jobs.create({"id":"../../escape","name":"unsafe","tasks":[{"id":"one","capability":"workspace.write_text","inputs":{}}]})

def test_job_process_lock_conflicts(service):
    from elevenvt_studio.locking import ProcessFileLock
    from elevenvt_studio.errors import Conflict
    lock_path=service.config.home/"job-locks"/"locked-job.lock"
    with ProcessFileLock(lock_path):
        with __import__("pytest").raises(Conflict):
            with ProcessFileLock(lock_path): pass

def test_database_backup_rejects_live_database_as_destination(service):
    with __import__("pytest").raises(ValueError): service.db.backup(service.config.database)

def test_quality_report_requires_explicit_reviews_and_rights(service):
    job=service.jobs.create({"name":"reviewed-output","tasks":[{"id":"write","capability":"workspace.write_text","inputs":{"path":"review.txt","content":"review me"}}]})
    status=service.jobs.run(job["id"])
    artifact_id=status["tasks"][0]["outputs"]["artifact_id"]
    pending=service.quality_report(job["id"])
    assert pending["status"]=="PASS_PENDING_REVIEW"
    assert any(c["id"]=="LICENSE-PROVENANCE" and c["status"]=="NOT_RUN" for c in pending["checks"])
    service.artifacts.review(artifact_id,reviewer="owner",license_status="cleared",license_identifier="Original user-authored content",license_source_url="https://example.invalid/original",validation_status="PASS",notes="Source inspected; output hash and UTF-8 structure verified.")
    service.record_quality_review(job["id"],review_type="technical",verdict="PASS",reviewer="qa-reviewer",rationale="Task graph and artifact hash verified.")
    service.record_quality_review(job["id"],review_type="creative",verdict="PASS",reviewer="art-director",rationale="Human review accepted the stated scope.")
    final=service.quality_report(job["id"])
    assert final["status"]=="PASS_ALL_CHECKS"
    assert final["certified"] is False

def test_license_clearance_requires_supporting_basis(service):
    service.invoke("workspace.write_text",{"path":"rights.txt","content":"source"})
    artifact=service.artifacts.list()[0]
    from elevenvt_studio.errors import ValidationError
    with __import__("pytest").raises(ValidationError):
        service.artifacts.review(artifact["id"],reviewer="reviewer",license_status="cleared")


def test_workspace_path_rejects_windows_dialect_traversal_on_non_windows_hosts(tmp_path):
    from elevenvt_studio.paths import safe_workspace_path
    from elevenvt_studio.errors import ValidationError
    for unsafe in (r"..\outside.txt", r"folder\..\outside.txt", r"C:\outside.txt", r"\\server\share\outside.txt"):
        with __import__("pytest").raises(ValidationError):
            safe_workspace_path(tmp_path, unsafe)
