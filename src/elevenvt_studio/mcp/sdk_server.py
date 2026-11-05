"""Official MCP Python SDK v2 transport used by installed production setups.

The dependency is optional for the repository's zero-dependency core, but the
Windows/Linux bootstrap installs the `mcp` extra. This delegates protocol
versioning, stdio framing, schema validation and tool-result encoding to the
maintained upstream SDK instead of reimplementing MCP on the production path.
"""
from __future__ import annotations

from typing import Any, Literal

from ..errors import StudioError
from ..perception.tools import PerceptionTools, to_call_tool_result


def build_server(service: Any):
    """Build an official MCP SDK v2 server around the local StudioService."""
    try:
        from mcp.server import MCPServer
        from mcp.server.mcpserver.exceptions import ToolError
    except ImportError as exc:  # pragma: no cover - depends on optional install
        raise RuntimeError("Install the official MCP SDK with `pip install -e '.[mcp]'`.") from exc

    server = MCPServer(
        "11vatedTech AI Game Jam Studio",
        version="0.2.0",
        instructions=(
            "You are connected to the local 11vatedTech Studio runtime. Start with capabilities_list and "
            "studio_status. Use durable jobs for multi-step work. The runtime is not the reasoning agent: "
            "Freebuff owns intent understanding, research, design and creative judgment. Every write, "
            "execute, network, publish or destructive action is governed by local policy. An approval_request "
            "does not approve an action; a human must grant approval through the local CLI. A queued ComfyUI "
            "prompt is not a completed artifact. Verify files, provenance, rights and domain quality separately."
        ),
        log_level="WARNING",
    )

    def tool_call(fn, *args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except StudioError as exc:
            detail = f"{exc.code}: {exc}"
            if exc.details:
                detail += f"; details={exc.details}"
            raise ToolError(detail) from exc
        except (ValueError, KeyError, OSError) as exc:
            raise ToolError(f"{type(exc).__name__}: {exc}") from exc

    @server.tool()
    def studio_status() -> dict[str, Any]:
        """Read local runtime identity, workspace paths and implementation counts."""
        return tool_call(service.status)

    @server.tool()
    def capabilities_list(domain: str | None = None) -> list[dict[str, Any]]:
        """List registered runtime capabilities, their maturity and evidence requirements."""
        return tool_call(service.registry.list, domain)

    @server.tool()
    def capability_invoke(capability_id: str, inputs: dict[str, Any] | None = None) -> dict[str, Any]:
        """Invoke one registered capability; the runtime enforces scope and side-effect policy."""
        return tool_call(service.invoke, capability_id, inputs or {})

    @server.tool()
    def resource_profile() -> dict[str, Any]:
        """Inspect the local CPU, memory, storage, GPU and VRAM profile."""
        return tool_call(service.handlers["resource.profile"], {})

    @server.tool()
    def job_create(job_spec: dict[str, Any]) -> dict[str, Any]:
        """Persist a dependency-ordered production job from a JSON task graph."""
        return tool_call(service.jobs.create, job_spec)

    @server.tool()
    def job_run(job_id: str, approval_id: str | None = None) -> dict[str, Any]:
        """Run or resume a job until success, failure, an approval block or reconciliation is required."""
        return tool_call(service.jobs.run, job_id, approval_id)

    @server.tool()
    def job_status(job_id: str) -> dict[str, Any]:
        """Read durable job/task states, outputs, attempts and failure details."""
        return tool_call(service.jobs.status, job_id)

    @server.tool()
    def job_list(status: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        """List recent jobs, optionally filtered by status."""
        return tool_call(service.jobs.list, status, limit)

    @server.tool()
    def workspace_read_text(path: str, max_bytes: int = 1000000) -> dict[str, Any]:
        """Read a bounded UTF-8 file confined to the managed workspace."""
        return tool_call(service.invoke, "workspace.read_text", {"path": path, "max_bytes": max_bytes})

    @server.tool()
    def workspace_write_text(path: str, content: str) -> dict[str, Any]:
        """Create a new UTF-8 workspace file; this operation refuses to overwrite existing files."""
        return tool_call(service.invoke, "workspace.write_text", {"path": path, "content": content})

    @server.tool()
    def artifacts_list(job_id: str | None = None) -> list[dict[str, Any]]:
        """List registered artifacts with hashes, provenance, rights and validation states."""
        return tool_call(service.artifacts.list, job_id)

    @server.tool()
    def artifact_verify(artifact_id: str) -> dict[str, Any]:
        """Recompute the artifact SHA-256 and report missing or modified files."""
        return tool_call(service.artifacts.verify, artifact_id)

    @server.tool()
    def quality_report(job_id: str) -> dict[str, Any]:
        """Run deterministic quality gates; subjective review and certification remain separate."""
        return tool_call(service.quality_report, job_id)

    @server.tool()
    def approval_request(scope: str, side_effect: Literal["READ", "CREATE", "MODIFY", "DELETE", "EXECUTE", "NETWORK", "CREDENTIAL", "PUBLISH"], target: str, reason: str) -> dict[str, Any]:
        """Request human approval for an exact scope, side-effect class and target; does not grant it."""
        return tool_call(service.policy.request, scope, side_effect, target, reason)

    @server.tool()
    def approvals_list(status: str | None = None) -> list[dict[str, Any]]:
        """Read approval request states; only a human CLI action can approve or reject them."""
        return tool_call(service.policy.list, status)

    # Perception tools return an explicit CallToolResult: text plus image content
    # blocks and no structuredContent. Returning a plain dict here would publish
    # identical-looking JSON that a host SDK may prefer over the images.
    perception = PerceptionTools(service)

    @server.tool(structured_output=False)
    def perception_capture(mode: str, plan: dict[str, Any] | None = None, roles: list[str] | None = None) -> Any:
        """Capture the running application and return the images as real image content."""
        return tool_call(lambda: to_call_tool_result(perception.capture({"mode": mode, "plan": plan, "roles": roles})))

    @server.tool(structured_output=False)
    def perception_get(capture_id: str, role: str) -> Any:
        """Return one artifact from an existing capture as an image block."""
        return tool_call(lambda: to_call_tool_result(perception.get({"capture_id": capture_id, "role": role})))

    @server.tool(structured_output=False)
    def perception_crop(capture_id: str, role: str, region: list[int], output_size: list[int] | None = None) -> Any:
        """Return a derivative crop for detail inspection; the original stays authoritative."""
        return tool_call(lambda: to_call_tool_result(perception.crop({"capture_id": capture_id, "role": role, "region": region, "output_size": output_size})))

    @server.tool(structured_output=False)
    def perception_probe(agent_instance: str | None = None) -> Any:
        """Issue a vision challenge whose code appears only inside the returned image."""
        return tool_call(lambda: to_call_tool_result(perception.probe({"agent_instance": agent_instance})))

    @server.tool(structured_output=False)
    def perception_probe_verify(challenge_id: str, answer: str) -> Any:
        """Answer a perception challenge; single use, expires after 180 seconds."""
        return tool_call(lambda: to_call_tool_result(perception.probe_verify({"challenge_id": challenge_id, "answer": answer})))

    @server.resource("studio://runtime/status")
    def runtime_status_resource() -> str:
        """Current runtime status as JSON."""
        import json
        return json.dumps(service.status(), sort_keys=True)

    return server


def serve_official(service: Any) -> None:
    """Start the official MCP SDK v2 server over stdio."""
    server = build_server(service)
    server.run()
