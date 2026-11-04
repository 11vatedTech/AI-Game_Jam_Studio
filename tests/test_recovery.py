import json
import sqlite3

import pytest

from elevenvt_studio.db import Database
from elevenvt_studio.errors import ValidationError


def _simulate_crash(service, job_id, task_id):
    with service.db.connect() as conn:
        conn.execute("UPDATE jobs SET status='RUNNING' WHERE id=?", (job_id,))
        conn.execute("UPDATE tasks SET status='RUNNING',attempt=1 WHERE job_id=? AND id=?", (job_id, task_id))


def test_crashed_external_task_is_quarantined_not_replayed(service):
    job = service.jobs.create({"name": "crash-recovery", "tasks": [
        {"id": "write", "capability": "workspace.write_text", "inputs": {"path": "recovery.txt", "content": "must not duplicate"}}
    ]})
    _simulate_crash(service, job["id"], "write")
    result = service.jobs.run(job["id"])
    assert result["status"] == "NEEDS_RECONCILIATION"
    assert result["tasks"][0]["status"] == "NEEDS_RECONCILIATION"
    assert not (service.config.workspace / "recovery.txt").exists()
    # Re-running is safe: quarantine remains until a human decides.
    assert service.jobs.run(job["id"])["status"] == "NEEDS_RECONCILIATION"
    with pytest.raises(ValidationError):
        service.jobs.reconcile(job["id"], "write", action="mark_succeeded", reviewer="operator", evidence="checked")


def test_human_can_retry_after_confirming_external_effect_did_not_occur(service):
    job = service.jobs.create({"name": "retry-after-inspection", "tasks": [
        {"id": "write", "capability": "workspace.write_text", "inputs": {"path": "retry.txt", "content": "retry exactly once"}}
    ]})
    _simulate_crash(service, job["id"], "write")
    assert service.jobs.run(job["id"])["status"] == "NEEDS_RECONCILIATION"
    with pytest.raises(ValidationError):
        service.jobs.reconcile(job["id"], "write", action="retry", reviewer="operator", evidence="checked", outputs={})
    resolved = service.jobs.reconcile(job["id"], "write", action="retry", reviewer="operator",
                                      evidence="Inspected target workspace; the file does not exist and the operation did not occur.")
    assert resolved["status"] == "BLOCKED"
    final = service.jobs.run(job["id"])
    assert final["status"] == "SUCCEEDED"
    assert (service.config.workspace / "retry.txt").read_text() == "retry exactly once"
    assert final["tasks"][0]["attempt"] == 2


def test_human_can_mark_task_succeeded_after_readback(service):
    job = service.jobs.create({"name": "mark-complete", "tasks": [
        {"id": "write", "capability": "workspace.write_text", "inputs": {"path": "already-done.txt", "content": "created before process died"}},
        {"id": "verify", "capability": "artifact.list", "depends_on": ["write"], "inputs": {}}
    ]})
    # Simulate external side effect succeeded, but the process died before persisting task success.
    (service.config.workspace / "already-done.txt").write_text("created before process died")
    _simulate_crash(service, job["id"], "write")
    assert service.jobs.run(job["id"])["status"] == "NEEDS_RECONCILIATION"
    resolved = service.jobs.reconcile(job["id"], "write", action="mark_succeeded", reviewer="operator",
                                      evidence="Read back exact target file and compared expected content; file exists with matching bytes.",
                                      outputs={"created": True, "path": "already-done.txt"})
    assert resolved["status"] == "BLOCKED"
    final = service.jobs.run(job["id"])
    assert final["status"] == "SUCCEEDED"  # Downstream can proceed from the explicitly reconciled output.


def test_database_schema_version_is_guarded(tmp_path):
    path = tmp_path / "versioned.sqlite3"
    db = Database(path)
    with db.connect() as conn:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 1
    future = tmp_path / "future.sqlite3"
    conn = sqlite3.connect(future)
    conn.execute("PRAGMA user_version=999")
    conn.close()
    with pytest.raises(RuntimeError, match="newer than this runtime supports"):
        Database(future)
