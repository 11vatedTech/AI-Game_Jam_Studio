import io, json
from elevenvt_studio.mcp.server import MCPServer

def test_mcp_initialize_and_tools_list(service):
    server=MCPServer(service)
    init=server.handle({"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-11-25"}})
    assert init["result"]["serverInfo"]["name"]=="11vatedtech-ai-game-jam-studio"
    listing=server.handle({"jsonrpc":"2.0","id":2,"method":"tools/list"})
    names={x["name"] for x in listing["result"]["tools"]}
    assert {"studio_status","job_create","job_run","artifact_verify"}.issubset(names)

def test_mcp_stdio_roundtrip(service):
    lines='\n'.join([json.dumps({"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}),json.dumps({"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"studio_status","arguments":{}}})])+'\n'
    reader=io.StringIO(lines); writer=io.StringIO(); MCPServer(service).serve(reader,writer)
    responses=[json.loads(x) for x in writer.getvalue().splitlines()]
    assert responses[0]["id"]==1 and responses[1]["result"]["isError"] is False
