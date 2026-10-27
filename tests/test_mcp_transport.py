"""Exercise the actual stdio transport against a local Python fixture server."""
import sys
import time
from concurrent.futures import ThreadPoolExecutor

from mcp_client import MCPClient, MCPServerConnection


SERVER = r'''
import json
import sys
import time

def send(value):
    print(json.dumps(value), flush=True)

for line in sys.stdin:
    message = json.loads(line)
    method = message.get("method")
    if not method:
        continue
    if method == "notifications/initialized":
        continue
    if method == "initialize":
        if sys.argv[1] == "silent":
            time.sleep(30)
        send({"jsonrpc": "2.0", "id": message["id"], "result": {
            "protocolVersion": "2024-11-05", "capabilities": {},
            "serverInfo": {"name": "fixture", "version": "1"}
        }})
    elif method == "tools/list":
        if sys.argv[1] == "bad_tools":
            send({"jsonrpc": "2.0", "id": message["id"], "error": {"code": -1, "message": "failed"}})
        else:
            send({"jsonrpc": "2.0", "id": message["id"], "result": {"tools": [{"name": "echo"}]}})
    elif method == "tools/call":
        value = message["params"]["arguments"]["value"]
        if value == "timeout":
            time.sleep(30)
        # Enough stderr to fill a pipe unless the client drains it.
        sys.stderr.write("diagnostic " * 20000)
        sys.stderr.flush()
        send({"jsonrpc": "2.0", "method": "notifications/message", "params": {"level": "info"}})
        send({"jsonrpc": "2.0", "id": -999, "result": "wrong response"})
        send({"jsonrpc": "2.0", "id": "server-ping", "method": "ping"})
        ping_reply = json.loads(sys.stdin.readline())
        if ping_reply.get("id") != "server-ping" or ping_reply.get("result") != {}:
            sys.exit(5)
        send({"jsonrpc": "2.0", "id": "server-request", "method": "sampling/createMessage"})
        unsupported_reply = json.loads(sys.stdin.readline())
        if unsupported_reply.get("error", {}).get("code") != -32601:
            sys.exit(6)
        send({"jsonrpc": "2.0", "id": message["id"], "result": {"content": [{"type": "text", "text": value}]}})
'''


def connection(mode="normal", timeout=3):
    return MCPServerConnection("fixture", {
        "command": [sys.executable, "-u", "-c", SERVER, mode],
        "request_timeout": timeout,
    })


def test_interleaved_notifications_requests_ids_and_stderr():
    conn = connection()
    try:
        assert conn.start()[0]
        ok, result = conn.call_tool("echo", {"value": "the answer"})
        assert ok, result
        assert result["content"][0]["text"] == "the answer"
        assert len(conn.notifications) == 1
        assert conn.is_connected
    finally:
        process = conn.process
        conn.stop()
    assert process.poll() is not None
    assert not conn.is_connected
    assert conn.tools == []


def test_concurrent_callers_receive_their_own_results():
    conn = connection()
    try:
        assert conn.start()[0]
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(lambda value: conn.call_tool("echo", {"value": str(value)}), range(4)))
        assert [result[1]["content"][0]["text"] for result in results] == ["0", "1", "2", "3"]
        assert all(result[0] for result in results)
    finally:
        conn.stop()


def test_initialize_timeout_terminates_server():
    conn = connection("silent", timeout=0.2)
    start = time.monotonic()
    ok, message = conn.start()
    assert not ok
    assert "timed out" in message
    assert time.monotonic() - start < 5
    assert conn.process is None


def test_tool_timeout_terminates_server_and_clears_connection():
    conn = connection(timeout=0.5)
    assert conn.start()[0]
    process = conn.process
    ok, message = conn.call_tool("echo", {"value": "timeout"})
    assert not ok
    assert "timed out" in message
    assert process.poll() is not None
    assert conn.process is None


def test_failed_discovery_does_not_report_connected():
    conn = connection("bad_tools")
    ok, message = conn.start()
    assert not ok
    assert "discovery failed" in message
    assert conn.process is None


def test_failed_reconnect_removes_stale_connection():
    client = MCPClient()
    try:
        config = {"name": "fixture", "command": [sys.executable, "-u", "-c", SERVER, "normal"]}
        assert client.connect_server(config)[0]
        assert not client.connect_server({"name": "fixture", "command": []})[0]
        assert "fixture" not in client.connections
    finally:
        client.disconnect_all()


def test_invalid_timeout_is_diagnostic():
    client = MCPClient()
    ok, message = client.connect_server({"name": "fixture", "request_timeout": -1})
    assert not ok
    assert "positive" in message


def test_get_all_tools_does_not_modify_server_metadata():
    client = MCPClient()
    conn = connection()
    conn._tools = [{"name": "echo"}]
    client.connections["fixture"] = conn
    assert client.get_all_tools() == [{"name": "echo", "_server": "fixture"}]
    assert "_server" not in conn.tools[0]


def test_context_update_replaces_all_tools_and_preserves_following_sections(tmp_path):
    context = tmp_path / ".opencode" / "context.md"
    context.parent.mkdir()
    context.write_text("# Project\n\n## MCP Tools Available\n### old_a\n---\n### old_b\n---\n\n## Decisions\nKeep this.\n", encoding="utf-8")
    client = MCPClient(tmp_path)
    conn = connection()
    conn._tools = [{"name": "new_a"}, {"name": "new_b"}]
    client.connections["fixture"] = conn
    client.update_context_md()
    first = context.read_text(encoding="utf-8")
    client.update_context_md()
    assert context.read_text(encoding="utf-8") == first
    assert "old_a" not in first and "old_b" not in first
    assert first.count("### new_a") == 1 and first.count("### new_b") == 1
    assert "## Decisions\nKeep this." in first
