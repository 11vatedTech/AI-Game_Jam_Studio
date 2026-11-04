from __future__ import annotations
import json, uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from .errors import ApprovalRequired, PermissionDenied, ValidationError


def utc_now() -> str: return datetime.now(timezone.utc).isoformat()

class PolicyEngine:
    def __init__(self, policy_file: Path, db):
        self.policy_file, self.db = policy_file, db
        self.policy = json.loads(policy_file.read_text(encoding="utf-8")) if policy_file.exists() else {"default_decision":"deny"}
        if self.policy.get("version") != 1 or self.policy.get("default_decision") != "deny":
            raise ValidationError("Policy must be version 1 and default-deny; permissive or unknown policy formats are rejected")
        valid_effects={"READ","CREATE","MODIFY","DELETE","EXECUTE","NETWORK","CREDENTIAL","PUBLISH"}
        if not isinstance(self.policy.get("auto_allow",[]),list) or not isinstance(self.policy.get("approval_required",[]),list) or not isinstance(self.policy.get("blocked_scopes",[]),list):
            raise ValidationError("Policy collections must be arrays")
        for rule in self.policy.get("auto_allow",[]):
            if not isinstance(rule,dict) or not isinstance(rule.get("scope"),str) or rule.get("side_effect") not in valid_effects:
                raise ValidationError("Invalid auto_allow policy rule")
            if "*" in rule["scope"]: raise ValidationError("Wildcard scopes are not permitted")
        if any(effect not in valid_effects for effect in self.policy.get("approval_required",[])):
            raise ValidationError("Unknown side-effect class in approval_required")
    def authorize(self, scope: str, side_effect: str, target: str, *, approval_id: str | None = None) -> None:
        blocked = self.policy.get("blocked_scopes", [])
        if scope in blocked: raise PermissionDenied(f"Scope is explicitly blocked: {scope}")
        for rule in self.policy.get("auto_allow", []):
            if rule.get("scope")==scope and rule.get("side_effect")==side_effect: return
        if side_effect in self.policy.get("approval_required", []):
            if approval_id and self._approved(approval_id,scope,side_effect,target): return
            raise ApprovalRequired(f"Approval required for {side_effect} / {scope}", details={"scope":scope,"side_effect":side_effect,"target":target})
        raise PermissionDenied(f"No policy grant for {side_effect} / {scope}")
    def _approved(self, approval_id: str, scope: str, side_effect: str, target: str) -> bool:
        with self.db.connect() as c: row=c.execute("SELECT * FROM approvals WHERE id=?",(approval_id,)).fetchone()
        if not row or row["status"]!="APPROVED": return False
        if row["scope"]!=scope or row["side_effect"]!=side_effect or row["target"]!=target: return False
        if row["expires_at"] and datetime.fromisoformat(row["expires_at"]) < datetime.now(timezone.utc): return False
        return True
    def request(self, scope: str, side_effect: str, target: str, reason: str, *, ttl_hours: int=24) -> dict:
        if not scope.strip() or not target.strip() or not reason.strip(): raise ValidationError("Scope, target and reason are required")
        if ttl_hours < 1 or ttl_hours > 168: raise ValidationError("Approval TTL must be between 1 and 168 hours")
        if scope in self.policy.get("blocked_scopes",[]): raise PermissionDenied(f"Scope is explicitly blocked: {scope}")
        approval_id=str(uuid.uuid4()); now=datetime.now(timezone.utc); expires=(now+timedelta(hours=ttl_hours)).isoformat()
        with self.db.connect() as c:
            c.execute("INSERT INTO approvals(id,scope,side_effect,target,reason,status,requested_at,expires_at) VALUES(?,?,?,?,?,?,?,?)",
                      (approval_id,scope,side_effect,target,reason,"PENDING",now.isoformat(),expires))
        return {"id":approval_id,"scope":scope,"side_effect":side_effect,"target":target,"reason":reason,"status":"PENDING","expires_at":expires}
    def decide(self, approval_id: str, approved: bool, approver: str, evidence: dict | None=None) -> dict:
        with self.db.connect() as c:
            row=c.execute("SELECT * FROM approvals WHERE id=?",(approval_id,)).fetchone()
            if not row: raise ValidationError(f"Unknown approval: {approval_id}")
            if row["status"] != "PENDING": raise ValidationError(f"Approval is already {row['status']}; create a new request instead")
            if row["expires_at"] and datetime.fromisoformat(row["expires_at"]) < datetime.now(timezone.utc):
                raise ValidationError("Approval request has expired")
            status="APPROVED" if approved else "REJECTED"
            c.execute("UPDATE approvals SET status=?,approved_at=?,approved_by=?,evidence_json=? WHERE id=?",
                      (status,utc_now(),approver,json.dumps(evidence or {}),approval_id))
        return {"id":approval_id,"status":status,"approved_by":approver}

    def list(self, status: str | None=None) -> list[dict]:
        with self.db.connect() as c:
            if status:
                rows=c.execute("SELECT * FROM approvals WHERE status=? ORDER BY requested_at DESC",(status.upper(),)).fetchall()
            else:
                rows=c.execute("SELECT * FROM approvals ORDER BY requested_at DESC").fetchall()
        result=[]
        for row in rows:
            item=dict(row)
            if item.get("evidence_json"):
                item["evidence"]=json.loads(item.pop("evidence_json"))
            else: item.pop("evidence_json",None)
            result.append(item)
        return result
