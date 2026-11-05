"""Godot capture adapter.

Runs the engine against a plan, then refuses to accept the result merely because
the process exited zero. The bundle is loaded, every hash is recomputed, and the
evidence grade is derived by the Studio — the game is not permitted to grant
authority to its own output.

No headless mode: Godot documents that ``--headless`` disables rendering, so an
"offscreen" capture would produce black frames and a critic that blames the art.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import socket
import subprocess
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

from ..errors import AdapterUnavailable, PostconditionFailed, ValidationError
from ..perception.bundle import CaptureBundle, compute_grade
from ..policy import utc_now

REPORT_MARKER = "STUDIO_CAPTURE_JSON"
DEFAULT_ROLES = ["frame"]
DEFAULT_PLAN_TICK = 30


def sha256_file(path: Path | str) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_state(workspace: Path) -> dict:
    def run(*args: str) -> str:
        try:
            result = subprocess.run(
                ["git", *args], cwd=str(workspace), capture_output=True, text=True, timeout=30
            )
        except (OSError, subprocess.SubprocessError):
            return ""
        return result.stdout.strip() if result.returncode == 0 else ""

    commit = run("rev-parse", "HEAD")
    tree = run("rev-parse", "HEAD^{tree}")
    status = run("status", "--porcelain")
    diff = run("diff", "HEAD")
    dirty = bool(status)
    return {
        "commit": commit,
        "dirty": dirty,
        "tree_sha256": hashlib.sha256(tree.encode()).hexdigest() if tree else None,
        "untracked_or_patch_sha256": hashlib.sha256(diff.encode()).hexdigest() if diff else None,
    }


def _atomic_json(path: Path, document: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(document, indent=2, sort_keys=True), encoding="utf-8")
    temporary.replace(path)


@dataclass
class CaptureRun:
    bundle: CaptureBundle
    stdout: str
    stderr: str
    duration_ms: int
    report: dict


class GodotCaptureAdapter:
    def __init__(
        self,
        *,
        godot_executable: str,
        project_path: Path | str,
        captures_root: Path | str,
        workspace_root: Path | str,
        name: str = "emberkeep",
        contract_sha256: str | None = None,
        resolution: tuple[int, int] | None = None,
        fixed_fps: int = 60,
        warmup_frames: int = 30,
        seed: int = 20261105,
        rng_instance_seeds: dict[str, int] | None = None,
        timeout_seconds: int = 240,
        ledger: Any = None,
    ):
        self.godot_executable = godot_executable
        self.project_path = Path(project_path)
        self.captures_root = Path(captures_root)
        self.workspace_root = Path(workspace_root)
        self.name = name
        self.contract_sha256 = contract_sha256
        self.resolution = resolution
        self.fixed_fps = fixed_fps
        self.warmup_frames = warmup_frames
        self.seed = seed
        self.rng_instance_seeds = rng_instance_seeds or {}
        self.timeout_seconds = timeout_seconds
        self.ledger = ledger
        self.last_process: dict | None = None

    # -- plan --------------------------------------------------------------
    def build_plan(self, plan: dict | None, roles: Sequence[str] | None) -> dict:
        roles = list(roles or DEFAULT_ROLES)
        if plan is None:
            return {
                "warmup_frames": self.warmup_frames,
                "default_roles": roles,
                "entries": [
                    {
                        "physics_tick": self.warmup_frames,
                        "roles": roles,
                        "state": {"lantern_lit": True},
                        "camera": {"side": "default"},
                        "seed": self.seed,
                    }
                ],
            }
        if "entries" not in plan or not isinstance(plan["entries"], list):
            raise ValidationError("Capture plan must contain an 'entries' list")
        if plan.get("default_roles") is None:
            plan = dict(plan)
            plan["default_roles"] = roles
        for entry in plan["entries"]:
            if "physics_tick" not in entry:
                raise ValidationError("Every plan entry needs a physics_tick; wall-clock waits are not reproducible")
        return plan

    # -- run ---------------------------------------------------------------
    def capture(self, *, mode: str = "deterministic", plan: dict | None = None, roles: Sequence[str] | None = None) -> CaptureBundle:
        if mode == "live":
            raise AdapterUnavailable(
                "Live capture requires a running session; start one with --capture-live",
                details={"mode": mode},
            )
        if mode != "deterministic":
            raise ValidationError(f"Unknown capture mode: {mode}")
        if not self.project_path.is_dir():
            raise AdapterUnavailable(f"Godot project not found: {self.project_path}")

        context = self._context()
        plan_document = self.build_plan(plan, roles)
        run_dir = self.captures_root / "_runs" / uuid.uuid4().hex
        run_dir.mkdir(parents=True, exist_ok=True)
        plan_path = run_dir / "plan.json"
        _atomic_json(plan_path, plan_document)

        context["plan_sha256"] = sha256_file(plan_path)
        context["started_at"] = utc_now()
        context["started_ms"] = int(time.time() * 1000)
        # The game reads this from its --capture-out directory. One capture at a
        # time is enforced, so a single well-known path is not a race.
        self.captures_root.mkdir(parents=True, exist_ok=True)
        _atomic_json(self.captures_root / "capture-context.json", context)

        before = {path.name for path in self.captures_root.glob("*/bundle.json")}
        started = time.monotonic()
        operation = None
        if self.ledger is not None:
            operation = self.ledger.start(
                kind="perception.capture",
                boundary="engine",
                target=str(self.project_path),
                inputs={"mode": mode, "plan_sha256": context["plan_sha256"], "roles": list(roles or DEFAULT_ROLES)},
            )
        try:
            process = self._run_engine(plan_path, run_dir)
        except BaseException as exc:
            if self.ledger is not None and operation:
                self.ledger.finish(operation, outcome="failed", failure=exc)
            raise

        duration_ms = int((time.monotonic() - started) * 1000)
        if self.ledger is not None and operation:
            self.ledger.finish(
                operation,
                outcome="ok" if process["returncode"] == 0 else "failed",
                outputs={"returncode": process["returncode"], "duration_ms": duration_ms},
            )

        bundle_path = self._locate_bundle(run_dir, before)
        bundle = CaptureBundle.load(bundle_path, root=bundle_path.parent)

        verification = bundle.verify()
        _record_verification(bundle, verification)
        if verification.status != "verified":
            failures = [check.name for check in verification.failures()]
            raise PostconditionFailed(
                "Capture produced a bundle that fails verification",
                details={"capture_id": bundle.capture_id, "failures": failures, "returncode": process["returncode"]},
            )

        self.last_process = process
        return CaptureBundle.load(bundle_path, root=bundle_path.parent)

    def _run_engine(self, plan_path: Path, run_dir: Path) -> dict:
        # Godot resolves relative paths against the project directory after --path,
        # so every path handed to the engine must already be absolute.
        command = [self.godot_executable, "--path", str(self.project_path.resolve())]
        if self.resolution:
            command += ["--resolution", f"{self.resolution[0]}x{self.resolution[1]}"]
        command += [
            "--position",
            "0,0",
            "--fixed-fps",
            str(self.fixed_fps),
            f"--capture-plan={plan_path.resolve()}",
            f"--capture-out={self.captures_root.resolve()}",
        ]

        try:
            completed = subprocess.run(
                command,
                cwd=str(self.workspace_root),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self.timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            raise AdapterUnavailable(
                f"Godot capture exceeded {self.timeout_seconds}s",
                details={"command": command},
            ) from exc
        except OSError as exc:
            raise AdapterUnavailable(f"Godot could not be started: {exc}", details={"command": command}) from exc

        (run_dir / "stdout.log").write_text(completed.stdout or "", encoding="utf-8")
        (run_dir / "stderr.log").write_text(completed.stderr or "", encoding="utf-8")

        report: dict = {}
        for line in (completed.stdout or "").splitlines():
            if line.startswith(REPORT_MARKER):
                try:
                    report = json.loads(line[len(REPORT_MARKER):].strip())
                except json.JSONDecodeError:
                    report = {"ok": False, "failures": ["capture_report_unparseable"]}

        if completed.returncode != 0:
            raise AdapterUnavailable(
                "Godot capture failed",
                details={
                    "returncode": completed.returncode,
                    "report": report,
                    "stderr_tail": (completed.stderr or "")[-2000:],
                    "stdout_tail": (completed.stdout or "")[-2000:],
                },
            )
        return {
            "returncode": completed.returncode,
            "stdout": completed.stdout or "",
            "stderr": completed.stderr or "",
            "report": report,
            "command": command,
        }

    def _locate_bundle(self, run_dir: Path, before: set[str]) -> Path:
        candidates = [
            path
            for path in self.captures_root.glob("*/bundle.json")
            if path.parent.name not in before and path.parent.name != "_runs"
        ]
        if not candidates:
            raise PostconditionFailed(
                "Godot exited cleanly but wrote no bundle; exit status is not evidence",
                details={"run": str(run_dir), "stdout": str(run_dir / "stdout.log")},
            )
        return max(candidates, key=lambda path: path.stat().st_mtime)

    # -- provenance --------------------------------------------------------
    def _context(self) -> dict:
        executable = Path(self.godot_executable)
        return {
            "name": self.name,
            "project_path": str(self.project_path),
            "requested_resolution": list(self.resolution) if self.resolution else None,
            "contract_sha256": self.contract_sha256 or "0" * 64,
            "git": _git_state(self.workspace_root),
            "seed": self.seed,
            "rng_instance_seeds": self.rng_instance_seeds,
            "engine_executable_sha256": sha256_file(executable) if executable.is_file() else None,
            "host": os.name,
            "gpu": None,
        }

    def start_live(self, *, timeout: float = 120.0) -> LiveSession:
        """Launch the game in live mode and return an authenticated session."""
        if not self.project_path.is_dir():
            raise AdapterUnavailable(f"Godot project not found: {self.project_path}")
        self.captures_root.mkdir(parents=True, exist_ok=True)
        context = self._context()
        context["started_at"] = utc_now()
        context["started_ms"] = int(time.time() * 1000)
        _atomic_json(self.captures_root / "capture-context.json", context)

        token = secrets.token_hex(32)
        self.live_token = token
        live_dir = self.captures_root / "__live"
        live_dir.mkdir(parents=True, exist_ok=True)
        token_file = live_dir / "token.txt"
        token_file.write_text(token, encoding="utf-8")
        self.live_acl = self._restrict_token_file(token_file)

        command = [self.godot_executable, "--path", str(self.project_path.resolve())]
        if self.resolution:
            command += ["--resolution", f"{self.resolution[0]}x{self.resolution[1]}"]
        command += [
            "--position",
            "0,0",
            "--capture-live",
            f"--capture-token-file={token_file.resolve()}",
            f"--capture-out={self.captures_root.resolve()}",
        ]
        log_path = live_dir / "godot.log"
        log = log_path.open("w", encoding="utf-8", errors="replace")
        process = subprocess.Popen(
            command, cwd=str(self.workspace_root), stdout=log, stderr=subprocess.STDOUT
        )
        self.live_process = process
        try:
            return LiveSession.connect(self.captures_root, token, timeout=timeout, process=process)
        except BaseException:
            process.terminate()
            raise

    @staticmethod
    def _restrict_token_file(path: Path) -> dict:
        """Restrict the session token to the current user.

        Recorded rather than assumed: a token readable by other local accounts is
        a real weakness, so the outcome travels with the session.
        """
        if os.name != "nt":
            try:
                path.chmod(0o600)
                return {"method": "chmod", "ok": True}
            except OSError as exc:
                return {"method": "chmod", "ok": False, "error": str(exc)}
        user = os.environ.get("USERNAME", "")
        try:
            result = subprocess.run(
                ["icacls", str(path), "/inheritance:r", "/grant:r", f"{user}:R"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            return {
                "method": "icacls",
                "ok": result.returncode == 0,
                "stdout": (result.stdout or "").strip(),
                "stderr": (result.stderr or "").strip(),
            }
        except (OSError, subprocess.SubprocessError) as exc:
            return {"method": "icacls", "ok": False, "error": str(exc)}


def qualify(bundles: Sequence[CaptureBundle], *, runs: int) -> dict:
    """Derive repeatability from measured agreement, never from a flag.

    Exact hashes are preferred. When they differ the empirical delta is recorded
    rather than a tolerance being invented to cover it.
    """
    if not bundles:
        raise ValidationError("Qualification needs at least one bundle")
    if len({bundle.mode for bundle in bundles}) != 1:
        raise ValidationError("Cannot qualify bundles from different capture modes")

    roles = sorted(set(bundles[0].roles()))
    per_role: dict[str, list[str]] = {}
    for role in roles:
        hashes = []
        for bundle in bundles:
            hashes.append(bundle.artifact(role)["sha256"] if bundle.has(role) else "missing")
        per_role[role] = hashes

    identical = all(len(set(hashes)) == 1 for hashes in per_role.values())
    state_digests = {
        json.dumps(bundle.document["request"].get("state", {}), sort_keys=True) for bundle in bundles
    }
    state_equal = len(state_digests) == 1

    if identical and state_equal and len(bundles) >= runs:
        return {
            "status": "qualified",
            "runs": len(bundles),
            "state_digest": hashlib.sha256(next(iter(state_digests)).encode()).hexdigest(),
            "render_contract": "exact_sha256",
            "tolerance": None,
            "measured_max_delta": None,
        }

    return {
        "status": "unqualified",
        "runs": len(bundles),
        "state_digest": None,
        "render_contract": None,
        "tolerance": None,
        "measured_max_delta": {
            "per_role_hash_sets": {role: sorted(set(hashes)) for role, hashes in per_role.items()},
            "state_equal": state_equal,
        },
    }


class LiveSession:
    """Client for one authenticated loopback capture session.

    The server refuses every op until `hello` authenticates on that connection,
    so "connected" is never confused with "authorized".
    """

    MAX_LINE_BYTES = 65536

    def __init__(self, connection: socket.socket, out_dir: Path, process=None):
        self.connection = connection
        self.out_dir = Path(out_dir)
        self.process = process

    @classmethod
    def connect(
        cls, out_dir: Path | str, token: str, *, timeout: float = 60.0, process=None
    ) -> "LiveSession":
        out_dir = Path(out_dir)
        session_file = out_dir / "session.json"
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if session_file.is_file():
                try:
                    session = json.loads(session_file.read_text(encoding="utf-8"))
                    port = int(session["port"])
                except (json.JSONDecodeError, KeyError, ValueError):
                    time.sleep(0.2)
                    continue
                connection = socket.create_connection(("127.0.0.1", port), timeout=timeout)
                live = cls(connection, out_dir, process)
                reply = live.request({"op": "hello", "token": token}, timeout=timeout)
                if not reply.get("ok"):
                    live.close()
                    raise AdapterUnavailable(
                        "Live session refused authentication",
                        details={"reply": reply, "port": port},
                    )
                return live
            time.sleep(0.2)
        raise AdapterUnavailable(
            "Live session did not publish session.json; the game may have failed to start",
            details={"out_dir": str(out_dir), "timeout": timeout},
        )

    def request(self, payload: dict, *, timeout: float = 60.0) -> dict:
        self.connection.settimeout(timeout)
        self.connection.sendall((json.dumps(payload) + "\n").encode("utf-8"))
        data = b""
        while not data.endswith(b"\n"):
            chunk = self.connection.recv(65536)
            if not chunk:
                raise AdapterUnavailable("Live session closed the connection", details={"request": payload.get("op")})
            data += chunk
            if len(data) > self.MAX_LINE_BYTES:
                raise ValidationError("Live response exceeded the 64 KiB line cap")
        return json.loads(data.decode("utf-8"))

    def state(self) -> dict:
        return self.request({"op": "state"})

    def capture(self, roles: Sequence[str] = ("frame",), *, timeout: float = 120.0) -> CaptureBundle:
        reply = self.request({"op": "capture", "roles": list(roles)}, timeout=timeout)
        if not reply.get("ok"):
            raise PostconditionFailed(
                "Live capture failed",
                details={"reply": reply},
            )
        bundle_path = Path(reply["bundle"])
        bundle = CaptureBundle.load(bundle_path, root=bundle_path.parent)
        verification = bundle.verify()
        _record_verification(bundle, verification)
        return CaptureBundle.load(bundle_path, root=bundle_path.parent)

    def close(self) -> None:
        """Close this socket only.

        The game process outlives any single connection: tying them together meant
        closing one client terminated the session other clients could still use.
        Process teardown belongs to the adapter.
        """
        try:
            self.connection.close()
        except OSError:
            pass

    def quit(self, *, timeout: float = 15.0) -> None:
        try:
            self.request({"op": "quit"}, timeout=timeout)
        except AdapterUnavailable:
            pass
        finally:
            self.close()

    def __enter__(self) -> "LiveSession":
        return self

    def __exit__(self, *exc_info) -> None:
        # Releasing the client must not end the game: another client may be next.
        self.close()


def _record_verification(bundle: CaptureBundle, verification) -> None:
    document = dict(bundle.document)
    document["verification"] = verification.to_dict()
    qualification = (document.get("qualification") or {}).get("repeatability") or {}
    document["evidence_grade"] = compute_grade(document["mode"], qualification.get("status"))
    _atomic_json(bundle.root / "bundle.json", document)


def apply_qualification(bundle: CaptureBundle, qualification: dict) -> CaptureBundle:
    document = dict(bundle.document)
    document["qualification"] = {"repeatability": qualification}
    document["evidence_grade"] = compute_grade(document["mode"], qualification.get("status"))
    _atomic_json(bundle.root / "bundle.json", document)
    return CaptureBundle.load(bundle.root / "bundle.json", root=bundle.root)
