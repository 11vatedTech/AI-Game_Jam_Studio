import pytest

from elevenvt_studio.errors import AdapterUnavailable
import elevenvt_studio.mcp as mcp_package
import elevenvt_studio.mcp.sdk_server as sdk_server


def test_production_mcp_fails_closed_without_official_sdk(service, monkeypatch):
    monkeypatch.delenv("STUDIO_ALLOW_LEGACY_MCP", raising=False)

    def missing_sdk(_service):
        raise RuntimeError("SDK missing in controlled test")

    monkeypatch.setattr(sdk_server, "build_server", missing_sdk)
    with pytest.raises(AdapterUnavailable, match="official MCP SDK is required"):
        mcp_package.serve(service)


def test_legacy_mcp_requires_explicit_development_opt_in(service, monkeypatch):
    calls = []

    class LegacyStub:
        def __init__(self, _service): pass
        def serve(self): calls.append("served")

    def missing_sdk(_service):
        raise RuntimeError("SDK missing in controlled test")

    monkeypatch.setattr(sdk_server, "build_server", missing_sdk)
    monkeypatch.setattr(mcp_package, "MCPServer", LegacyStub)
    monkeypatch.setenv("STUDIO_ALLOW_LEGACY_MCP", "1")
    mcp_package.serve(service)
    assert calls == ["served"]
