"""Protobuf wire-format decoder for CallGraphData payloads (no compiled proto)."""

from __future__ import annotations

import base64
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

try:
    import zstandard
except ImportError:
    zstandard = None

_HAS_ZSTD = zstandard is not None

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
        if method_id_raw is not None:
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
        if site_key_raw is not None:
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
                if key_raw:
                    internal_types.append(_decode_type(str(key_raw), type_body))
        for entry in _get_fields(cha_raw, 2):
            if isinstance(entry, bytes):
                key_raw, type_body = _decode_proto_map_entry(entry)
                if key_raw:
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
