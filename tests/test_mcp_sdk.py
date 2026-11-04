"""Integration tests for the maintained MCP SDK path; skipped in core-only environments."""
import asyncio
import pytest

pytest.importorskip("mcp", reason="Install the optional official MCP SDK v2 with the [mcp] extra")

from mcp import Client
from elevenvt_studio.mcp.sdk_server import build_server


def test_official_mcp_sdk_v2_discovery_and_tool_calls(service):
    server = build_server(service)

    async def exercise():
        async with Client(server) as client:
            assert client.protocol_version == "2026-07-28"
            tools = await client.list_tools()
            names = {tool.name for tool in tools.tools}
            assert {"studio_status", "capabilities_list", "capability_invoke", "job_create", "job_run"}.issubset(names)
            result = await client.call_tool("studio_status", {})
            assert not result.is_error
            assert result.structured_content["product"] == "11vatedTech AI Game Jam Studio"

    asyncio.run(exercise())
