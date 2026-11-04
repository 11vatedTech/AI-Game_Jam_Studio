from __future__ import annotations
import os
from .server import MCPServer
from ..errors import AdapterUnavailable


def serve(service):
    """Use maintained MCP SDK v2; legacy framing requires an explicit opt-in."""
    try:
        from .sdk_server import build_server
        server = build_server(service)
    except RuntimeError as exc:
        if os.environ.get("STUDIO_ALLOW_LEGACY_MCP") != "1":
            raise AdapterUnavailable(
                "The official MCP SDK is required for the production bridge. "
                "Install with `pip install -e '.[mcp]'`. Set STUDIO_ALLOW_LEGACY_MCP=1 "
                "only for isolated legacy-client development tests."
            ) from exc
        import sys
        print(f"WARNING: explicitly enabled legacy MCP fallback: {exc}", file=sys.stderr)
        MCPServer(service).serve()
        return
    server.run()


__all__ = ["MCPServer", "serve"]
