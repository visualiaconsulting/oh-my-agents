"""
mcp_client.py — Model Context Protocol client for oh-my-agents

Implements JSON-RPC 2.0 over stdio to connect with MCP servers.
Supports tool listing, calling, and context injection.
"""
import os
import json
import subprocess
import threading
import math
import queue
import time
from collections import deque
from pathlib import Path
from typing import Optional, Dict, List, Any, Tuple

from utils import get_opencode_dir


class MCPServerConnection:
    """Bounded stdio JSON-RPC transport with one owner per request.

    The request_timeout option is a positive duration in seconds (default 10).
    Timeouts close the connection. Notifications and stderr use bounded buffers.
    """

    def __init__(self, name: str, config: dict):
        self.name = name
        self.config = config
        timeout = float(config.get("request_timeout", 10))
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("request_timeout must be a finite positive number")
        self.request_timeout = timeout
        self.process: Optional[subprocess.Popen] = None
        self._request_id = 0
        self._lock = threading.Lock()
        self._write_lock = threading.Lock()
        self._responses = queue.Queue()
        self._readers = []
        self.notifications = deque(maxlen=100)
        self.stderr_tail = deque(maxlen=20)
        self._tools: List[dict] = []
        self._initialized = False

    def start(self) -> Tuple[bool, str]:
        """Start the server, initialize it, then discover its tools."""
        if self.process is not None:
            self.stop()
        command = self.config.get("command", [])
        if not isinstance(command, list) or not command or not all(
            isinstance(part, str) and part for part in command
        ):
            return False, "Command must be a non-empty list of strings"

        env = os.environ.copy()
        if "env" in self.config:
            env.update(self.config["env"])
        self._responses = queue.Queue()
        self.notifications.clear()
        self.stderr_tail.clear()

        try:
            self.process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                env=env,
            )
        except (OSError, ValueError) as exc:
            return False, f"Failed to start server: {exc}"

        process = self.process
        self._readers = [
            threading.Thread(target=self._read_stdout, args=(process,), daemon=True),
            threading.Thread(target=self._drain_stderr, args=(process,), daemon=True),
        ]
        for reader in self._readers:
            reader.start()

        ok, message = self._initialize()
        if not ok:
            self.stop()
            return False, message
        ok, tools = self._list_tools()
        if not ok:
            self.stop()
            return False, "Tool discovery failed"
        self._tools = tools
        return True, f"Connected with {len(self._tools)} tool(s)"

    def _write_message(self, message: dict) -> None:
        with self._write_lock:
            process = self.process
            if process is None or process.poll() is not None:
                raise OSError("Server is not running")
            process.stdin.write(json.dumps(message) + "\n")
            process.stdin.flush()

    def _read_stdout(self, process) -> None:
        try:
            for line in process.stdout:
                try:
                    message = json.loads(line)
                except (ValueError, TypeError):
                    self._responses.put({"_transport_error": "Invalid JSON from server"})
                    continue
                if not isinstance(message, dict) or message.get("jsonrpc") != "2.0":
                    self._responses.put({"_transport_error": "Invalid JSON-RPC message"})
                    continue
                if "method" in message:
                    if "id" in message:
                        reply = {"jsonrpc": "2.0", "id": message["id"]}
                        if message["method"] == "ping":
                            reply["result"] = {}
                        else:
                            reply["error"] = {
                                "code": -32601,
                                "message": "Client method not supported",
                            }
                        try:
                            self._write_message(reply)
                        except (OSError, ValueError):
                            pass
                    else:
                        self.notifications.append(message)
                    continue
                if "id" in message:
                    self._responses.put(message)
        except (OSError, ValueError) as exc:
            self._responses.put({"_transport_error": str(exc)})
        finally:
            self._responses.put({"_transport_error": "Server closed stdout"})

    def _drain_stderr(self, process) -> None:
        try:
            while True:
                chunk = process.stderr.read(4096)
                if not chunk:
                    return
                self.stderr_tail.append(chunk[-4096:])
        except (OSError, ValueError):
            return

    def stop(self):
        process = self.process
        self._initialized = False
        self._tools = []
        if process is None:
            return
        try:
            process.terminate()
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=2)
        except OSError:
            pass
        finally:
            self.process = None
            self._responses.put({"_transport_error": "Connection stopped"})
            for stream in (process.stdin, process.stdout, process.stderr):
                try:
                    stream.close()
                except (OSError, ValueError):
                    pass
            for reader in self._readers:
                if reader is not threading.current_thread():
                    reader.join(timeout=1)
            self._readers = []

    def _send_request(self, method: str, params: Optional[dict] = None) -> Tuple[bool, Any]:
        # Own the entire transaction: concurrent callers cannot steal replies.
        with self._lock:
            self._request_id += 1
            req_id = self._request_id
            request = {"jsonrpc": "2.0", "id": req_id, "method": method}
            if params is not None:
                request["params"] = params
            try:
                self._write_message(request)
                deadline = time.monotonic() + self.request_timeout
                while True:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise queue.Empty
                    response = self._responses.get(timeout=remaining)
                    if "_transport_error" in response:
                        return False, response["_transport_error"]
                    if response.get("id") != req_id:
                        continue
                    if "error" in response:
                        return False, response["error"]
                    if "result" not in response:
                        return False, "Response has no result or error"
                    return True, response["result"]
            except queue.Empty:
                self.stop()
                return False, f"Request '{method}' timed out after {self.request_timeout:g}s"
            except (OSError, ValueError) as exc:
                return False, str(exc)

    def _initialize(self) -> Tuple[bool, str]:
        from update_manager import get_current_version

        ok, result = self._send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "oh-my-agents", "version": get_current_version()},
        })
        if not ok:
            return False, f"Initialize failed: {result}"
        if not isinstance(result, dict):
            return False, "Initialize returned an invalid result"
        try:
            self._write_message({"jsonrpc": "2.0", "method": "notifications/initialized"})
        except (OSError, ValueError) as exc:
            return False, f"Initialize notification failed: {exc}"
        self._initialized = True
        return True, "Initialized"

    def _list_tools(self) -> Tuple[bool, List[dict]]:
        ok, result = self._send_request("tools/list")
        if not ok or not isinstance(result, dict) or not isinstance(result.get("tools"), list):
            return False, []
        return True, result["tools"]

    def call_tool(self, tool_name: str, arguments: dict) -> Tuple[bool, Any]:
        if not self._initialized:
            return False, "Server not initialized"
        return self._send_request("tools/call", {
            "name": tool_name,
            "arguments": arguments,
        })

    @property
    def tools(self) -> List[dict]:
        return self._tools

    @property
    def is_connected(self) -> bool:
        return self.process is not None and self.process.poll() is None and self._initialized


class MCPClient:
    """Manages multiple MCP server connections and generates context."""

    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or Path.cwd()
        self.connections: Dict[str, MCPServerConnection] = {}

    def connect_server(self, config: dict) -> Tuple[bool, str]:
        name = config.get("name")
        if not name:
            return False, "Server config missing 'name'"

        # Disconnect existing
        if name in self.connections:
            self.disconnect_server(name)

        try:
            conn = MCPServerConnection(name, config)
        except (TypeError, ValueError) as exc:
            return False, str(exc)
        ok, msg = conn.start()
        if ok:
            self.connections[name] = conn
        return ok, msg

    def disconnect_server(self, name: str):
        if name in self.connections:
            self.connections[name].stop()
            del self.connections[name]

    def disconnect_all(self):
        for conn in self.connections.values():
            conn.stop()
        self.connections.clear()

    def get_all_tools(self) -> List[dict]:
        tools = []
        for conn in self.connections.values():
            for tool in conn.tools:
                tools.append({**tool, "_server": conn.name})
        return tools

    def call_tool(self, server_name: str, tool_name: str, arguments: dict) -> Tuple[bool, Any]:
        if server_name not in self.connections:
            return False, f"Server '{server_name}' not connected"
        return self.connections[server_name].call_tool(tool_name, arguments)

    def inject_mcp_context(self) -> str:
        """Generate markdown context describing available MCP tools."""
        tools = self.get_all_tools()
        if not tools:
            return ""

        lines = ["## MCP Tools Available", ""]
        for tool in tools:
            name = tool.get("name", "unknown")
            desc = tool.get("description", "")
            server = tool.get("_server", "unknown")
            lines.append(f"### {name} (via {server})")
            lines.append("")
            if desc:
                lines.append(f"{desc}")
                lines.append("")
            schema = tool.get("inputSchema", {})
            if schema and isinstance(schema, dict):
                props = schema.get("properties", {})
                if props:
                    lines.append("**Parameters:**")
                    for prop_name, prop_info in props.items():
                        ptype = prop_info.get("type", "any")
                        pdesc = prop_info.get("description", "")
                        req = " (required)" if prop_name in schema.get("required", []) else ""
                        lines.append(f"- `{prop_name}` ({ptype}){req}: {pdesc}")
                    lines.append("")
            lines.append("---")
            lines.append("")

        return "\n".join(lines)

    def update_context_md(self):
        """Replace the complete generated tool section without duplicating tools."""
        import re

        context_file = get_opencode_dir(self.project_root) / "context.md"
        if not context_file.exists():
            return
        try:
            content = context_file.read_text(encoding="utf-8")
        except OSError:
            return
        mcp_context = self.inject_mcp_context()
        if not mcp_context:
            return

        start_marker = "<!-- oh-my-agents:mcp:start -->"
        end_marker = "<!-- oh-my-agents:mcp:end -->"
        block = f"{start_marker}\n{mcp_context.rstrip()}\n{end_marker}"
        if start_marker in content and end_marker in content:
            pattern = re.escape(start_marker) + r".*?" + re.escape(end_marker)
            content = re.sub(pattern, lambda _: block, content, count=1, flags=re.DOTALL)
        elif "## MCP Tools Available" in content:
            # Migrate the old unbounded section, retaining following sections.
            content = re.sub(
                r"^## MCP Tools Available\b.*?(?=^## |\Z)",
                lambda _: block + "\n\n",
                content, count=1, flags=re.DOTALL | re.MULTILINE,
            )
        else:
            content = content.rstrip() + "\n\n" + block + "\n"
        try:
            context_file.write_text(content, encoding="utf-8")
        except OSError:
            pass
