"""Gate 2 adapter conformance: typed operations with native read-back.

Live-application tests are skipped when the application is absent so hosted CI
stays green; on the developer workstation they exercise Blender 5.x, Godot
4.7.x, ffmpeg 8.x, Unreal 5.8 records and the Unity CLI for real.
"""
from __future__ import annotations

import json
import shutil
import threading
from dataclasses import replace
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

from elevenvt_studio.adapters.comfyui import ComfyUIAdapter
from elevenvt_studio.errors import AdapterUnavailable, ValidationError

REPO = Path(__file__).resolve().parents[1]

BLENDER = r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
GODOT = r"C:\Users\11vat\tools\ai-game-studio\godot\godot.exe"
COMFY = "http://127.0.0.1:8188"


class Handler(BaseHTTPRequestHandler):
    def _send(self, body):
        payload = json.dumps(body).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        if self.path == "/object_info":
            self._send({"CheckpointLoaderSimple": {}, "KSampler": {}, "SaveImage": {}})
        elif self.path == "/queue":
            self._send({"queue_running": [], "queue_pending": []})
        elif self.path.startswith("/models/"):
            self._send(["test-model.safetensors"])
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        size = int(self.headers.get("Content-Length", "0"))
        self.rfile.read(size)
        if self.path == "/interrupt":
            self._send({"ok": True})
        elif self.path == "/prompt":
            self._send({"prompt_id": "test-prompt"})
        else:
            self.send_response(404)
            self.end_headers()

    def do_DELETE(self):
        if self.path == "/queue":
            self._send({"cleared": True})
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, *args):
        pass


@pytest.fixture
def mock_comfy():
    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()


def _graph():
    return {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {}},
        "2": {"class_type": "KSampler", "inputs": {"model": ["1", 0]}},
        "3": {"class_type": "SaveImage", "inputs": {"images": ["2", 0]}},
    }


def test_validate_workflow_accepts_sound_graph(mock_comfy):
    report = ComfyUIAdapter(mock_comfy).validate_workflow(_graph())
    assert report["valid"] and report["node_count"] == 3 and report["errors"] == []


def test_validate_workflow_rejects_dangling_link(mock_comfy):
    graph = _graph()
    graph["3"]["inputs"] = {"images": ["99", 0]}
    report = ComfyUIAdapter(mock_comfy).validate_workflow(graph)
    assert not report["valid"]
    assert any("99" in e for e in report["errors"])


def test_validate_workflow_flags_placeholders_and_unknown_classes(mock_comfy):
    graph = _graph()
    graph["2"]["inputs"]["seed"] = "__SEED__"
    graph["4"] = {"class_type": "CustomMagicNode", "inputs": {}}
    report = ComfyUIAdapter(mock_comfy).validate_workflow(graph)
    assert report["valid"]
    assert any("__SEED__" in w for w in report["warnings"])
    assert any("CustomMagicNode" in w for w in report["warnings"])


def test_interrupt_clears_mock_queue(mock_comfy):
    report = ComfyUIAdapter(mock_comfy).interrupt(clear_queue=True)
    assert report["interrupted"] and report["queue_cleared"]


@pytest.mark.skipif(not Path(BLENDER).is_file(), reason="Blender not installed")
def test_blender_inspect_reads_native_scene(service, tmp_path):
    src = REPO / "Games" / "emberkeep" / "source" / "assets" / "lantern" / "lantern.blend"
    assert src.is_file()
    dst = tmp_path / "workspace" / "lantern.blend"
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    from elevenvt_studio.adapters.process import ProcessAdapter
    service.config = replace(service.config, workspace=tmp_path / "workspace",
                             blender_executable=BLENDER)
    service.process = ProcessAdapter(service.config.workspace)
    out = service.invoke("blender.inspect_scene", {"blend_path": "lantern.blend"})
    assert out["application_state_verified"] is True
    assert out["report"]["ok"] is True
    assert out["report"]["object_count"] > 0
    assert out["report"]["blender_version"].startswith("5.")


@pytest.mark.skipif(not Path(GODOT).is_file(), reason="Godot not installed")
def test_godot_inspect_reads_native_scene(service):
    games = REPO / "Games"
    assert (games / "emberkeep" / "game" / "tools" / "inspect_scene.gd").is_file()
    from elevenvt_studio.adapters.process import ProcessAdapter
    service.config = replace(service.config, workspace=games,
                             godot_executable=GODOT)
    service.process = ProcessAdapter(service.config.workspace)
    request = service.policy.request("godot.execute", "EXECUTE", "emberkeep/game",
                                     "Native scene read-back conformance")
    service.policy.decide(request["id"], True, "test-reviewer")
    out = service.invoke("godot.inspect_scene",
                         {"project_path": "emberkeep/game", "approval_id": request["id"]})
    assert out["application_state_verified"] is True
    assert out["scene"] == "res://main.tscn"
    assert out["node_count"] > 100


def _comfy_live():
    try:
        import urllib.request
        with urllib.request.urlopen(COMFY + "/system_stats", timeout=5) as response:
            return response.status == 200
    except Exception:
        return False


@pytest.mark.skipif(not _comfy_live(), reason="Live ComfyUI not reachable")
def test_live_interrupt_is_safe_on_idle_queue():
    report = ComfyUIAdapter(COMFY).interrupt()
    assert report["interrupted"] is True
    assert report["running_before"] == 0


@pytest.mark.skipif(not _comfy_live(), reason="Live ComfyUI not reachable")
def test_live_validate_flags_golden_workflow_placeholders():
    raw = json.loads((REPO / "workflows" / "generation" / "flux2_klein_txt2img.api.json").read_text())
    graph = {k: v for k, v in raw.items() if not k.startswith("_")}
    report = ComfyUIAdapter(COMFY).validate_workflow(graph)
    assert report["valid"] and report["node_count"] == 11
    assert any("__PROMPT__" in w or "__WIDTH__" in w for w in report["warnings"])


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")
def test_media_probe_reports_streams(service, tmp_path):
    from elevenvt_studio.adapters.media import MediaAdapter
    service.config = replace(service.config, workspace=tmp_path)
    service.media = MediaAdapter(service.config.workspace)
    media = service.media
    tone = tmp_path / "tone.wav"
    proc = media._run(media._executable("ffmpeg"),
                      ["-hide_banner", "-v", "error", "-f", "lavfi",
                       "-i", "sine=frequency=440:duration=2", str(tone)], 60)
    assert proc["returncode"] == 0 and tone.is_file()
    report = service.invoke("media.probe", {"path": "tone.wav"})
    assert report["stream_count"] >= 1
    assert report["streams"][0]["codec_type"] == "audio"


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")
def test_media_transcode_never_overwrites(service, tmp_path):
    from elevenvt_studio.adapters.media import MediaAdapter
    service.config = replace(service.config, workspace=tmp_path)
    service.media = MediaAdapter(service.config.workspace)
    media = service.media
    tone = tmp_path / "tone.wav"
    media._run(media._executable("ffmpeg"),
               ["-hide_banner", "-v", "error", "-f", "lavfi",
                "-i", "sine=frequency=440:duration=2", str(tone)], 60)
    request = service.policy.request("media.transcode", "EXECUTE", "tone.ogg",
                                     "Transcode conformance")
    service.policy.decide(request["id"], True, "test-reviewer")
    out = service.invoke("media.transcode",
                         {"src": "tone.wav", "dst": "tone.ogg",
                          "audio_codec": "libopus", "approval_id": request["id"]})
    assert out["verification"]["stream_count"] >= 1
    with pytest.raises(ValidationError):
        service.invoke("media.transcode",
                       {"src": "tone.wav", "dst": "tone.ogg",
                        "audio_codec": "libopus", "approval_id": request["id"]})


def test_unreal_health_reads_authoritative_build_record(service):
    record = Path(r"C:\Program Files\Epic Games\UE_5.8\Engine\Build\Build.version")
    if not record.is_file():
        pytest.skip("Unreal Engine not installed")
    out = service.invoke("unreal.health", {})
    assert out["found"] is True
    assert out["build_version"]["MajorVersion"] == 5
    assert "UnrealEditor" in out["executable"]


def test_unity_health_reports_cli_and_empty_inventory(service):
    cli = Path(r"C:\Users\11vat\AppData\Local\Unity\bin\unity.exe")
    if not cli.is_file():
        pytest.skip("Unity CLI not installed")
    out = service.invoke("unity.health", {})
    assert out["found"] is True
    assert out["version"] != ""


def test_job_cancel_before_run_never_starts(service):
    job = service.jobs.create({"name": "cancel-never-starts", "tasks": [
        {"id": "t1", "capability": "workspace.write_text",
         "inputs": {"path": "cancel/a.txt", "content": "must not exist"}},
        {"id": "t2", "capability": "workspace.write_text",
         "inputs": {"path": "cancel/b.txt", "content": "must not exist"}}]})
    cancelled = service.jobs.cancel(job["id"], reason="operator stop")
    assert cancelled["status"] == "CANCELLED"
    result = service.jobs.run(job["id"])
    assert result["status"] == "CANCELLED"
    assert all(t["attempt"] == 0 for t in result["tasks"])
    assert not (service.config.workspace / "cancel" / "a.txt").exists()


def test_job_cancel_mid_run_stops_at_boundary(service):
    release = threading.Event()
    started = threading.Event()
    original = service.invoke

    def gated(capability_id, inputs, **kwargs):
        if capability_id == "workspace.write_text" and inputs.get("path") == "cancel/c1.txt":
            started.set()
            assert release.wait(timeout=60)
        return original(capability_id, inputs, **kwargs)

    service.invoke = gated
    job = service.jobs.create({"name": "cancel-mid-run", "tasks": [
        {"id": "t1", "capability": "workspace.write_text",
         "inputs": {"path": "cancel/c1.txt", "content": "first"}},
        {"id": "t2", "capability": "workspace.write_text",
         "inputs": {"path": "cancel/c2.txt", "content": "second"}}]})
    outcome = {}

    def run():
        outcome["result"] = service.jobs.run(job["id"])

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    try:
        assert started.wait(timeout=60)
        cancelled = service.jobs.cancel(job["id"], reason="operator stop")
        assert cancelled["status"] == "CANCELLING"
    finally:
        release.set()
    thread.join(timeout=60)
    assert outcome["result"]["status"] == "CANCELLED"
    assert not (service.config.workspace / "cancel" / "c2.txt").exists()


def test_job_cancel_rejects_terminal_jobs(service):
    job = service.jobs.create({"name": "cancel-terminal", "tasks": [
        {"id": "t1", "capability": "studio.status", "inputs": {}}]})
    service.jobs.run(job["id"])
    with pytest.raises(ValidationError):
        service.jobs.cancel(job["id"])


def test_job_cancel_running_is_nonterminal_request(service):
    job = service.jobs.create({"name": "cancel-nonterminal", "tasks": [
        {"id": "t1", "capability": "studio.status", "inputs": {}}]})
    with service.db.connect() as c:
        c.execute("UPDATE jobs SET status='RUNNING' WHERE id=?", (job["id"],))
    requested = service.jobs.cancel(job["id"], reason="operator stop")
    assert requested["status"] == "CANCELLING"
    with pytest.raises(ValidationError):
        service.jobs.cancel(job["id"], reason="operator stop again")
    result = service.jobs.run(job["id"])
    assert result["status"] == "CANCELLED"
    assert all(t["attempt"] == 0 for t in result["tasks"])


def test_cancel_then_crash_quarantines_for_reconciliation(service):
    job = service.jobs.create({"name": "cancel-crash", "tasks": [
        {"id": "t1", "capability": "studio.status", "inputs": {}}]})
    with service.db.connect() as c:
        c.execute("UPDATE jobs SET status='CANCELLING' WHERE id=?", (job["id"],))
        c.execute("UPDATE tasks SET status='RUNNING',attempt=1 WHERE job_id=? AND id='t1'",
                  (job["id"],))
    result = service.jobs.run(job["id"])
    assert result["status"] == "NEEDS_RECONCILIATION"
    assert result["tasks"][0]["status"] == "NEEDS_RECONCILIATION"
    assert result["tasks"][0]["error"]["code"] == "WORKER_CRASH_RECOVERY_REQUIRED"


def test_cancel_applied_after_completion_never_reports_succeeded(service):
    job = service.jobs.create({"name": "cancel-after-tasks", "tasks": [
        {"id": "t1", "capability": "studio.status", "inputs": {}}]})
    with service.db.connect() as c:
        c.execute("UPDATE tasks SET status='SUCCEEDED',outputs_json='{}' "
                  "WHERE job_id=? AND id='t1'", (job["id"],))
        c.execute("UPDATE jobs SET status='CANCELLING' WHERE id=?", (job["id"],))
    result = service.jobs.run(job["id"])
    assert result["status"] == "CANCELLED"


def test_cancel_during_final_task_never_reports_succeeded(service):
    job = service.jobs.create({"name": "cancel-final-task", "tasks": [
        {"id": "t1", "capability": "studio.status", "inputs": {}}]})
    original = service.invoke

    def cancel_then_run(capability_id, inputs, **kwargs):
        service.jobs.cancel(kwargs["job_id"], reason="operator stop")
        return original(capability_id, inputs, **kwargs)

    service.invoke = cancel_then_run
    try:
        result = service.jobs.run(job["id"])
    finally:
        service.invoke = original
    assert result["status"] == "CANCELLED"
    assert result["tasks"][0]["status"] == "SUCCEEDED"


def test_cancel_in_startup_window_never_executes(service):
    engine = service.jobs
    job = engine.create({"name": "cancel-startup-race", "tasks": [
        {"id": "t1", "capability": "studio.status", "inputs": {}}]})
    entered = threading.Event()
    release = threading.Event()
    failures = []
    original_claim = engine._claim_running

    def pausing_claim(c, job_id):
        entered.set()
        assert release.wait(timeout=60)
        return original_claim(c, job_id)

    def guarded_run():
        try:
            engine.run(job["id"])
        except Exception as exc:  # noqa: BLE001 -- surfaced below
            failures.append(exc)

    engine._claim_running = pausing_claim
    runner = threading.Thread(target=guarded_run, daemon=True)
    try:
        runner.start()
        assert entered.wait(timeout=60)
        # Worker is paused after the entry read, before the claim write:
        # the cancel lands exactly in the startup race window.
        cancelled = engine.cancel(job["id"], reason="operator stop")
        assert cancelled["status"] == "CANCELLED"
        release.set()
        runner.join(timeout=120)
    finally:
        engine._claim_running = original_claim
    assert not failures
    assert not runner.is_alive()
    result = engine.status(job["id"])
    assert result["status"] == "CANCELLED"
    assert all(t["attempt"] == 0 for t in result["tasks"])


def test_cancel_between_final_read_and_write_never_reports_succeeded(service):
    engine = service.jobs
    job = engine.create({"name": "cancel-completion-race", "tasks": [
        {"id": "t1", "capability": "studio.status", "inputs": {}}]})
    entered = threading.Event()
    release = threading.Event()
    failures = []
    original_invoke = service.invoke

    def blocking_invoke(capability_id, inputs, **kwargs):
        entered.set()
        assert release.wait(timeout=60)
        return original_invoke(capability_id, inputs, **kwargs)

    def guarded_run():
        try:
            engine.run(job["id"])
        except Exception as exc:  # noqa: BLE001 -- surfaced below
            failures.append(exc)

    service.invoke = blocking_invoke
    runner = threading.Thread(target=guarded_run, daemon=True)
    try:
        runner.start()
        assert entered.wait(timeout=60)
        # Worker is inside the final task, past its last job-status read:
        # the cancel lands between that read and the aggregation write.
        engine.cancel(job["id"], reason="operator stop")
        release.set()
        runner.join(timeout=120)
    finally:
        service.invoke = original_invoke
    assert not failures
    assert not runner.is_alive()
    result = engine.status(job["id"])
    assert result["status"] == "CANCELLED"
    assert result["tasks"][0]["status"] == "SUCCEEDED"


def test_media_extra_args_rejects_workspace_escape(service, tmp_path):
    from elevenvt_studio.adapters.media import MediaAdapter
    media = MediaAdapter(tmp_path)
    (tmp_path / "tone.wav").write_bytes(b"RIFF" + b"\0" * 44)
    for evil in (["-i", "other.wav"], ["-y"], ["pipe:1"],
                 ["-filter_complex", "aevalsrc=0"], ["-map", "0"],
                 ["-b:a"], ["-b:a", "128k", "-f", "mp3"],
                 ["-b:a", ";rm -rf"], ["-c:a", "libopus"],
                 ["-movflags", "faststart", "-ss"]):
        with pytest.raises(ValidationError):
            media.transcode("tone.wav", "out.ogg", extra_args=evil)
    assert not (tmp_path / "out.ogg").exists()


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")
def test_media_extra_args_accepts_safe_tuning(service, tmp_path):
    from elevenvt_studio.adapters.media import MediaAdapter
    service.config = replace(service.config, workspace=tmp_path)
    service.media = MediaAdapter(service.config.workspace)
    media = service.media
    tone = tmp_path / "tone.wav"
    media._run(media._executable("ffmpeg"),
               ["-hide_banner", "-v", "error", "-f", "lavfi",
                "-i", "sine=frequency=440:duration=1", str(tone)], 60)
    request = service.policy.request("media.transcode", "EXECUTE", "tone-tuned.ogg",
                                     "Safe tuning conformance")
    service.policy.decide(request["id"], True, "test-reviewer")
    out = service.invoke("media.transcode",
                         {"src": "tone.wav", "dst": "tone-tuned.ogg",
                          "audio_codec": "libopus", "extra_args": ["-b:a", "96k"],
                          "approval_id": request["id"]})
    assert out["verification"]["stream_count"] >= 1


@pytest.mark.skipif(not Path(GODOT).is_file(), reason="Godot not installed")
def test_godot_inspect_writes_unique_evidence_paths(service):
    from elevenvt_studio.adapters.process import ProcessAdapter
    service.config = replace(service.config, workspace=REPO / "Games",
                             godot_executable=GODOT)
    service.process = ProcessAdapter(service.config.workspace)
    request = service.policy.request("godot.execute", "EXECUTE", "emberkeep/game",
                                     "Unique evidence conformance")
    service.policy.decide(request["id"], True, "test-reviewer")
    first = service.invoke("godot.inspect_scene",
                           {"project_path": "emberkeep/game", "approval_id": request["id"]})
    second = service.invoke("godot.inspect_scene",
                            {"project_path": "emberkeep/game", "approval_id": request["id"]})
    assert first["report_path"] != second["report_path"]
    assert Path(first["report_path"]).is_file()
    assert Path(second["report_path"]).is_file()
