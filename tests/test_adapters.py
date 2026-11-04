from http.server import BaseHTTPRequestHandler, HTTPServer
import json, threading, urllib.parse, base64
import pytest
from elevenvt_studio.adapters.comfyui import ComfyUIAdapter
from elevenvt_studio.errors import PermissionDenied
from elevenvt_studio.adapters.process import ProcessAdapter
import sys

PNG_1X1 = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jG7sAAAAASUVORK5CYII=")

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed=urllib.parse.urlparse(self.path)
        if parsed.path=="/system_stats": body={"system":{"device":"cpu"}}
        elif parsed.path=="/queue": body={"queue_running":[],"queue_pending":[]}
        elif parsed.path=="/object_info": body={"CheckpointLoaderSimple":{},"KSampler":{},"SaveImage":{}}
        elif parsed.path.startswith("/models/"): body=["test-model.safetensors"]
        elif parsed.path=="/history/test-prompt": body={"test-prompt":{"status":{"completed":True,"status_str":"success"},"outputs":{"9":{"images":[{"filename":"test.png","subfolder":"","type":"output"}]}}}}
        elif parsed.path=="/redirect":
            self.send_response(302); self.send_header("Location","http://example.com/steal"); self.end_headers(); return
        elif parsed.path=="/view":
            query=urllib.parse.parse_qs(parsed.query)
            if query.get("filename") != ["test.png"]:
                self.send_response(404); self.end_headers(); return
            self.send_response(200); self.send_header("Content-Type","image/png"); self.send_header("Content-Length",str(len(PNG_1X1))); self.end_headers(); self.wfile.write(PNG_1X1); return
        else: self.send_response(404); self.end_headers(); return
        payload=json.dumps(body).encode(); self.send_response(200); self.send_header("Content-Type","application/json"); self.send_header("Content-Length",str(len(payload))); self.end_headers(); self.wfile.write(payload)
    def do_POST(self):
        size=int(self.headers.get("Content-Length","0")); request=json.loads(self.rfile.read(size))
        assert "prompt" in request
        payload=json.dumps({"prompt_id":"test-prompt"}).encode(); self.send_response(200); self.send_header("Content-Type","application/json"); self.send_header("Content-Length",str(len(payload))); self.end_headers(); self.wfile.write(payload)
    def log_message(self,*args): pass

@pytest.fixture
def comfy_server():
    server=HTTPServer(("127.0.0.1",0),Handler); thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start()
    try: yield f"http://127.0.0.1:{server.server_port}"
    finally: server.shutdown(); thread.join(timeout=2); server.server_close()

def test_comfyui_native_http_adapter(comfy_server,tmp_path):
    adapter=ComfyUIAdapter(comfy_server)
    assert adapter.health()["adapter"]=="comfyui"
    queued=adapter.queue_prompt({"1":{"class_type":"CheckpointLoaderSimple","inputs":{}}})
    assert queued["prompt_id"]=="test-prompt"
    assert adapter.history("test-prompt")["test-prompt"]["status"]["completed"]
    inventory=adapter.inventory()
    assert inventory["node_count"]==3 and "checkpoints" in inventory["models"]
    downloaded=adapter.download_output("test.png","",tmp_path/"download.png")
    assert downloaded["size_bytes"]==len(PNG_1X1)

def test_comfyui_refuses_remote_redirects_and_bounds_json_responses(comfy_server):
    adapter=ComfyUIAdapter(comfy_server)
    from elevenvt_studio.errors import AdapterUnavailable
    with pytest.raises(AdapterUnavailable): adapter._request("/redirect")
    with pytest.raises(AdapterUnavailable): adapter._request("/object_info",max_response_bytes=8)


def test_comfyui_refuses_remote_endpoint_without_remote_transport(comfy_server):
    adapter=ComfyUIAdapter("http://example.com:8188")
    assert adapter.is_loopback is False
    with pytest.raises(PermissionDenied): adapter.queue()

def test_process_adapter_uses_argv_and_workspace_cwd(tmp_path):
    result=ProcessAdapter(tmp_path).run(sys.executable,["-c","print('safe-process-check')"],cwd=tmp_path,timeout=10)
    assert result["success"] and "safe-process-check" in result["stdout"]

def test_process_adapter_refuses_external_working_directory(tmp_path):
    outside=tmp_path.parent
    with pytest.raises(Exception): ProcessAdapter(tmp_path).run(sys.executable,["--version"],cwd=outside,timeout=5)

def test_job_can_resume_after_exact_human_approval(service,comfy_server):
    from dataclasses import replace
    service.config=replace(service.config,comfyui_url=comfy_server)
    service.comfyui=ComfyUIAdapter(comfy_server)
    job=service.jobs.create({"name":"approved-comfy-job","tasks":[
      {"id":"queue","capability":"comfyui.queue_prompt","inputs":{"prompt":{"1":{"class_type":"Test","inputs":{}}}}}
    ]})
    first=service.jobs.run(job["id"])
    assert first["status"]=="BLOCKED"
    request=service.policy.request("comfyui.queue","NETWORK",comfy_server,"Generate approved local workflow")
    service.policy.decide(request["id"],True,"human-reviewer")
    second=service.jobs.run(job["id"],request["id"])
    assert second["status"]=="SUCCEEDED"
    assert second["tasks"][0]["outputs"]["prompt_id"]=="test-prompt"

def test_service_rejects_remote_comfyui_before_request(service):
    from dataclasses import replace
    from elevenvt_studio.adapters.comfyui import ComfyUIAdapter
    from elevenvt_studio.errors import PermissionDenied
    service.config=replace(service.config,comfyui_url="http://example.com:8188")
    service.comfyui=ComfyUIAdapter("http://example.com:8188")
    with pytest.raises(PermissionDenied): service.invoke("comfyui.queue_prompt",{"prompt":{"1":{"class_type":"Test","inputs":{}}}})


def test_comfyui_end_to_end_job_retrieves_and_manifests_output(service,comfy_server):
    from dataclasses import replace
    service.config=replace(service.config,comfyui_url=comfy_server)
    service.comfyui=ComfyUIAdapter(comfy_server)
    job=service.jobs.create({"name":"comfyui-production-chain","required_reviews":["technical","creative","rights"],"tasks":[
      {"id":"queue","capability":"comfyui.queue_prompt","inputs":{"prompt":{"1":{"class_type":"Test","inputs":{}}}}},
      {"id":"await","capability":"comfyui.await_completion","depends_on":["queue"],"inputs":{"prompt_id":{"$ref":"queue.prompt_id"},"timeout_seconds":5}},
      {"id":"retrieve","capability":"comfyui.retrieve_outputs","depends_on":["await"],"inputs":{"prompt_id":{"$ref":"queue.prompt_id"},"workflow_sha256":{"$ref":"queue.workflow_sha256"}}},
      {"id":"verify","capability":"artifact.verify","depends_on":["retrieve"],"inputs":{"artifact_id":{"$ref":"retrieve.artifact_id"}}}
    ]})
    first=service.jobs.run(job["id"])
    assert first["status"]=="BLOCKED"
    request=service.policy.request("comfyui.queue","NETWORK",comfy_server,"Approve the local generation workflow")
    service.policy.decide(request["id"],True,"test-reviewer")
    result=service.jobs.run(job["id"],request["id"])
    assert result["status"]=="SUCCEEDED"
    retrieve=result["tasks"][2]["outputs"]
    assert retrieve["retrieved_count"]==1
    assert retrieve["semantic_validation"]=="NOT_RUN"
    verify=result["tasks"][3]["outputs"]
    assert verify["status"]=="PASS"
    artifact=service.artifacts.list(job["id"])[0]
    assert artifact["provenance"]["creator"]=="comfyui"
    assert artifact["provenance"]["workflow_sha256"]
    assert artifact["provenance"]["license"]["status"]=="unknown"


def test_comfyui_output_download_rejects_traversal(comfy_server,tmp_path):
    adapter=ComfyUIAdapter(comfy_server)
    with pytest.raises(Exception): adapter.download_output("..\\outside.png","",tmp_path/"unsafe.png")
    with pytest.raises(Exception): adapter.download_output("test.png",r"..\\outside",tmp_path/"unsafe2.png")
