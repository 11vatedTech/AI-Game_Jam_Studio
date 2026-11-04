from __future__ import annotations
import json, sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

SCHEMA_VERSION = 1

SCHEMA = """
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS jobs (
 id TEXT PRIMARY KEY, name TEXT NOT NULL, status TEXT NOT NULL, spec_json TEXT NOT NULL,
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL, started_at TEXT, finished_at TEXT,
 error_json TEXT, workspace TEXT NOT NULL, version INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS tasks (
 id TEXT NOT NULL, job_id TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
 capability_id TEXT NOT NULL, status TEXT NOT NULL, inputs_json TEXT NOT NULL,
 outputs_json TEXT, depends_on_json TEXT NOT NULL, attempt INTEGER NOT NULL DEFAULT 0,
 started_at TEXT, finished_at TEXT, error_json TEXT, PRIMARY KEY(job_id,id)
);
CREATE TABLE IF NOT EXISTS events (
 seq INTEGER PRIMARY KEY AUTOINCREMENT, entity_type TEXT NOT NULL, entity_id TEXT NOT NULL,
 event_type TEXT NOT NULL, payload_json TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS artifacts (
 id TEXT PRIMARY KEY, job_id TEXT, task_id TEXT, name TEXT NOT NULL, relative_path TEXT NOT NULL,
 sha256 TEXT NOT NULL, size_bytes INTEGER NOT NULL, media_type TEXT, provenance_json TEXT NOT NULL,
 validation_json TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS approvals (
 id TEXT PRIMARY KEY, scope TEXT NOT NULL, side_effect TEXT NOT NULL, target TEXT NOT NULL,
 reason TEXT NOT NULL, status TEXT NOT NULL, requested_at TEXT NOT NULL, approved_at TEXT,
 approved_by TEXT, expires_at TEXT, evidence_json TEXT
);
CREATE TABLE IF NOT EXISTS reviews (
 id TEXT PRIMARY KEY, job_id TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
 review_type TEXT NOT NULL, verdict TEXT NOT NULL, reviewer TEXT NOT NULL, rationale TEXT NOT NULL,
 evidence_json TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_tasks_job_status ON tasks(job_id,status);
CREATE INDEX IF NOT EXISTS idx_events_entity ON events(entity_type,entity_id,seq);
CREATE INDEX IF NOT EXISTS idx_artifacts_job ON artifacts(job_id);
CREATE INDEX IF NOT EXISTS idx_reviews_job_type ON reviews(job_id,review_type,created_at);
"""

class Database:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as conn:
            current = int(conn.execute("PRAGMA user_version").fetchone()[0])
            if current > SCHEMA_VERSION:
                raise RuntimeError(f"Database schema version {current} is newer than this runtime supports ({SCHEMA_VERSION})")
            if current < 1:
                # Idempotent bootstrap is also the migration from the original unversioned v0.2 preview DB.
                conn.executescript(SCHEMA)
                conn.execute(f"PRAGMA user_version={SCHEMA_VERSION}")
            conn.execute("PRAGMA journal_mode=WAL")
    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA busy_timeout=30000")
        conn.execute("PRAGMA synchronous=FULL")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    def event(self, conn: sqlite3.Connection, entity_type: str, entity_id: str, event_type: str, payload: dict, at: str) -> None:
        conn.execute("INSERT INTO events(entity_type,entity_id,event_type,payload_json,created_at) VALUES(?,?,?,?,?)",
                     (entity_type,entity_id,event_type,json.dumps(payload,sort_keys=True),at))
    def events(self, entity_type: str, entity_id: str) -> list[dict]:
        with self.connect() as c:
            rows=c.execute("SELECT * FROM events WHERE entity_type=? AND entity_id=? ORDER BY seq",(entity_type,entity_id)).fetchall()
            return [dict(r) | {"payload":json.loads(r["payload_json"])} for r in rows]

    def integrity_check(self) -> dict:
        with self.connect() as c:
            rows=c.execute("PRAGMA integrity_check").fetchall()
            foreign=c.execute("PRAGMA foreign_key_check").fetchall()
        messages=[r[0] for r in rows]
        return {"integrity":"PASS" if messages==["ok"] and not foreign else "FAIL","messages":messages,
                "foreign_key_violations":[dict(r) for r in foreign]}
    def backup(self, destination: Path) -> dict:
        destination=destination.expanduser().resolve()
        if destination==self.path.resolve(): raise ValueError("Backup destination cannot be the active database")
        destination.parent.mkdir(parents=True,exist_ok=True)
        source=sqlite3.connect(self.path,timeout=30)
        target=sqlite3.connect(destination)
        try:
            source.backup(target)
            target.commit()
            result=target.execute("PRAGMA integrity_check").fetchone()[0]
            if result!="ok": raise RuntimeError(f"Backup integrity check failed: {result}")
        finally:
            target.close(); source.close()
        import hashlib
        digest=hashlib.sha256(destination.read_bytes()).hexdigest()
        return {"path":str(destination),"sha256":digest,"size_bytes":destination.stat().st_size,"integrity":"PASS"}
