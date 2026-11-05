"""Execution-boundary trace ledger.

Every meaningful call the studio makes writes a row before it happens and a row
update after. The ledger's job is to make invisible execution impossible: if a
model was invoked, a file was written or a human approved something, there is a
record with a digest, a boundary and an outcome — or a visible gap.

It stores digests, never payloads. Secrets are redacted before hashing.
"""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from contextlib import contextmanager
from typing import Any, Iterator, Mapping

from .db import Database
from .errors import NotFound, ValidationError
from .policy import utc_now
from .quality.taxonomy import FailureClass, classify, outcome_for

BOUNDARIES = ("agent", "mcp", "cli", "engine", "human")
OUTCOMES = ("ok", "failed", "denied", "uncertain")
_SECRET_KEY = re.compile(r"(api[_-]?key|token|secret|password|authorization|credential)", re.IGNORECASE)
REDACTED = "***REDACTED***"


def redact(payload: Any) -> Any:
    """Recursively replace secret-looking values before they can be stored or hashed."""
    if isinstance(payload, Mapping):
        return {
            key: REDACTED if _SECRET_KEY.search(str(key)) else redact(value)
            for key, value in payload.items()
        }
    if isinstance(payload, (list, tuple)):
        return [redact(item) for item in payload]
    return payload


def _digest(payload: Any) -> str | None:
    if payload is None:
        return None
    encoded = json.dumps(redact(payload), sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class Ledger:
    def __init__(self, db: Database):
        self.db = db

    def start(
        self,
        *,
        kind: str,
        boundary: str,
        target: str,
        inputs: Mapping[str, Any] | None = None,
        job_id: str | None = None,
        task_id: str | None = None,
    ) -> str:
        if boundary not in BOUNDARIES:
            raise ValidationError(f"Unknown execution boundary: {boundary}")
        if not kind.strip() or not target.strip():
            raise ValidationError("An operation needs a kind and a target")

        op_id = str(uuid.uuid4())
        with self.db.connect() as conn:
            conn.execute(
                "INSERT INTO operations(id,job_id,task_id,kind,boundary,target,started_at,outcome,"
                "request_digest,inputs_json) VALUES(?,?,?,?,?,?,?,?,?,?)",
                (
                    op_id,
                    job_id,
                    task_id,
                    kind,
                    boundary,
                    target,
                    utc_now(),
                    "uncertain",  # until finish() says otherwise, an in-flight op is not a success
                    _digest(inputs),
                    json.dumps(redact(dict(inputs or {})), sort_keys=True, default=str),
                ),
            )
        return op_id

    def finish(
        self,
        op_id: str,
        *,
        outcome: str,
        outputs: Mapping[str, Any] | None = None,
        failure: BaseException | None = None,
        notes: str | None = None,
    ) -> dict:
        if outcome not in OUTCOMES:
            raise ValidationError(f"Unknown outcome: {outcome}")
        failure_class = None
        if failure is not None:
            failure_class, reason = classify(failure)
            notes = f"{notes + '; ' if notes else ''}{failure_class.value}: {reason}"

        with self.db.connect() as conn:
            row = conn.execute("SELECT id FROM operations WHERE id=?", (op_id,)).fetchone()
            if row is None:
                raise NotFound(f"Operation not found: {op_id}")
            conn.execute(
                "UPDATE operations SET finished_at=?, outcome=?, failure_class=?, notes=?,"
                " response_digest=?, outputs_json=? WHERE id=?",
                (
                    utc_now(),
                    outcome,
                    failure_class.value if failure_class else None,
                    notes,
                    _digest(outputs),
                    json.dumps(redact(dict(outputs or {})), sort_keys=True, default=str),
                    op_id,
                ),
            )
        return self.show(op_id)

    @contextmanager
    def context(
        self,
        *,
        kind: str,
        boundary: str,
        target: str,
        inputs: Mapping[str, Any] | None = None,
        job_id: str | None = None,
        task_id: str | None = None,
    ) -> Iterator[str]:
        """Record an operation for the duration of a block. Never swallows the exception."""
        op_id = self.start(kind=kind, boundary=boundary, target=target, inputs=inputs, job_id=job_id, task_id=task_id)
        try:
            yield op_id
        except BaseException as exc:  # noqa: BLE001 - recorded, then re-raised unchanged
            self.finish(op_id, outcome=outcome_for(exc), failure=exc)
            raise
        else:
            self.finish(op_id, outcome="ok")

    def record_denial(self, *, kind: str, boundary: str, target: str, reason: str,
                      inputs: Mapping[str, Any] | None = None, job_id: str | None = None) -> str:
        """Policy refusals are evidence too: record what was not allowed and why."""
        from .errors import PermissionDenied

        op_id = self.start(kind=kind, boundary=boundary, target=target, inputs=inputs, job_id=job_id)
        # Carried as a failure so the class is POLICY_DENIED in the aggregate counts, while the
        # outcome stays 'denied' — a refusal is not a malfunction.
        self.finish(op_id, outcome="denied", failure=PermissionDenied(reason))
        return op_id

    def show(self, op_id: str) -> dict:
        with self.db.connect() as conn:
            row = conn.execute("SELECT * FROM operations WHERE id=?", (op_id,)).fetchone()
        if row is None:
            raise NotFound(f"Operation not found: {op_id}")
        return self._decode(row)

    def list_operations(self, job_id: str | None = None, limit: int = 100) -> list[dict]:
        query = "SELECT * FROM operations"
        params: tuple = ()
        if job_id:
            query += " WHERE job_id=?"
            params = (job_id,)
        query += " ORDER BY started_at DESC LIMIT ?"
        with self.db.connect() as conn:
            rows = conn.execute(query, params + (max(1, min(int(limit), 1000)),)).fetchall()
        return [self._decode(row) for row in rows]

    def gaps(self, job_id: str | None = None) -> list[dict]:
        """Operations that never resolved. A non-empty result means the record is incomplete."""
        query = "SELECT * FROM operations WHERE finished_at IS NULL OR outcome='uncertain'"
        params: tuple = ()
        if job_id:
            query += " AND job_id=?"
            params = (job_id,)
        query += " ORDER BY started_at"
        with self.db.connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [self._decode(row) for row in rows]

    def failure_summary(self, job_id: str | None = None) -> dict[str, int]:
        query = "SELECT failure_class, COUNT(*) AS n FROM operations WHERE failure_class IS NOT NULL"
        params: tuple = ()
        if job_id:
            query += " AND job_id=?"
            params = (job_id,)
        query += " GROUP BY failure_class"
        with self.db.connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return {row["failure_class"]: row["n"] for row in rows}

    @staticmethod
    def _decode(row) -> dict:
        record = dict(row)
        record["inputs"] = json.loads(record.pop("inputs_json") or "{}")
        record["outputs"] = json.loads(record.pop("outputs_json") or "{}")
        return record
