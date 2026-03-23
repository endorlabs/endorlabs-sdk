"""Dependency tree and call graph explorer for Endor Labs projects.

Fetches PackageVersion BOMs, DependencyMetadata, and call graph data from
the Endor Labs API and produces human-readable Markdown summaries alongside
raw JSON artifacts.

This module consolidates logic previously split across
``.tmp/prove_dependency_tree_and_call_graph.py`` and
``.tmp/explore/analyze_callgraph.py``.

Experimental: API may change without the same stability guarantees as the
rest of the SDK.
"""

from __future__ import annotations

import base64
import json
import os
import re
import textwrap
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import UTC, datetime
from io import StringIO
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from endorlabs import Client
    from endorlabs.api_client import APIClient

from endorlabs.utils.logging_config import get_resource_logger

logger = get_resource_logger(__name__)

# ---------------------------------------------------------------------------
# Optional: zstandard for call graph decoding
# ---------------------------------------------------------------------------
try:
    import zstandard  # type: ignore[import-untyped]
except ImportError:
    zstandard = None  # type: ignore[assignment]

_HAS_ZSTD = zstandard is not None

# ===================================================================
#  Section 1 — Protobuf wire-format decoder (no compiled proto dep)
# ===================================================================

WIRETYPE_VARINT = 0
WIRETYPE_64BIT = 1
WIRETYPE_LENGTH_DELIMITED = 2
WIRETYPE_32BIT = 5


def _decode_varint(data: bytes, pos: int) -> tuple[int, int]:
    """Decode a protobuf varint starting at *pos*. Returns ``(value, new_pos)``."""
    result = 0
    shift = 0
    while True:
        b = data[pos]
        result |= (b & 0x7F) << shift
        pos += 1
        if (b & 0x80) == 0:
            return result, pos
        shift += 7


def _decode_raw_fields(data: bytes) -> list[tuple[int, int, Any]]:
    """Return ``(field_number, wire_type, value)`` tuples from raw protobuf."""
    fields: list[tuple[int, int, Any]] = []
    pos = 0
    while pos < len(data):
        try:
            tag, pos = _decode_varint(data, pos)
        except (IndexError, ValueError):
            break
        field_number = tag >> 3
        wire_type = tag & 0x7
        if wire_type == WIRETYPE_VARINT:
            value, pos = _decode_varint(data, pos)
            fields.append((field_number, wire_type, value))
        elif wire_type == WIRETYPE_LENGTH_DELIMITED:
            length, pos = _decode_varint(data, pos)
            fields.append((field_number, wire_type, data[pos : pos + length]))
            pos += length
        elif wire_type == WIRETYPE_32BIT:
            fields.append((field_number, wire_type, data[pos : pos + 4]))
            pos += 4
        elif wire_type == WIRETYPE_64BIT:
            fields.append((field_number, wire_type, data[pos : pos + 8]))
            pos += 8
        else:
            break
    return fields


def _get_fields(data: bytes, field_num: int) -> list[Any]:
    """Extract all values for a given field number from raw protobuf bytes."""
    return [v for fn, _, v in _decode_raw_fields(data) if fn == field_num]


def _get_field(data: bytes, field_num: int, default: Any = None) -> Any:
    """Extract the first value for a given field number, or *default*."""
    vals = _get_fields(data, field_num)
    return vals[0] if vals else default


def _unwrap_string(data: bytes) -> str:
    """Decode a protobuf StringValue wrapper (field 1 = string)."""
    inner = _get_field(data, 1)
    if inner is None:
        return ""
    if isinstance(inner, bytes):
        return inner.decode("utf-8", errors="replace")
    return str(inner)


def _unwrap_int(data: bytes) -> int | None:
    """Decode a protobuf Int32Value/Int64Value wrapper (field 1 = varint)."""
    return _get_field(data, 1)


def _unwrap_bool(data: bytes) -> bool | None:
    """Decode a protobuf BoolValue wrapper (field 1 = varint 0/1)."""
    v = _get_field(data, 1)
    return bool(v) if v is not None else None


# ===================================================================
#  Section 2 — Callgraph enums and data classes
# ===================================================================

LANGUAGE_OR_RUNTIME = {
    0: "UNSPECIFIED",
    1: "JVM",
    2: "RUST",
    3: "PYTHON",
    4: "GO",
    5: "JAVASCRIPT",
    6: "DOTNET",
    7: "KOTLIN",
    8: "RUBY",
}

# Fallback: infer language from package ecosystem prefix when the protobuf
# language field is unset (platform sometimes omits it).
_ECOSYSTEM_LANGUAGE: dict[str, str] = {
    "pypi://": "PYTHON",
    "npm://": "JAVASCRIPT",
    "go://": "GO",
    "maven://": "JVM",
    "crates://": "RUST",
    "nuget://": "DOTNET",
    "rubygems://": "RUBY",
}

CALLGRAPH_VERSION = {
    0: "UNSPECIFIED",
    1: "V1",
    2: "V2",
    3: "V3",
    4: "V4",
    5: "V5",
    6: "V6",
    7: "V7",
}

ACCESS_LEVEL = {
    0: "UNSPECIFIED",
    1: "PUBLIC",
    2: "PRIVATE",
    3: "PROTECTED",
    4: "PACKAGE_PRIVATE",
    5: "INTERNAL",
    6: "LOCAL",
}

CLASS_TYPE = {
    0: "UNSPECIFIED",
    1: "ABSTRACT",
    2: "INTERFACE",
    3: "SYNTHETIC",
    4: "REGULAR",
}

CALL_TYPE = {
    0: "UNSPECIFIED",
    1: "DYNAMIC",
    2: "INTERFACE",
    3: "SPECIAL",
    4: "STATIC",
    5: "VIRTUAL",
    6: "INSTANCE",
    7: "INSTANCE_FIELD_READ",
    8: "INSTANCE_FIELD_WRITE",
    9: "STATIC_FIELD_READ",
    10: "STATIC_FIELD_WRITE",
    11: "UNRESOLVED_FIELD_READ",
    12: "UNRESOLVED_FIELD_WRITE",
}


@dataclass
class CallableInfo:
    """A decoded Callable (function/method)."""

    method_id: int
    uri: str
    access: str
    first_line: int | None
    last_line: int | None
    defined: bool | None


@dataclass
class TypeInfo:
    """A decoded Type (module/class)."""

    key: str
    access: str
    class_type: str
    source_file: str
    methods: list[CallableInfo] = field(default_factory=list)


@dataclass
class CallSiteInfo:
    """A decoded CallSite within a Call edge."""

    site_key: int
    receiver: list[str]
    line: int | None
    call_type: str


@dataclass
class CallEdge:
    """A decoded Call (source -> target edge)."""

    source_id: int
    target_id: int
    callsites: list[CallSiteInfo] = field(default_factory=list)


@dataclass
class CallGraphInfo:
    """Fully decoded CallGraph message."""

    uuid: str
    namespace: str
    parent_uuid: str
    create_time_iso: str
    update_time_iso: str
    package_name: str
    proto_create_time: datetime | None
    language: str
    version: str
    internal_types: list[TypeInfo] = field(default_factory=list)
    external_types: list[TypeInfo] = field(default_factory=list)
    call_edges: list[CallEdge] = field(default_factory=list)
    _callable_index: dict[int, CallableInfo] = field(
        default_factory=dict,
        repr=False,
    )
    _callable_type: dict[int, TypeInfo] = field(default_factory=dict, repr=False)

    def build_index(self) -> None:
        """Populate the callable index from types."""
        for t in self.internal_types + self.external_types:
            for m in t.methods:
                self._callable_index[m.method_id] = m
                self._callable_type[m.method_id] = t

    def callable_label(self, method_id: int) -> str:
        """Human label for a method id."""
        c = self._callable_index.get(method_id)
        if c is None:
            return f"<unknown id={method_id}>"
        uri = c.uri
        for prefix in ("javascript://", "java://", "python://", "go://", "rust://"):
            if uri.startswith(prefix):
                uri = uri[len(prefix) :]
                break
        return uri

    def callable_short(self, method_id: int) -> str:
        """Short function name from the URI."""
        label = self.callable_label(method_id)
        if "]/" in label:
            return label.rsplit("]/", 1)[-1] or "(module scope)"
        return label


# ===================================================================
#  Section 3 — Protobuf decoding logic
# ===================================================================


def _decode_proto_map_entry(entry_bytes: bytes) -> tuple[Any, bytes]:
    """Decode a protobuf map entry: field 1 = key, field 2 = value bytes."""
    fields = _decode_raw_fields(entry_bytes)
    key = None
    value = b""
    for fn, _wt, v in fields:
        if fn == 1:
            key = v.decode("utf-8", errors="replace") if isinstance(v, bytes) else v
        elif fn == 2:
            value = v if isinstance(v, bytes) else b""
    return key, value


def _decode_callable(method_id: int, callable_bytes: bytes) -> CallableInfo:
    """Decode a Callable message."""
    uri_raw = _get_field(callable_bytes, 1)
    uri = _unwrap_string(uri_raw) if isinstance(uri_raw, bytes) else str(uri_raw or "")
    metadata_raw = _get_field(callable_bytes, 2)
    access = "UNSPECIFIED"
    first_line = None
    last_line = None
    defined = None
    if isinstance(metadata_raw, bytes):
        access_val = _get_field(metadata_raw, 1, 0)
        access = ACCESS_LEVEL.get(access_val, f"UNKNOWN({access_val})")
        first_raw = _get_field(metadata_raw, 2)
        if isinstance(first_raw, bytes):
            first_line = _unwrap_int(first_raw)
        last_raw = _get_field(metadata_raw, 3)
        if isinstance(last_raw, bytes):
            last_line = _unwrap_int(last_raw)
        defined_raw = _get_field(metadata_raw, 4)
        if isinstance(defined_raw, bytes):
            defined = _unwrap_bool(defined_raw)
    return CallableInfo(
        method_id=method_id,
        uri=uri,
        access=access,
        first_line=first_line,
        last_line=last_line,
        defined=defined,
    )


def _decode_type(key: str, type_bytes: bytes) -> TypeInfo:
    """Decode a Type message from CHA."""
    access_val = _get_field(type_bytes, 1, 0)
    access = ACCESS_LEVEL.get(access_val, f"UNKNOWN({access_val})")
    source_file_raw = _get_field(type_bytes, 7)
    source_file = (
        _unwrap_string(source_file_raw) if isinstance(source_file_raw, bytes) else ""
    )
    if source_file and not source_file[0].isalnum() and "/" in source_file:
        source_file = source_file[source_file.index("/") :]
    class_type_val = _get_field(type_bytes, 8, 0)
    class_type = CLASS_TYPE.get(class_type_val, f"UNKNOWN({class_type_val})")
    methods: list[CallableInfo] = []
    for method_entry_bytes in _get_fields(type_bytes, 2):
        if not isinstance(method_entry_bytes, bytes):
            continue
        method_id_raw, callable_bytes = _decode_proto_map_entry(method_entry_bytes)
        if method_id_raw is not None and isinstance(callable_bytes, bytes):
            methods.append(_decode_callable(int(method_id_raw), callable_bytes))
    return TypeInfo(
        key=key,
        access=access,
        class_type=class_type,
        source_file=source_file,
        methods=methods,
    )


def _decode_callsite(site_key: int, site_bytes: bytes) -> CallSiteInfo:
    """Decode a CallSite message."""
    receivers = [
        _unwrap_string(r) for r in _get_fields(site_bytes, 1) if isinstance(r, bytes)
    ]
    line_raw = _get_field(site_bytes, 2)
    line: int | None = None
    if isinstance(line_raw, bytes):
        v = _unwrap_int(line_raw)
        if v is not None and v < 2**63:
            line = v
    call_type_val = _get_field(site_bytes, 3, 0)
    call_type = CALL_TYPE.get(call_type_val, f"UNKNOWN({call_type_val})")
    return CallSiteInfo(
        site_key=site_key,
        receiver=receivers,
        line=line,
        call_type=call_type,
    )


def _decode_call(call_bytes: bytes) -> CallEdge:
    """Decode a Call message (call_sites entry)."""
    source_raw = _get_field(call_bytes, 1)
    source_id = _unwrap_int(source_raw) if isinstance(source_raw, bytes) else source_raw
    target_raw = _get_field(call_bytes, 2)
    target_id = _unwrap_int(target_raw) if isinstance(target_raw, bytes) else target_raw
    sites: list[CallSiteInfo] = []
    for entry_bytes in _get_fields(call_bytes, 3):
        if not isinstance(entry_bytes, bytes):
            continue
        site_key_raw, site_body = _decode_proto_map_entry(entry_bytes)
        if site_key_raw is not None and isinstance(site_body, bytes):
            sites.append(_decode_callsite(int(site_key_raw), site_body))
    return CallEdge(source_id=source_id or 0, target_id=target_id or 0, callsites=sites)


def _decode_timestamp(ts_bytes: bytes) -> datetime | None:
    """Decode a ``google.protobuf.Timestamp``."""
    seconds = _get_field(ts_bytes, 1, 0)
    nanos = _get_field(ts_bytes, 2, 0)
    if not seconds:
        return None
    return datetime.fromtimestamp(seconds + nanos / 1e9, tz=UTC)


def decode_callgraph(envelope: dict[str, Any]) -> CallGraphInfo:
    """Decode a CallGraphData JSON envelope into a :class:`CallGraphInfo`.

    Args:
        envelope: Raw JSON dict containing ``zstd_bytes`` (base64-encoded,
            zstd-compressed protobuf).

    Returns:
        Fully decoded call graph with types, methods, and edges.

    Raises:
        ImportError: If ``zstandard`` is not installed.
        KeyError: If ``zstd_bytes`` is missing from the envelope.
    """
    if not _HAS_ZSTD:
        raise ImportError(
            "zstandard is required for call graph decoding. "
            "Install with: pip install zstandard"
        )

    assert zstandard is not None  # guarded by _HAS_ZSTD check above
    compressed = base64.b64decode(envelope["zstd_bytes"])
    raw = zstandard.ZstdDecompressor().decompress(compressed)

    pkg_raw = _get_field(raw, 1)
    package_name = _unwrap_string(pkg_raw) if isinstance(pkg_raw, bytes) else ""
    ts_raw = _get_field(raw, 2)
    proto_ts = _decode_timestamp(ts_raw) if isinstance(ts_raw, bytes) else None
    lang_val = _get_field(raw, 6, 0)
    language = LANGUAGE_OR_RUNTIME.get(lang_val, f"UNKNOWN({lang_val})")

    if language == "UNSPECIFIED" and package_name:
        for prefix, lang in _ECOSYSTEM_LANGUAGE.items():
            if package_name.startswith(prefix):
                language = lang
                break
    ver_val = _get_field(raw, 7, 0)
    version = CALLGRAPH_VERSION.get(ver_val, f"UNKNOWN({ver_val})")

    cha_raw = _get_field(raw, 3)
    internal_types: list[TypeInfo] = []
    external_types: list[TypeInfo] = []
    if isinstance(cha_raw, bytes):
        for entry in _get_fields(cha_raw, 1):
            if isinstance(entry, bytes):
                key_raw, type_body = _decode_proto_map_entry(entry)
                if key_raw and isinstance(type_body, bytes):
                    internal_types.append(_decode_type(str(key_raw), type_body))
        for entry in _get_fields(cha_raw, 2):
            if isinstance(entry, bytes):
                key_raw, type_body = _decode_proto_map_entry(entry)
                if key_raw and isinstance(type_body, bytes):
                    external_types.append(_decode_type(str(key_raw), type_body))

    call_edges = [
        _decode_call(call_raw)
        for call_raw in _get_fields(raw, 5)
        if isinstance(call_raw, bytes)
    ]

    meta = envelope.get("meta", {})
    info = CallGraphInfo(
        uuid=envelope.get("uuid", ""),
        namespace=envelope.get("tenant_meta", {}).get("namespace", ""),
        parent_uuid=meta.get("parent_uuid", ""),
        create_time_iso=meta.get("create_time", ""),
        update_time_iso=meta.get("update_time", ""),
        package_name=package_name,
        proto_create_time=proto_ts,
        language=language,
        version=version,
        internal_types=internal_types,
        external_types=external_types,
        call_edges=call_edges,
    )
    info.build_index()
    return info


# ===================================================================
#  Section 4 — Callgraph rendering (Markdown)
# ===================================================================


def _short_type_key(key: str) -> str:
    """Shorten a type key for display."""
    if key.startswith("/[") and "]" in key:
        inner = key[2 : key.index("]")]
        parts = inner.split(":")
        module_path = parts[-1] if len(parts) >= 3 else inner
        suffix = key[key.index("]") + 1 :].rstrip("/")
        return f"{module_path}{suffix}" if suffix else module_path
    return key


def _build_call_tree(info: CallGraphInfo) -> str:
    """Build an ASCII call tree rooted at entry-point modules."""
    adj: dict[int, list[tuple[int, list[CallSiteInfo]]]] = {}
    for edge in info.call_edges:
        adj.setdefault(edge.source_id, []).append((edge.target_id, edge.callsites))

    all_targets = {edge.target_id for edge in info.call_edges}
    roots: list[int] = [
        m.method_id
        for t in info.internal_types
        for m in t.methods
        if m.method_id not in all_targets
    ]
    if not roots:
        roots = [
            m.method_id
            for t in info.internal_types
            for m in t.methods
            if m.uri.endswith("/()")
        ]

    lines: list[str] = []
    visited: set[int] = set()

    def _walk(mid: int, prefix: str, is_last: bool, depth: int) -> None:
        if depth > 15:
            return
        connector = "\u2514\u2500\u2500 " if is_last else "\u251c\u2500\u2500 "
        label = info.callable_label(mid)
        c = info._callable_index.get(mid)
        line_info = ""
        if c and c.first_line is not None:
            if c.last_line is not None:
                line_info = f"  [L{c.first_line}-{c.last_line}]"
            else:
                line_info = f"  [L{c.first_line}]"
        lines.append(f"{prefix}{connector}{label}{line_info}")
        if mid in visited:
            new_prefix = prefix + ("    " if is_last else "\u2502   ")
            lines.append(f"{new_prefix}(cycle -- see above)")
            return
        visited.add(mid)
        children = adj.get(mid, [])
        new_prefix = prefix + ("    " if is_last else "\u2502   ")
        for i, (child_id, _sites) in enumerate(children):
            _walk(child_id, new_prefix, i == len(children) - 1, depth + 1)

    for i, root_id in enumerate(sorted(set(roots))):
        if i > 0:
            lines.append("")
        label = info.callable_label(root_id)
        c = info._callable_index.get(root_id)
        line_info = ""
        if c and c.first_line is not None:
            if c.last_line is not None:
                line_info = f"  [L{c.first_line}-{c.last_line}]"
            else:
                line_info = f"  [L{c.first_line}]"
        lines.append(f"{label}{line_info}")
        visited.add(root_id)
        children = adj.get(root_id, [])
        for j, (child_id, _) in enumerate(children):
            _walk(child_id, "", j == len(children) - 1, 1)

    return "\n".join(lines) if lines else "(no call tree could be reconstructed)"


def build_call_tree(info: CallGraphInfo) -> str:
    """Public helper that renders a call tree from decoded call graph info."""
    return _build_call_tree(info)


def _infer_profile(info: CallGraphInfo) -> str:
    """Attempt to infer what the application does from the call graph."""
    lines: list[str] = []
    lines.append(f"- **Language**: {info.language}")

    dep_names: set[str] = set()
    for t in info.external_types:
        key = _short_type_key(t.key)
        if "/" in key:
            dep_names.add(key.split("/")[0].split(":")[0])
        else:
            dep_names.add(key.split(":")[0])

    if dep_names:
        lines.append(
            f"- **Dependencies referenced in call graph**: "
            f"{', '.join(sorted(dep_names))}"
        )

    patterns: list[str] = []
    all_uris = [m.uri for t in info.internal_types for m in t.methods]
    uri_text = " ".join(all_uris).lower()
    if any(d in dep_names for d in ("express", "koa", "fastify", "hapi")):
        patterns.append("Web server (Node.js)")
    if any(d in dep_names for d in ("flask", "django", "fastapi", "starlette")):
        patterns.append("Web server (Python)")
    if "jsonwebtoken" in dep_names or "jwt" in uri_text:
        patterns.append("JWT authentication")
    if "bcrypt" in dep_names or "argon2" in dep_names:
        patterns.append("Password hashing")
    if any(d in dep_names for d in ("mongoose", "sequelize", "typeorm", "prisma")):
        patterns.append("Database ORM")
    if patterns:
        lines.append(f"- **Detected patterns**: {', '.join(patterns)}")

    module_names = [_short_type_key(t.key) for t in info.internal_types]
    lines.append(f"- **Application modules**: {', '.join(sorted(module_names))}")
    total_funcs = sum(len(t.methods) for t in info.internal_types)
    total_dep_funcs = sum(len(t.methods) for t in info.external_types)
    lines.append(f"- **First-party functions**: {total_funcs}")
    lines.append(f"- **Third-party function stubs**: {total_dep_funcs}")
    lines.append(f"- **Cross-module call edges**: {len(info.call_edges)}")
    return "\n".join(lines) + "\n"


def render_callgraph_analysis(info: CallGraphInfo) -> str:
    """Render a full Markdown analysis document for a decoded call graph.

    Args:
        info: Decoded :class:`CallGraphInfo`.

    Returns:
        Complete Markdown string.
    """
    sections: list[str] = []

    sections.append(f"# Call Graph Analysis: `{info.package_name}`\n")
    sections.append(
        textwrap.dedent(f"""\
        | Field | Value |
        |-------|-------|
        | UUID | `{info.uuid}` |
        | Namespace | `{info.namespace}` |
        | Parent (PackageVersion) UUID | `{info.parent_uuid}` |
        | Scan created | {info.create_time_iso} |
        | Scan updated | {info.update_time_iso} |
        | Language | {info.language} |
        | Callgraph version | {info.version} |
        | Internal types (modules) | {len(info.internal_types)} |
        | External types (deps) | {len(info.external_types)} |
        | Cross-module call edges | {len(info.call_edges)} |
        | Total callables | {len(info._callable_index)} |
        """)
    )

    sections.append(
        "> Proto schema: `spec/internal/plugin/v1/call_graph.proto` "
        "(endorlabs/monorepo). Inner message is `CallGraph` with CHA "
        "(types+methods), call_sites (edges), lang_or_rt, and version fields.\n"
    )

    # First-party modules
    sections.append("## First-Party Modules (CHA.internal_types)\n")
    for t in sorted(info.internal_types, key=lambda x: x.key):
        short = _short_type_key(t.key)
        src = t.source_file or "(unknown)"
        sections.append(f"### `{short}`\n")
        sections.append(f"- **Source file**: `{src}`")
        sections.append(f"- **Access**: {t.access} | **Class type**: {t.class_type}")
        sections.append(f"- **Methods**: {len(t.methods)}\n")
        if t.methods:
            sections.append("| ID | Function | Lines | Access | Defined |")
            sections.append("|----|----------|-------|--------|---------|")
            for m in sorted(t.methods, key=lambda x: x.method_id):
                fn_name = m.uri
                if "]/" in fn_name:
                    fn_name = fn_name.rsplit("]/", 1)[-1] or "(module scope)"
                lines_str = ""
                if m.first_line is not None and m.last_line is not None:
                    lines_str = f"L{m.first_line}-{m.last_line}"
                elif m.first_line is not None:
                    lines_str = f"L{m.first_line}"
                sections.append(
                    f"| {m.method_id} | `{fn_name}` | {lines_str} "
                    f"| {m.access} | {m.defined} |"
                )
        sections.append("")

    # External types
    sections.append("## Third-Party Dependencies (CHA.external_types)\n")
    for t in sorted(info.external_types, key=lambda x: x.key):
        short = _short_type_key(t.key)
        sections.append(f"### `{short}`\n")
        if t.methods:
            sections.append("| ID | Function | Access |")
            sections.append("|----|----------|--------|")
            for m in sorted(t.methods, key=lambda x: x.method_id):
                fn_name = m.uri
                if "]/" in fn_name:
                    fn_name = fn_name.rsplit("]/", 1)[-1] or "(module scope)"
                sections.append(f"| {m.method_id} | `{fn_name}` | {m.access} |")
        sections.append("")

    # Call tree
    sections.append("## Reconstructed Call Tree\n")
    sections.append(
        "The tree below shows the caller-to-callee relationships starting from\n"
        "entry-point functions (those not called by any other function).\n"
    )
    tree = _build_call_tree(info)
    sections.append("```")
    sections.append(tree)
    sections.append("```\n")

    # Edge table
    sections.append("## Cross-Module Call Edges (CallGraph.call_sites)\n")
    sections.append("| # | Source | Target | Call Type | Receiver |")
    sections.append("|---|--------|--------|-----------|----------|")
    for i, edge in enumerate(info.call_edges, 1):
        src_label = info.callable_short(edge.source_id)
        tgt_label = info.callable_short(edge.target_id)
        types_set = {s.call_type for s in edge.callsites}
        receivers = [r for s in edge.callsites for r in s.receiver]
        type_str = ", ".join(sorted(types_set)) if types_set else "-"
        recv_str = ", ".join(f"`{r}`" for r in receivers[:3]) if receivers else "-"
        sections.append(
            f"| {i} | `{src_label}` | `{tgt_label}` | {type_str} | {recv_str} |"
        )
    sections.append("")

    # Source files
    sections.append("## Source Files\n")
    files = sorted({t.source_file for t in info.internal_types if t.source_file})
    if files:
        sections.extend(f"- `{f}`" for f in files)
    else:
        sections.append("(no source files recorded)")
    sections.append("")

    sections.append("## Application Profile (inferred)\n")
    sections.append(_infer_profile(info))

    sections.append(
        "> **Limitations**: No dataflow analysis (call edges only). "
        "Anonymous function names are positional (line:column). "
        "Third-party stubs are shallow (exported entry points only). "
        "No HTTP route annotations.\n"
    )

    return "\n".join(sections)


# ===================================================================
#  Section 5 — Utility helpers
# ===================================================================


def slugify(name: str, max_len: int = 80) -> str:
    """Turn a package/project name into a filesystem-safe slug."""
    s = re.sub(r"https?://github\.com/", "", name)
    s = s.rstrip(".git").rstrip("/")
    s = re.sub(r"[^a-zA-Z0-9._-]+", "_", s)
    s = s.strip("_")
    return s[:max_len] if s else "unknown"


def write_json(path: str | Path, data: Any, *, base_dir: Path | None = None) -> None:
    """Write *data* as formatted JSON, creating parent directories.

    When *base_dir* is provided the target path is resolved and checked
    for containment so that ``../`` sequences cannot escape the intended
    output directory.
    """
    from endorlabs.utils.path_safety import safe_write_text

    path = Path(path)
    content = json.dumps(data, indent=2, default=str, ensure_ascii=False)
    if base_dir is not None:
        safe_write_text(base_dir, path, content)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    logger.info("  Wrote %s", path)


def extract_objects(resp_data: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract objects list from standard Endor API response."""
    if isinstance(resp_data, dict) and "list" in resp_data:
        list_data = resp_data["list"]
        if isinstance(list_data, dict) and "objects" in list_data:
            return list_data["objects"] or []
    return []


def paginate_raw(
    api_client: APIClient,
    url: str,
    params: dict[str, str],
    max_pages: int = 10,
) -> list[dict[str, Any]]:
    """Paginate a raw API list call, returning all objects."""
    all_objects: list[dict[str, Any]] = []
    current_params = dict(params)

    for _page in range(max_pages):
        resp = api_client.get(url, params=current_params)
        data = resp.json()
        objects = extract_objects(data)
        all_objects.extend(objects)

        next_token = None
        next_page_id = None
        if isinstance(data, dict) and "list" in data:
            list_data = data["list"]
            if isinstance(list_data, dict) and "response" in list_data:
                resp_meta = list_data["response"]
                next_token = resp_meta.get("next_page_token")
                next_page_id = resp_meta.get("next_page_id")

        if next_page_id:
            current_params["list_parameters.page_id"] = str(next_page_id)
        elif next_token:
            current_params["list_parameters.page_token"] = str(next_token)
        else:
            break

    return all_objects


def parse_dep_name(dep_name: str) -> tuple[str, str]:
    """Split ``npm://express@4.22.1`` into ``('npm://express', '4.22.1')``."""
    if "@" not in dep_name:
        return dep_name, ""
    idx = dep_name.rfind("@")
    if idx <= 0:
        return dep_name, ""
    if dep_name[idx - 1] == "/":
        return dep_name, ""
    return dep_name[:idx], dep_name[idx + 1 :]


# ===================================================================
#  Section 6 — BOM helpers
# ===================================================================


def _bom_to_serializable(bom: Any) -> dict[str, Any]:
    """Convert a BOM (model or dict) to a plain serializable dict."""
    if isinstance(bom, dict):
        return bom
    if hasattr(bom, "model_dump"):
        return bom.model_dump(mode="json", warnings=False)
    return {"raw": str(bom)}


def retrieve_bom_full(pv: Any) -> dict[str, Any]:
    """Extract the full BOM from a PackageVersion as a serializable dict."""
    bom = pv.spec.resolved_dependencies if pv.spec else None
    if bom is None:
        return {}
    return _bom_to_serializable(bom)


def _normalize_children(children_raw: list[Any]) -> list[str]:
    """Normalize BOM graph children to a list of string keys."""
    children: list[str] = []
    if not children_raw:
        return children
    for c in children_raw:
        if isinstance(c, str):
            children.append(c)
        elif isinstance(c, dict):
            children.append(c.get("name", c.get("key", str(c))))
        else:
            children.append(str(c))
    return children


def count_transitive_children(graph: dict[str, Any], root: str) -> int:
    """BFS from *root*, return count of unique transitive descendants."""
    visited: set[str] = set()
    queue = deque(_normalize_children(graph.get(root, [])))
    while queue:
        node = queue.popleft()
        if node in visited:
            continue
        visited.add(node)
        queue.extend(
            c for c in _normalize_children(graph.get(node, [])) if c not in visited
        )
    return len(visited)


def extract_direct_deps(graph: dict[str, Any]) -> list[tuple[str, str, int]]:
    """Find direct dependencies from a BOM adjacency-list graph.

    Returns ``[(full_name, version, transitive_child_count), ...]``.
    """
    all_children: set[str] = set()
    for children_raw in graph.values():
        if isinstance(children_raw, list):
            all_children.update(_normalize_children(children_raw))

    roots = [k for k in graph if k not in all_children]
    if not roots:
        roots = list(graph.keys())[:3]

    direct_dep_names: list[str] = []
    for root in roots:
        direct_dep_names.extend(_normalize_children(graph.get(root, [])))

    seen: set[str] = set()
    unique_directs: list[str] = []
    for d in direct_dep_names:
        if d not in seen:
            seen.add(d)
            unique_directs.append(d)

    result: list[tuple[str, str, int]] = []
    for dep in sorted(unique_directs):
        name, ver = parse_dep_name(dep)
        result.append((name, ver, count_transitive_children(graph, dep)))
    return result


def render_slim_dependencies(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Transform raw DependencyMetadata rows into slim dicts."""
    slim: list[dict[str, Any]] = []
    for row in rows:
        spec = row.get("spec", {}) or {}
        dd = spec.get("dependency_data", {}) or {}
        reach_raw = str(dd.get("reachable", "") or dd.get("reachability", ""))
        if "UNREACHABLE" in reach_raw:
            reachable: bool | None = False
        elif "REACHABLE" in reach_raw:
            reachable = True
        else:
            reachable = None
        slim.append(
            {
                "name": dd.get("package_name", "") or "",
                "version": (
                    dd.get("resolved_version", "")
                    or dd.get("unresolved_version", "")
                    or ""
                ),
                "direct": dd.get("direct", False),
                "reachable": reachable,
                "ecosystem": (dd.get("ecosystem", "") or "")
                .replace("ECOSYSTEM_", "")
                .lower(),
                "scope": (dd.get("scope", "") or "")
                .replace("DEPENDENCY_SCOPE_", "")
                .lower(),
            }
        )
    return slim


# ===================================================================
#  Section 7 — DependencyMetadata retrieval and summarization
# ===================================================================


def retrieve_dep_metadata_full(
    api_client: APIClient,
    project_namespace: str,
    project_uuid: str,
    max_pages: int = 10,
) -> tuple[list[dict[str, Any]], str]:
    """Retrieve all DependencyMetadata rows for a project.

    Tries the project's namespace first, then falls back to ``"oss"``.
    Returns ``(rows, source_namespace)``.
    """
    from endorlabs.operations import validate_namespace

    for ns in [project_namespace, "oss"]:
        url = f"v1/namespaces/{validate_namespace(ns)}/dependency-metadata"
        params = {
            "list_parameters.filter": (
                f'spec.importer_data.project_uuid=="{project_uuid}"'
            ),
            "list_parameters.page_size": "500",
        }
        objects = paginate_raw(api_client, url, params, max_pages=max_pages)
        if objects:
            return objects, ns
    return [], ""


def summarize_dep_metadata(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Build a human-readable summary from raw DependencyMetadata rows."""
    stats: dict[str, Any] = {
        "total": len(rows),
        "direct": 0,
        "transitive": 0,
        "reachable": 0,
        "unreachable": 0,
        "unknown_reachability": 0,
        "by_ecosystem": defaultdict(int),
        "by_scope": defaultdict(int),
    }
    for row in rows:
        spec = row.get("spec", {}) or {}
        dd = spec.get("dependency_data", {}) or {}
        if dd.get("direct", False):
            stats["direct"] += 1
        else:
            stats["transitive"] += 1
        reach = dd.get("reachable", "") or dd.get("reachability", "")
        if isinstance(reach, str):
            if "UNREACHABLE" in reach:
                stats["unreachable"] += 1
            elif "REACHABLE" in reach:
                stats["reachable"] += 1
            else:
                stats["unknown_reachability"] += 1
        eco = dd.get("ecosystem", "?") or "?"
        stats["by_ecosystem"][eco] += 1
        scope = dd.get("scope", "?") or "?"
        stats["by_scope"][scope] += 1
    stats["by_ecosystem"] = dict(stats["by_ecosystem"])
    stats["by_scope"] = dict(stats["by_scope"])
    return stats


# ===================================================================
#  Section 8 — Call graph retrieval
# ===================================================================


def retrieve_call_graph_full(
    api_client: APIClient,
    namespace: str,
    pv_uuid: str,
) -> dict[str, Any]:
    """Retrieve the full call graph data for a PackageVersion.

    Uses ``x-callgraph-encoding=any`` header to request JSON encoding.
    """
    from endorlabs.operations import validate_namespace

    ns = validate_namespace(namespace)
    url = f"v1/namespaces/{ns}/call-graph-data"
    params = {
        "list_parameters.filter": f'meta.parent_uuid=="{pv_uuid}"',
        "list_parameters.page_size": "1",
    }
    resp = api_client.get(url, params=params)
    data = resp.json()
    objects = extract_objects(data)
    if not objects:
        return {}

    cg_uuid = objects[0].get("uuid", "")
    if not cg_uuid:
        return objects[0]

    get_url = f"v1/namespaces/{ns}/call-graph-data/{cg_uuid}"
    try:
        resp_full = api_client.get(
            get_url,
            headers={"x-callgraph-encoding": "any"},
        )
        return resp_full.json()
    except Exception as exc:
        logger.warning("  Unable to GET full call graph %s: %s", cg_uuid, exc)
        return objects[0]


def retrieve_call_graph_for_client(
    client: Client,
    namespace: str,
    pv_uuid: str,
) -> dict[str, Any]:
    """Retrieve call graph data using a high-level ``Client`` instance."""
    api_client = getattr(client, "_client", None)
    if api_client is None:
        raise RuntimeError("Client is closed; cannot retrieve call graph data.")
    return retrieve_call_graph_full(api_client, namespace, pv_uuid)


def summarize_call_graph(cg_data: dict[str, Any]) -> dict[str, Any]:
    """Extract a human-readable summary dict from raw call graph data."""
    summary: dict[str, Any] = {
        "uuid": cg_data.get("uuid", ""),
        "top_level_keys": list(cg_data.keys()),
    }
    meta = cg_data.get("meta", {})
    if meta:
        summary["name"] = meta.get("name", "")
        summary["parent_uuid"] = meta.get("parent_uuid", "")
    spec = cg_data.get("spec", {})
    if spec:
        summary["spec_keys"] = list(spec.keys())
        any_data = spec.get("any", {})
        if any_data and isinstance(any_data, dict):
            summary["call_graph_format"] = "json (any)"
            summary["call_graph_top_keys"] = list(any_data.keys())[:20]
        elif spec.get("zstd_bytes"):
            summary["call_graph_format"] = "zstd_bytes (binary)"
            zb = spec["zstd_bytes"]
            summary["zstd_bytes_length"] = (
                len(zb) if isinstance(zb, (str, bytes)) else "?"
            )
        elif spec.get("storage_url"):
            summary["call_graph_format"] = "external_storage"
        elif spec.get("related_object"):
            summary["call_graph_format"] = "related_object reference"
    return summary


def _clean_source_path(path: str) -> str:
    """Strip ``/tmp/endorctl/<project>/`` prefix from source file paths."""
    if "/tmp/endorctl/" in path:
        after = path.split("/tmp/endorctl/", 1)[1]
        if "/" in after:
            return after.split("/", 1)[1]
        return after
    return path


def render_call_graph_summary_md(cg_json_path: str | Path) -> str | None:
    """Decode a call graph JSON and return a compact Markdown summary.

    Returns ``None`` if ``zstandard`` is unavailable or data lacks ``zstd_bytes``.
    """
    if not _HAS_ZSTD:
        return None
    try:
        with open(cg_json_path, encoding="utf-8") as f:
            envelope = json.load(f)
    except Exception:
        return None
    if "zstd_bytes" not in envelope:
        return None
    try:
        info = decode_callgraph(envelope)
    except Exception as exc:
        logger.warning("Unable to decode call graph: %s", exc)
        return None

    total_fp = sum(len(t.methods) for t in info.internal_types)
    total_tp = sum(len(t.methods) for t in info.external_types)
    lines: list[str] = [
        f"{info.language} | {total_fp} first-party functions | "
        f"{total_tp} third-party stubs | {len(info.call_edges)} call edges",
        "",
    ]
    file_funcs: dict[str, list[str]] = {}
    for t in info.internal_types:
        src = _clean_source_path(t.source_file) if t.source_file else "(unknown)"
        if src not in file_funcs:
            file_funcs[src] = []
        for m in t.methods:
            fn = m.uri
            if "]/" in fn:
                fn = fn.rsplit("]/", 1)[-1]
            if not fn or fn == "()":
                continue
            fn = fn.split(".anonymous_function")[0]
            if fn and fn not in file_funcs[src]:
                file_funcs[src].append(fn)

    lines.append("| Source File | Key Functions |")
    lines.append("|-------------|---------------|")
    for src in sorted(file_funcs.keys()):
        funcs = file_funcs[src] or ["(module init)"]
        func_str = ", ".join(f"`{f}`" for f in funcs[:4])
        if len(funcs) > 4:
            func_str += f" (+{len(funcs) - 4} more)"
        lines.append(f"| `{src}` | {func_str} |")
    return "\n".join(lines)


def generate_call_graph_analysis_md(cg_json_path: str | Path) -> str | None:
    """Decode a call graph JSON and write an ``_analysis.md`` alongside it.

    Returns the path to the generated file, or ``None`` on failure.
    """
    if not _HAS_ZSTD:
        return None
    cg_json_path = Path(cg_json_path)
    try:
        envelope = json.loads(cg_json_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if "zstd_bytes" not in envelope:
        return None
    try:
        info = decode_callgraph(envelope)
        md = render_callgraph_analysis(info)
    except Exception as exc:
        logger.warning("Unable to generate call graph analysis: %s", exc)
        return None
    from endorlabs.utils.path_safety import safe_write_text

    out_path = cg_json_path.with_name(cg_json_path.stem + "_analysis.md")
    safe_write_text(cg_json_path.parent, out_path, md)
    logger.info("  Wrote %s", out_path)
    return str(out_path)


# ===================================================================
#  Section 9 — Per-project orchestration
# ===================================================================


@dataclass
class PVResult:
    """Per-PackageVersion retrieval results."""

    pv_name: str = ""
    pv_uuid: str = ""
    pv_slug: str = ""
    cg_available: bool = False
    bom_file: str = ""
    cg_file: str = ""
    cg_analysis_file: str = ""
    deps_file: str = ""
    bom_summary: dict[str, Any] = field(default_factory=dict)
    cg_summary: dict[str, Any] = field(default_factory=dict)
    direct_deps: list[tuple[str, str, int]] = field(default_factory=list)
    graph_nodes: int = 0


@dataclass
class ProjectResult:
    """Full retrieval results for one project."""

    project_uuid: str = ""
    project_name: str = ""
    namespace: str = ""
    slug: str = ""
    out_dir: str = ""
    pv_results: list[PVResult] = field(default_factory=list)
    dep_metadata_stats: dict[str, Any] = field(default_factory=dict)
    dep_metadata_namespace: str = ""
    dep_metadata_count: int = 0
    report: str = ""


def process_project(
    client: Client,
    api_client: APIClient,
    root_namespace: str,
    project: Any,
    out_dir: str,
    pv_limit: int = 5,
    dep_metadata_max_pages: int = 10,
    *,
    deterministic: bool = False,
) -> ProjectResult:
    """Retrieve full dependency tree and call graph data for one project.

    Args:
        client: Authenticated Endor Labs Client.
        api_client: Low-level APIClient for raw calls.
        root_namespace: Tenant namespace.
        project: Project resource object.
        out_dir: Output directory for this project's artifacts.
        pv_limit: Maximum PackageVersions to process.
        dep_metadata_max_pages: Max pages for DependencyMetadata pagination.
        deterministic: When True, sort package versions and dependency rows
            so output artifacts are stable across runs.

    Returns:
        :class:`ProjectResult` with paths to all written artifacts.
    """
    project_name = project.meta.name if project.meta else project.uuid
    project_ns = (
        project.tenant_meta.namespace
        if project.tenant_meta and project.tenant_meta.namespace
        else root_namespace
    )
    slug = slugify(project_name)
    os.makedirs(out_dir, exist_ok=True)

    result = ProjectResult(
        project_uuid=project.uuid,
        project_name=project_name,
        namespace=project_ns,
        slug=slug,
        out_dir=out_dir,
    )

    # 1. PackageVersions
    logger.info("  Fetching PackageVersions ...")
    from endorlabs import F

    pvs = client.PackageVersion.list(  # type: ignore[attr-defined]
        namespace=project_ns,
        filter=F("spec.project_uuid") == project.uuid,
        max_pages=1,
        page_size=pv_limit,
    )
    pvs = pvs[:pv_limit]
    if deterministic:
        pvs = sorted(pvs, key=lambda pv: str(pv.meta.name if pv.meta else pv.uuid))
    single_pv = len(pvs) == 1

    # 2. Per-PV: BOM + Call Graph
    for pv in pvs:
        pv_name = pv.meta.name if pv.meta else pv.uuid
        pv_slug = slugify(pv_name, max_len=60)
        cg_available = bool(pv.spec and pv.spec.call_graph_available)

        pvr = PVResult(
            pv_name=pv_name,
            pv_uuid=pv.uuid,
            pv_slug=pv_slug,
            cg_available=cg_available,
        )

        # BOM
        bom_data = retrieve_bom_full(pv)
        if bom_data:
            bom_filename = "bom.json" if single_pv else f"bom_{pv_slug}.json"
            bom_path = os.path.join(out_dir, bom_filename)
            write_json(bom_path, bom_data, base_dir=Path(out_dir))
            pvr.bom_file = bom_path
            graph = bom_data.get("dependency_graph", {}) or {}
            pvr.graph_nodes = len(graph)
            pvr.direct_deps = extract_direct_deps(graph)
            pvr.bom_summary = {
                "graph_nodes": len(graph),
                "dependency_count": len(bom_data.get("dependencies", []) or []),
            }

        # Call Graph
        logger.info("  [CallGraph] %s (available=%s)", pv_name, cg_available)
        cg_data = retrieve_call_graph_full(api_client, project_ns, pv.uuid)
        if cg_data:
            cg_filename = (
                "call_graph.json" if single_pv else f"call_graph_{pv_slug}.json"
            )
            cg_path = os.path.join(out_dir, cg_filename)
            write_json(cg_path, cg_data, base_dir=Path(out_dir))
            pvr.cg_file = cg_path
            pvr.cg_summary = summarize_call_graph(cg_data)
            analysis_path = generate_call_graph_analysis_md(cg_path)
            if analysis_path:
                pvr.cg_analysis_file = analysis_path

        result.pv_results.append(pvr)

    # 3. DependencyMetadata
    logger.info("  [DepMetadata] project_uuid=%s", project.uuid)
    dep_rows, dep_ns = retrieve_dep_metadata_full(
        api_client,
        project_ns,
        project.uuid,
        max_pages=dep_metadata_max_pages,
    )
    if deterministic:
        dep_rows = sorted(
            dep_rows,
            key=lambda row: (
                str(row.get("tenant_meta", {}).get("namespace", "")),
                str(
                    row.get("spec", {})
                    .get("dependency_data", {})
                    .get("package_name", "")
                ),
                str(
                    row.get("spec", {})
                    .get("dependency_data", {})
                    .get("resolved_version", "")
                ),
            ),
        )
    result.dep_metadata_count = len(dep_rows)
    result.dep_metadata_namespace = dep_ns
    out_base = Path(out_dir)
    if dep_rows:
        write_json(
            os.path.join(out_dir, "dep_metadata.json"),
            dep_rows,
            base_dir=out_base,
        )
        result.dep_metadata_stats = summarize_dep_metadata(dep_rows)
        slim = render_slim_dependencies(dep_rows)
        write_json(
            os.path.join(out_dir, "dependencies.json"),
            slim,
            base_dir=out_base,
        )

    # 4. Build summary
    result.report = build_dependency_callgraph_summary(result)
    return result


# ===================================================================
#  Section 10 — Markdown summary builders
# ===================================================================


def _render_pv_section(pv: PVResult, heading_level: str, buf: StringIO) -> None:
    """Render one PV's Dependencies + Call Graph into the Markdown buffer."""
    dep_count = max(pv.graph_nodes - 1, 0)
    direct_count = len(pv.direct_deps)
    transitive_count = dep_count - direct_count if dep_count > direct_count else 0

    buf.write(
        f"{heading_level} Dependencies"
        f" \u2014 {dep_count} total"
        f" ({direct_count} direct, {transitive_count} transitive)\n\n"
    )
    if pv.direct_deps:
        buf.write("| Direct Dependency | Version | Transitive Children |\n")
        buf.write("|-------------------|---------|---------------------|\n")
        buf.writelines(
            f"| {name} | {ver} | {trans} |\n" for name, ver, trans in pv.direct_deps
        )
        buf.write("\n")

    bom_fn = os.path.basename(pv.bom_file) if pv.bom_file else None
    if bom_fn:
        buf.write(f"> Full graph: [`{bom_fn}`]({bom_fn}) ({pv.graph_nodes} nodes)\n")
    buf.write("\n")

    if pv.cg_available or pv.cg_file:
        buf.write(f"{heading_level} Call Graph\n\n")
        cg_fn = os.path.basename(pv.cg_file) if pv.cg_file else None
        cg_analysis_fn = (
            os.path.basename(pv.cg_analysis_file) if pv.cg_analysis_file else None
        )
        cg_md: str | None = None
        if pv.cg_file and os.path.isfile(pv.cg_file):
            cg_md = render_call_graph_summary_md(pv.cg_file)
        if cg_md:
            buf.write(cg_md)
            buf.write("\n\n")
        else:
            uuid_val = pv.cg_summary.get("uuid", "n/a")
            fmt = pv.cg_summary.get("call_graph_format", "unknown")
            buf.write(f"UUID: `{uuid_val}` | Format: {fmt}\n\n")
        if cg_analysis_fn:
            buf.write(f"> Decoded analysis: [`{cg_analysis_fn}`]({cg_analysis_fn})  \n")
        if cg_fn:
            buf.write(f"> Raw data: [`{cg_fn}`]({cg_fn})\n")
        buf.write("\n")


def build_dependency_callgraph_summary(result: ProjectResult) -> str:
    """Build the ``dependency-callgraph-summary.md`` content.

    This is the renamed equivalent of the old ``README.md`` / ``summary.txt``.
    """
    buf = StringIO()
    single_pv = len(result.pv_results) == 1

    if single_pv and result.pv_results:
        buf.write(f"# {result.pv_results[0].pv_name}\n\n")
    else:
        buf.write(f"# {result.project_name}\n\n")

    buf.write("| | |\n|---|---|\n")
    buf.write(f"| Repository | {result.project_name} |\n")
    buf.write(f"| Project UUID | `{result.project_uuid}` |\n")
    buf.write(f"| Namespace | `{result.namespace}` |\n\n")

    if not single_pv and result.pv_results:
        buf.write(f"## Package Versions ({len(result.pv_results)})\n\n")
        buf.write("| # | Package Version | Dependencies | Call Graph | BOM File |\n")
        buf.write("|---|----------------|--------------|------------|----------|\n")
        for i, pvr in enumerate(result.pv_results, 1):
            bom_fn = os.path.basename(pvr.bom_file) if pvr.bom_file else "-"
            cg_yn = "Yes" if (pvr.cg_available or pvr.cg_file) else "No"
            dep_count = max(pvr.graph_nodes - 1, 0)
            buf.write(f"| {i} | {pvr.pv_name} | {dep_count} | {cg_yn} | `{bom_fn}` |\n")
        buf.write("\n")

    for i, pvr in enumerate(result.pv_results, 1):
        if single_pv:
            heading = "##"
        else:
            buf.write(f"---\n\n### {i}. {pvr.pv_name}\n\n")
            heading = "####"
        _render_pv_section(pvr, heading, buf)

    stats = result.dep_metadata_stats
    if stats:
        if not single_pv:
            buf.write("---\n\n")
        buf.write("## Dependency Metadata (project-level)\n\n")
        total = stats.get("total", 0)
        direct = stats.get("direct", 0)
        trans = stats.get("transitive", 0)
        reach = stats.get("reachable", 0)
        unreach = stats.get("unreachable", 0)
        unknown = stats.get("unknown_reachability", 0)
        ecos = stats.get("by_ecosystem", {})
        eco_parts = [
            f"{k.replace('ECOSYSTEM_', '')}: {v}" for k, v in sorted(ecos.items())
        ]
        buf.write(f"- **Total**: {total} ({direct} direct, {trans} transitive)\n")
        buf.write(
            f"- **Reachability**: {reach} reachable, "
            f"{unreach} unreachable, {unknown} unknown\n"
        )
        if eco_parts:
            buf.write(f"- **Ecosystems**: {', '.join(eco_parts)}\n")
        buf.write("\n")

    ts = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    buf.write(f"---\n\n*Generated at {ts}*\n")
    return buf.getvalue()
