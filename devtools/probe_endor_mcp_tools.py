#!/usr/bin/env python3
# ruff: noqa: T201, S603
r"""Introspect the running ``endorctl ai-tools mcp-server`` MCP tool surface.

What it does **not** do: it does not call ``tools/call`` or run a scan. It only performs
MCP **discovery** (``initialize`` + ``tools/list``), same as an IDE listing tools.

What it **does** do:

- Always fetches the **full** ``tools/list`` merge (all tools the server registers),
  with pagination handled.
- **Default stdout:** prints a human-readable focus on the ``scan`` tool
  (description + ``inputSchema`` + small heuristics) for quick reference.
- **``--dump-tools-json PATH``:** writes **everything** returned —
  ``initialize`` result, full merged ``tools/list``, and a ``tool_names`` array —
  as one JSON file.

Uses MCP newline-delimited JSON-RPC over stdin/stdout (Go MCP SDK / endorctl style).

**Windows:** subprocess pipes must be **binary** so LF is not rewritten to CRLF;
otherwise the server reports ``invalid trailing data at the end of stream``.

Negotiate ``protocolVersion`` **2025-06-18** (matches current endorctl MCP).

Usage:
  uv run python devtools/probe_endor_mcp_tools.py
  uv run python devtools/probe_endor_mcp_tools.py --dump-tools-json .tmp/mcp_tools.json
  set ENDORCTL=G:\\Tools\\endorctl\\endorctl.exe
  uv run python devtools/probe_endor_mcp_tools.py --endorctl "%ENDORCTL%"
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import threading
from collections.abc import Iterator
from typing import Any

MCP_PROTOCOL_VERSION = "2025-06-18"


def _drain_stderr(stream: Any) -> None:
    try:
        for _line in iter(stream.readline, b""):
            pass
    except OSError:
        pass


def _read_jsonrpc_objects(stream: Any) -> Iterator[dict[str, Any]]:
    """Yield JSON-RPC objects from newline-delimited binary stdout."""
    for raw in iter(stream.readline, b""):
        if not raw:
            break
        line = raw.strip()
        if not line.startswith(b"{"):
            continue
        try:
            obj = json.loads(line.decode("utf-8"))
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict) and obj.get("jsonrpc") == "2.0":
            yield obj


def _write_msg(proc: subprocess.Popen[bytes], payload: dict[str, Any]) -> None:
    line = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    if "\n" in line:
        msg = "JSON-RPC payload must not contain embedded newlines (MCP stdio)"
        raise ValueError(msg)
    assert proc.stdin is not None
    proc.stdin.write(line.encode("utf-8") + b"\n")
    proc.stdin.flush()


def _handshake(proc: subprocess.Popen[bytes]) -> dict[str, Any]:
    init_id = 1
    _write_msg(
        proc,
        {
            "jsonrpc": "2.0",
            "id": init_id,
            "method": "initialize",
            "params": {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {
                    "name": "probe_endor_mcp_tools",
                    "version": "1.0.0",
                },
            },
        },
    )
    init_result: dict[str, Any] | None = None
    for msg in _read_jsonrpc_objects(proc.stdout):
        if msg.get("id") == init_id:
            init_result = msg
            break
    if init_result is None:
        msg = "no initialize response from MCP server"
        raise RuntimeError(msg)
    if "error" in init_result:
        err = init_result["error"]
        msg = f"initialize error: {err!r}"
        raise RuntimeError(msg)

    _write_msg(
        proc,
        {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}},
    )
    return init_result


def _tools_list_all(proc: subprocess.Popen[bytes], start_id: int = 2) -> dict[str, Any]:
    """Return merged tools/list result (handles pagination)."""
    all_tools: list[Any] = []
    cursor: str | None = None
    req_id = start_id
    while True:
        params: dict[str, Any] = {}
        if cursor:
            params["cursor"] = cursor
        _write_msg(
            proc,
            {
                "jsonrpc": "2.0",
                "id": req_id,
                "method": "tools/list",
                "params": params,
            },
        )
        listed: dict[str, Any] | None = None
        for msg in _read_jsonrpc_objects(proc.stdout):
            if msg.get("id") == req_id:
                listed = msg
                break
        if listed is None:
            msg = "no tools/list response"
            raise RuntimeError(msg)
        if "error" in listed:
            return listed
        result = listed.get("result") or {}
        batch = result.get("tools") or []
        all_tools.extend(batch)
        cursor = result.get("nextCursor")
        if not cursor:
            return {
                "jsonrpc": "2.0",
                "id": start_id,
                "result": {"tools": all_tools},
            }
        req_id += 1


def _find_scan_tool(tools_result: dict[str, Any]) -> dict[str, Any] | None:
    result = tools_result.get("result") or {}
    tools = result.get("tools") or []
    for t in tools:
        if isinstance(t, dict) and t.get("name") == "scan":
            return t
    return None


def _summarize_path_support(schema: dict[str, Any]) -> list[str]:
    """Heuristic notes about whether partial paths / globs appear in the schema."""
    text = json.dumps(schema, ensure_ascii=False).lower()
    notes: list[str] = []
    patterns = [
        (r"\bpath\b", "mentions `path`"),
        (r"include", "mentions include"),
        (r"exclude", "mentions exclude"),
        (r"glob", "mentions glob"),
        (
            r"partial|subpath|subdirectory|subdir|relative",
            "mentions partial/subdir wording",
        ),
        (r"repository root|repo root|absolute", "mentions root/absoluteness"),
        (r"pr_incremental|incremental", "mentions incremental / pr_incremental"),
    ]
    for pat, label in patterns:
        if re.search(pat, text):
            notes.append(label)
    return notes


def _resolve_server_argv(
    endorctl: str | None,
    server_cmd: str,
    server_args: str,
    npx_style_args: str,
) -> list[str]:
    if endorctl:
        # Direct binary: subcommand args only (no `npx -y endorctl` prefix).
        return [endorctl, *server_args.split(",")]
    server_exe = server_cmd
    if (
        server_exe == "npx"
        and not os.path.isabs(server_exe)
        and os.sep not in server_exe
    ):
        resolved = shutil.which("npx")
        if resolved:
            server_exe = resolved
    return [server_exe, *npx_style_args.split(",")]


def main() -> int:
    """MCP handshake; optional full-tool JSON dump; print ``scan`` schema on stdout."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--endorctl",
        default=os.environ.get("ENDORCTL"),
        help=(
            "Path to endorctl executable "
            "(recommended on Windows; avoids npx stdin issues)."
        ),
    )
    parser.add_argument(
        "--server-cmd",
        default="npx",
        help="Command to launch the MCP server if --endorctl not set (default: npx)",
    )
    parser.add_argument(
        "--server-args",
        default="ai-tools,mcp-server,--log-level,error",
        help=(
            "Comma-separated args after endorctl binary "
            "(when using --endorctl / PATH endorctl)."
        ),
    )
    parser.add_argument(
        "--npx-args",
        default="-y,endorctl,ai-tools,mcp-server,--log-level,error",
        help="Comma-separated args after npx (when not using a direct endorctl path)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=120.0,
        help="Seconds to wait for subprocess (default: 120)",
    )
    parser.add_argument(
        "--dump-tools-json",
        metavar="PATH",
        help=(
            "Write full MCP payload (initialize result + all tools/list tools) "
            "to this file as UTF-8 JSON."
        ),
    )
    args = parser.parse_args()

    if not args.endorctl:
        w = shutil.which("endorctl")
        if w:
            args.endorctl = w

    server_argv = _resolve_server_argv(
        args.endorctl,
        args.server_cmd,
        args.server_args,
        args.npx_args,
    )

    proc = subprocess.Popen(
        server_argv,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=0,
    )
    assert proc.stdin is not None
    assert proc.stdout is not None
    assert proc.stderr is not None
    t_err = threading.Thread(target=_drain_stderr, args=(proc.stderr,), daemon=True)
    t_err.start()

    try:
        init = _handshake(proc)
        server_info = (init.get("result") or {}).get("serverInfo") or {}
        print(
            "MCP initialize ok:",
            f"name={server_info.get('name')!r}",
            f"version={server_info.get('version')!r}",
            f"protocol={MCP_PROTOCOL_VERSION!r}",
        )
        listed = _tools_list_all(proc)
        if "error" in listed:
            print("tools/list error:", listed["error"], file=sys.stderr)
            return 1

        if args.dump_tools_json:
            snapshot = {
                "mcp_protocol_version": MCP_PROTOCOL_VERSION,
                "server_argv": server_argv,
                "initialize": init,
                "tools_list": listed,
                "tool_names": [
                    t.get("name")
                    for t in (listed.get("result") or {}).get("tools") or []
                    if isinstance(t, dict)
                ],
            }
            out_path = os.path.abspath(args.dump_tools_json)
            parent = os.path.dirname(out_path)
            if parent:
                os.makedirs(parent, exist_ok=True)
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(snapshot, f, indent=2, ensure_ascii=False)
                f.write("\n")
            print()
            n_tools = len(snapshot["tool_names"])
            print(f"Wrote full MCP snapshot ({n_tools} tools) to: {out_path}")

        scan_tool = _find_scan_tool(listed)
        if scan_tool is None:
            print("No tool named 'scan' in tools/list.", file=sys.stderr)
            print(json.dumps(listed, indent=2)[:4000])
            return 2
        schema = scan_tool.get("inputSchema") or {}
        desc = scan_tool.get("description") or ""
        print()
        print("=== scan tool (MCP) ===")
        print("description:", desc[:2000] if desc else "(none)")
        print()
        print("inputSchema (JSON):")
        print(json.dumps(schema, indent=2))
        print()
        print("Heuristic keyword scan of schema JSON:")
        for line in _summarize_path_support(schema):
            print(" -", line)
    finally:
        proc.stdin.close()
        try:
            proc.wait(timeout=args.timeout)
        except subprocess.TimeoutExpired:
            proc.kill()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
