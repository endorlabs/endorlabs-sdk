"""Tests for split dependency/call-graph workflow modules.

Covers protobuf wire-format decoder, data class helpers, BOM utilities,
rendering, and summary builders. API-calling functions are tested with mocks.
"""

from __future__ import annotations

import json
import struct
from datetime import UTC, datetime
from io import StringIO
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, Mock

import pytest  # noqa: TC002

from endorlabs.operations.list_response import extract_list_objects as extract_objects
from endorlabs.resources.call_graph_data_proto import (
    CallableInfo,
    CallEdge,
    CallGraphInfo,
    TypeInfo,
    _decode_call,
    _decode_callable,
    _decode_callsite,
    _decode_proto_map_entry,
    _decode_raw_fields,
    _decode_timestamp,
    _get_field,
    _get_fields,
    _unwrap_bool,
    _unwrap_int,
    _unwrap_string,
)
from endorlabs.tools.callgraph_artifacts import _clean_source_path, summarize_call_graph
from endorlabs.utils.artifact_io import write_json
from endorlabs.workflows.agent_context.hydration import (
    ProjectResult,
    PVResult,
    _render_pv_section,
    build_dependency_callgraph_summary,
)
from endorlabs.workflows.callgraph.render import (
    _build_call_tree,
    _infer_profile,
    _short_type_key,
    render_callgraph_analysis,
)
from endorlabs.workflows.dependencies.bom_graph import (
    _bom_to_serializable,
    _normalize_children,
    count_transitive_children,
    extract_direct_deps,
    render_slim_dependencies,
    retrieve_bom_full,
)
from endorlabs.workflows.dependencies.coordinates import parse_dep_name
from endorlabs.workflows.dependencies.metadata_fetch import (
    retrieve_dep_metadata_full,
    summarize_dep_metadata,
)

# ===================================================================
# Helpers for building protobuf test data
# ===================================================================


def _encode_varint(value: int) -> bytes:
    """Encode an integer as a protobuf varint."""
    result = bytearray()
    while value > 0x7F:
        result.append((value & 0x7F) | 0x80)
        value >>= 7
    result.append(value & 0x7F)
    return bytes(result)


def _encode_field(field_number: int, wire_type: int, value: bytes) -> bytes:
    """Encode a protobuf field (tag + value)."""
    tag = (field_number << 3) | wire_type
    return _encode_varint(tag) + value


def _encode_varint_field(field_number: int, value: int) -> bytes:
    """Encode a varint field."""
    return _encode_field(field_number, 0, _encode_varint(value))


def _encode_length_delimited(field_number: int, data: bytes) -> bytes:
    """Encode a length-delimited field."""
    return _encode_field(field_number, 2, _encode_varint(len(data)) + data)


def _encode_string_wrapper(value: str) -> bytes:
    """Encode a protobuf StringValue wrapper (field 1 = string)."""
    inner = value.encode("utf-8")
    return _encode_length_delimited(1, inner)


def _encode_int_wrapper(value: int) -> bytes:
    """Encode a protobuf Int32Value wrapper (field 1 = varint)."""
    return _encode_varint_field(1, value)


def _parse_headings(md: str) -> list[str]:
    """Extract heading text from markdown (strips leading # and whitespace)."""
    return [
        line.lstrip("#").strip() for line in md.splitlines() if line.startswith("#")
    ]


# ===================================================================
#  Section 1 — Wire-format decoder tests (multi-field and edge cases)
# ===================================================================


class TestDecodeRawFields:
    """Test _decode_raw_fields for various wire types."""

    def test_varint_field(self) -> None:
        data = _encode_varint_field(1, 150)
        fields = _decode_raw_fields(data)
        assert len(fields) == 1
        assert fields[0][0] == 1  # field_number
        assert fields[0][1] == 0  # wire_type VARINT
        assert fields[0][2] == 150  # value

    def test_length_delimited_field(self) -> None:
        payload = b"hello"
        data = _encode_length_delimited(2, payload)
        fields = _decode_raw_fields(data)
        assert len(fields) == 1
        assert fields[0][0] == 2
        assert fields[0][1] == 2  # wire_type LENGTH_DELIMITED
        assert fields[0][2] == payload

    def test_multiple_fields(self) -> None:
        data = _encode_varint_field(1, 42) + _encode_length_delimited(2, b"test")
        fields = _decode_raw_fields(data)
        assert len(fields) == 2

    def test_32bit_field(self) -> None:
        tag = _encode_varint((3 << 3) | 5)  # field 3, wire_type 5 (32-bit)
        data = tag + struct.pack("<f", 3.14)
        fields = _decode_raw_fields(data)
        assert len(fields) == 1
        assert fields[0][0] == 3
        assert fields[0][1] == 5

    def test_64bit_field(self) -> None:
        tag = _encode_varint((4 << 3) | 1)  # field 4, wire_type 1 (64-bit)
        data = tag + struct.pack("<d", 2.718)
        fields = _decode_raw_fields(data)
        assert len(fields) == 1
        assert fields[0][0] == 4
        assert fields[0][1] == 1

    def test_empty_data(self) -> None:
        assert _decode_raw_fields(b"") == []

    def test_truncated_data_graceful(self) -> None:
        # Truncated varint tag — should stop gracefully
        data = bytes([0x80])  # incomplete varint
        fields = _decode_raw_fields(data)
        assert fields == []


class TestGetFields:
    """Test _get_fields and _get_field helpers."""

    def test_get_fields_returns_matching(self) -> None:
        data = (
            _encode_varint_field(1, 10)
            + _encode_varint_field(2, 20)
            + _encode_varint_field(1, 30)
        )
        vals = _get_fields(data, 1)
        assert vals == [10, 30]

    def test_get_fields_no_match(self) -> None:
        data = _encode_varint_field(1, 10)
        assert _get_fields(data, 99) == []

    def test_get_field_returns_first(self) -> None:
        data = _encode_varint_field(1, 10) + _encode_varint_field(1, 20)
        assert _get_field(data, 1) == 10

    def test_get_field_default(self) -> None:
        data = _encode_varint_field(1, 10)
        assert _get_field(data, 99, "missing") == "missing"

    def test_get_field_default_none(self) -> None:
        assert _get_field(b"", 1) is None


class TestUnwrappers:
    """Test _unwrap_string, _unwrap_int, _unwrap_bool."""

    def test_unwrap_string(self) -> None:
        data = _encode_string_wrapper("hello world")
        assert _unwrap_string(data) == "hello world"

    def test_unwrap_string_empty(self) -> None:
        # No field 1
        assert _unwrap_string(b"") == ""

    def test_unwrap_int(self) -> None:
        data = _encode_int_wrapper(42)
        assert _unwrap_int(data) == 42

    def test_unwrap_int_none(self) -> None:
        assert _unwrap_int(b"") is None

    def test_unwrap_bool_true(self) -> None:
        data = _encode_varint_field(1, 1)
        assert _unwrap_bool(data) is True

    def test_unwrap_bool_false(self) -> None:
        data = _encode_varint_field(1, 0)
        assert _unwrap_bool(data) is False

    def test_unwrap_bool_none(self) -> None:
        assert _unwrap_bool(b"") is None


# ===================================================================
#  Section 2 — Data class and CallGraphInfo tests
# ===================================================================


class TestCallGraphInfo:
    """Test CallGraphInfo methods."""

    @staticmethod
    def _make_info() -> CallGraphInfo:
        internal = TypeInfo(
            key="module/App",
            access="PUBLIC",
            class_type="REGULAR",
            source_file="app.py",
            methods=[
                CallableInfo(
                    method_id=1,
                    uri="python://[module:app.py]/main()",
                    access="PUBLIC",
                    first_line=1,
                    last_line=10,
                    defined=True,
                ),
                CallableInfo(
                    method_id=2,
                    uri="python://[module:app.py]/helper()",
                    access="PRIVATE",
                    first_line=12,
                    last_line=20,
                    defined=True,
                ),
            ],
        )
        external = TypeInfo(
            key="dep/Lib",
            access="PUBLIC",
            class_type="REGULAR",
            source_file="",
            methods=[
                CallableInfo(
                    method_id=100,
                    uri="python://dep/lib.do_thing()",
                    access="PUBLIC",
                    first_line=None,
                    last_line=None,
                    defined=False,
                ),
            ],
        )
        info = CallGraphInfo(
            uuid="cg-uuid",
            namespace="test.ns",
            parent_uuid="pv-uuid",
            create_time_iso="2025-01-01T00:00:00Z",
            update_time_iso="2025-01-01T01:00:00Z",
            package_name="pypi://test-pkg",
            proto_create_time=None,
            language="PYTHON",
            version="V7",
            internal_types=[internal],
            external_types=[external],
            call_edges=[
                CallEdge(source_id=1, target_id=2),
                CallEdge(source_id=2, target_id=100),
            ],
        )
        info.build_index()
        return info

    def test_build_index_populates(self) -> None:
        info = self._make_info()
        assert 1 in info._callable_index
        assert 2 in info._callable_index
        assert 100 in info._callable_index

    def test_callable_label_strips_prefix(self) -> None:
        info = self._make_info()
        label = info.callable_label(1)
        assert not label.startswith("python://")
        assert "main()" in label

    def test_callable_label_unknown(self) -> None:
        info = self._make_info()
        assert info.callable_label(999) == "<unknown id=999>"

    def test_callable_short(self) -> None:
        info = self._make_info()
        short = info.callable_short(1)
        assert short == "main()"

    def test_callable_short_no_bracket(self) -> None:
        info = self._make_info()
        # method 100 has no "]/" in URI
        short = info.callable_short(100)
        assert "do_thing()" in short


# ===================================================================
#  Section 3 — Protobuf decoding logic tests
# ===================================================================


class TestDecodeProtoMapEntry:
    """Test _decode_proto_map_entry."""

    def test_basic_entry(self) -> None:
        key_bytes = b"my_key"
        value_bytes = b"my_value"
        entry = _encode_length_delimited(1, key_bytes) + _encode_length_delimited(
            2, value_bytes
        )
        # Remove outer wrapper — entry_bytes is raw inner content
        key, value = _decode_proto_map_entry(entry)
        assert key == "my_key"
        assert value == b"my_value"


class TestDecodeCallable:
    """Test _decode_callable."""

    def test_basic_callable(self) -> None:
        uri_wrapper = _encode_string_wrapper("python://foo/bar()")
        # Wrap URI as field 1
        callable_bytes = _encode_length_delimited(1, uri_wrapper)
        result = _decode_callable(42, callable_bytes)
        assert result.method_id == 42
        assert result.uri == "python://foo/bar()"
        assert result.access == "UNSPECIFIED"


class TestDecodeCallsite:
    """Test _decode_callsite."""

    def test_basic_callsite(self) -> None:
        # Field 3 = call_type varint
        site_bytes = _encode_varint_field(3, 4)  # STATIC
        result = _decode_callsite(7, site_bytes)
        assert result.site_key == 7
        assert result.call_type == "STATIC"
        assert result.line is None


class TestDecodeCall:
    """Test _decode_call."""

    def test_basic_call(self) -> None:
        source_wrapper = _encode_int_wrapper(10)
        target_wrapper = _encode_int_wrapper(20)
        call_bytes = _encode_length_delimited(
            1, source_wrapper
        ) + _encode_length_delimited(2, target_wrapper)
        result = _decode_call(call_bytes)
        assert result.source_id == 10
        assert result.target_id == 20
        assert result.callsites == []


class TestDecodeTimestamp:
    """Test _decode_timestamp."""

    def test_valid_timestamp(self) -> None:
        ts_bytes = _encode_varint_field(1, 1700000000)  # seconds
        result = _decode_timestamp(ts_bytes)
        assert result is not None
        assert isinstance(result, datetime)
        assert result.tzinfo == UTC

    def test_zero_seconds(self) -> None:
        ts_bytes = _encode_varint_field(1, 0)
        result = _decode_timestamp(ts_bytes)
        assert result is None

    def test_with_nanos(self) -> None:
        ts_bytes = _encode_varint_field(1, 1700000000) + _encode_varint_field(
            2, 500_000_000
        )
        result = _decode_timestamp(ts_bytes)
        assert result is not None
        assert result.microsecond > 0


# ===================================================================
#  Section 4 — Rendering tests
# ===================================================================


class TestShortTypeKey:
    """Test _short_type_key helper."""

    def test_bracket_format(self) -> None:
        assert _short_type_key("/[python:module:app.py]/App") == "app.py/App"

    def test_plain_key(self) -> None:
        assert _short_type_key("some/key") == "some/key"

    def test_bracket_no_suffix(self) -> None:
        assert _short_type_key("/[python:module:utils.py]") == "utils.py"


class TestBuildCallTree:
    """Test _build_call_tree rendering."""

    def test_simple_tree(self) -> None:
        info = TestCallGraphInfo._make_info()
        tree = _build_call_tree(info)
        assert "main()" in tree
        assert "helper()" in tree

    def test_empty_types(self) -> None:
        info = CallGraphInfo(
            uuid="",
            namespace="",
            parent_uuid="",
            create_time_iso="",
            update_time_iso="",
            package_name="",
            proto_create_time=None,
            language="PYTHON",
            version="V7",
        )
        info.build_index()
        tree = _build_call_tree(info)
        assert "no call tree" in tree


class TestInferProfile:
    """Test _infer_profile."""

    def test_basic_profile(self) -> None:
        info = TestCallGraphInfo._make_info()
        profile = _infer_profile(info)
        # Language label is derived from info.language
        assert info.language in profile
        # Callable counts from fixture appear in the profile text
        total_first_party = sum(len(t.methods) for t in info.internal_types)
        total_third_party = sum(len(t.methods) for t in info.external_types)
        assert str(total_first_party) in profile
        assert str(total_third_party) in profile

    def test_detects_flask_pattern(self) -> None:
        external = TypeInfo(
            key="flask",
            access="PUBLIC",
            class_type="REGULAR",
            source_file="",
            methods=[],
        )
        info = CallGraphInfo(
            uuid="",
            namespace="",
            parent_uuid="",
            create_time_iso="",
            update_time_iso="",
            package_name="",
            proto_create_time=None,
            language="PYTHON",
            version="V7",
            external_types=[external],
        )
        info.build_index()
        profile = _infer_profile(info)
        # The type key "flask" surfaces in the dependencies line of the profile
        assert external.key in profile
        assert info.language in profile


class TestRenderCallgraphAnalysis:
    """Test render_callgraph_analysis full output."""

    def test_produces_markdown(self) -> None:
        info = TestCallGraphInfo._make_info()
        md = render_callgraph_analysis(info)
        headings = _parse_headings(md)
        # Top-level heading is H1 containing the analysis label
        assert headings and headings[0].startswith("Call Graph Analysis")
        # At least 6 distinct sections are rendered (H1 + 5+ H2/H3 sections)
        assert len(headings) >= 6
        # Callable names from the fixture appear in the output
        assert "main()" in md
        assert "helper()" in md
        # Package name from fixture appears in the document
        assert info.package_name in md


# ===================================================================
#  Section 5 — Utility helper tests
# ===================================================================


class TestWriteJson:
    """Test write_json file output."""

    def test_writes_json_file(self, tmp_path: Path) -> None:
        out = tmp_path / "sub" / "data.json"
        write_json(out, {"key": "value"})
        assert out.exists()
        data = json.loads(out.read_text(encoding="utf-8"))
        assert data["key"] == "value"


class TestExtractObjects:
    """Test extract_objects from API response."""

    def test_standard_response(self) -> None:
        resp = {"list": {"objects": [{"uuid": "1"}, {"uuid": "2"}]}}
        assert len(extract_objects(resp)) == 2

    def test_empty_response(self) -> None:
        assert extract_objects({"list": {"objects": []}}) == []

    def test_missing_list(self) -> None:
        assert extract_objects({}) == []

    def test_none_objects(self) -> None:
        assert extract_objects({"list": {"objects": None}}) == []


class TestParseDepName:
    """Test parse_dep_name splitting."""

    def test_npm_package(self) -> None:
        name, ver = parse_dep_name("npm://express@4.22.1")
        assert name == "npm://express"
        assert ver == "4.22.1"

    def test_scoped_npm(self) -> None:
        name, ver = parse_dep_name("npm://@types/node@20.0.0")
        assert name == "npm://@types/node"
        assert ver == "20.0.0"

    def test_no_version(self) -> None:
        name, ver = parse_dep_name("pypi://requests")
        assert name == "pypi://requests"
        assert ver == ""

    def test_trailing_slash_at(self) -> None:
        _name, ver = parse_dep_name("go://example.com/@v1")
        # @ right after / — no split
        assert ver == ""


# ===================================================================
#  Section 6 — BOM helper tests
# ===================================================================


class TestBomToSerializable:
    """Test _bom_to_serializable conversions."""

    def test_dict_passthrough(self) -> None:
        d: dict[str, Any] = {"a": 1}
        assert _bom_to_serializable(d) is d

    def test_model_dump(self) -> None:
        mock = MagicMock()
        mock.model_dump.return_value = {"b": 2}
        assert _bom_to_serializable(mock) == {"b": 2}

    def test_fallback_str(self) -> None:
        result = _bom_to_serializable(42)
        assert "raw" in result


class TestRetrieveBomFull:
    """Test retrieve_bom_full extraction."""

    def test_with_bom(self) -> None:
        pv = MagicMock()
        pv.spec.resolved_dependencies = {"deps": [1, 2]}
        result = retrieve_bom_full(pv)
        assert result == {"deps": [1, 2]}

    def test_no_spec(self) -> None:
        pv = MagicMock()
        pv.spec = None
        assert retrieve_bom_full(pv) == {}

    def test_no_bom(self) -> None:
        pv = MagicMock()
        pv.spec.resolved_dependencies = None
        assert retrieve_bom_full(pv) == {}


class TestNormalizeChildren:
    """Test _normalize_children utility."""

    def test_strings(self) -> None:
        assert _normalize_children(["a", "b"]) == ["a", "b"]

    def test_dicts(self) -> None:
        result = _normalize_children([{"name": "x"}, {"key": "y"}])
        assert result == ["x", "y"]

    def test_empty(self) -> None:
        assert _normalize_children([]) == []

    def test_mixed(self) -> None:
        result = _normalize_children(["a", {"name": "b"}, 42])
        assert result == ["a", "b", "42"]


class TestCountTransitiveChildren:
    """Test count_transitive_children BFS."""

    def test_simple_graph(self) -> None:
        graph = {"A": ["B", "C"], "B": ["D"], "C": [], "D": []}
        assert count_transitive_children(graph, "A") == 3

    def test_cycle_handling(self) -> None:
        graph = {"A": ["B"], "B": ["A"]}
        # BFS visits B (child of A) then A (child of B) — both are descendants
        assert count_transitive_children(graph, "A") == 2

    def test_missing_root(self) -> None:
        graph = {"A": ["B"]}
        assert count_transitive_children(graph, "X") == 0


class TestExtractDirectDeps:
    """Test extract_direct_deps from BOM graph."""

    def test_basic_graph(self) -> None:
        graph: dict[str, list[str]] = {
            "root@1.0": ["npm://a@1.0", "npm://b@2.0"],
            "npm://a@1.0": ["npm://c@3.0"],
            "npm://b@2.0": [],
            "npm://c@3.0": [],
        }
        result = extract_direct_deps(graph)
        names = [r[0] for r in result]
        assert "npm://a" in names
        assert "npm://b" in names
        assert len(result) == 2

    def test_empty_graph(self) -> None:
        assert extract_direct_deps({}) == []


class TestRenderSlimDependencies:
    """Test render_slim_dependencies transformation."""

    def test_basic_row(self) -> None:
        rows = [
            {
                "spec": {
                    "dependency_data": {
                        "package_name": "express",
                        "resolved_version": "4.22.1",
                        "direct": True,
                        "reachable": "DEPENDENCY_REACHABLE",
                        "ecosystem": "ECOSYSTEM_NPM",
                        "scope": "DEPENDENCY_SCOPE_RUNTIME",
                    }
                }
            }
        ]
        slim = render_slim_dependencies(rows)
        assert len(slim) == 1
        assert slim[0]["name"] == "express"
        assert slim[0]["version"] == "4.22.1"
        assert slim[0]["direct"] is True
        assert slim[0]["reachable"] is True
        assert slim[0]["ecosystem"] == "npm"
        assert slim[0]["scope"] == "runtime"

    def test_unreachable(self) -> None:
        rows = [
            {
                "spec": {
                    "dependency_data": {
                        "reachable": "DEPENDENCY_UNREACHABLE",
                    }
                }
            }
        ]
        slim = render_slim_dependencies(rows)
        assert slim[0]["reachable"] is False

    def test_unknown_reachability(self) -> None:
        rows = [{"spec": {"dependency_data": {}}}]
        slim = render_slim_dependencies(rows)
        assert slim[0]["reachable"] is None


# ===================================================================
#  Section 7 — Summarization tests
# ===================================================================


class TestSummarizeDepMetadata:
    """Test summarize_dep_metadata aggregation."""

    def test_basic_summary(self) -> None:
        rows = [
            {
                "spec": {
                    "dependency_data": {
                        "direct": True,
                        "reachable": "DEPENDENCY_REACHABLE",
                        "ecosystem": "ECOSYSTEM_NPM",
                        "scope": "RUNTIME",
                    }
                }
            },
            {
                "spec": {
                    "dependency_data": {
                        "direct": False,
                        "reachable": "DEPENDENCY_UNREACHABLE",
                        "ecosystem": "ECOSYSTEM_NPM",
                        "scope": "DEV",
                    }
                }
            },
            {
                "spec": {
                    "dependency_data": {
                        "direct": False,
                        "ecosystem": "ECOSYSTEM_PYPI",
                    }
                }
            },
        ]
        stats = summarize_dep_metadata(rows)
        assert stats["total"] == 3
        assert stats["direct"] == 1
        assert stats["transitive"] == 2
        assert stats["reachable"] == 1
        assert stats["unreachable"] == 1
        assert stats["unknown_reachability"] == 1
        assert stats["by_ecosystem"]["ECOSYSTEM_NPM"] == 2
        assert stats["by_ecosystem"]["ECOSYSTEM_PYPI"] == 1


class TestSummarizeCallGraph:
    """Test summarize_call_graph extraction."""

    def test_json_any_format(self) -> None:
        cg_data = {
            "uuid": "cg-1",
            "meta": {"name": "pkg", "parent_uuid": "pv-1"},
            "spec": {"any": {"types": [], "calls": []}},
        }
        summary = summarize_call_graph(cg_data)
        assert summary["uuid"] == "cg-1"
        assert summary["call_graph_format"] == "json (any)"

    def test_zstd_format(self) -> None:
        cg_data = {
            "uuid": "cg-2",
            "meta": {},
            "spec": {"zstd_bytes": "base64data"},
        }
        summary = summarize_call_graph(cg_data)
        assert summary["call_graph_format"] == "zstd_bytes (binary)"

    def test_empty_spec(self) -> None:
        cg_data = {"uuid": "cg-3"}
        summary = summarize_call_graph(cg_data)
        assert summary["uuid"] == "cg-3"


class TestCleanSourcePath:
    """Test _clean_source_path prefix stripping."""

    def test_with_tmp_prefix(self) -> None:
        path = "/tmp/endorctl/myproject/src/app.py"
        assert _clean_source_path(path) == "src/app.py"

    def test_no_prefix(self) -> None:
        assert _clean_source_path("src/app.py") == "src/app.py"


# ===================================================================
#  Section 8 — Markdown summary builder tests
# ===================================================================


class TestRenderPvSection:
    """Test _render_pv_section Markdown output."""

    def test_basic_pv(self) -> None:
        pv = PVResult(
            pv_name="pkg@1.0",
            pv_uuid="pv-1",
            pv_slug="pkg_1.0",
            graph_nodes=5,
            direct_deps=[
                ("npm://a", "1.0", 3),
                ("npm://b", "2.0", 0),
            ],
        )
        buf = StringIO()
        _render_pv_section(pv, "##", buf)
        md = buf.getvalue()
        headings = _parse_headings(md)
        # At least one section heading is rendered
        assert len(headings) >= 1
        # Dependency coordinates from fixture appear in output
        assert "npm://a" in md
        assert "npm://b" in md

    def test_pv_with_cg(self) -> None:
        pv = PVResult(
            pv_name="pkg",
            pv_uuid="pv-1",
            pv_slug="pkg",
            cg_available=True,
            cg_summary={"uuid": "cg-1", "call_graph_format": "json (any)"},
        )
        buf = StringIO()
        _render_pv_section(pv, "##", buf)
        md = buf.getvalue()
        # Call graph UUID from fixture surfaces in the section
        assert pv.cg_summary["uuid"] in md


class TestBuildDependencyCallgraphSummary:
    """Test build_dependency_callgraph_summary full output."""

    def test_single_pv(self) -> None:
        pv = PVResult(
            pv_name="my-pkg@1.0",
            pv_uuid="pv-1",
            pv_slug="my-pkg_1.0",
            graph_nodes=10,
            direct_deps=[("npm://a", "1.0", 5)],
        )
        result = ProjectResult(
            project_uuid="proj-1",
            project_name="https://github.com/org/repo",
            namespace="tenant.ns",
            slug="org_repo",
            out_dir="/tmp/out",
            pv_results=[pv],
        )
        md = build_dependency_callgraph_summary(result)
        headings = _parse_headings(md)
        # Data-derived identifiers appear in the summary
        assert pv.pv_name in md
        assert result.project_uuid in md
        # At least a top-level heading and one sub-section are rendered
        assert len(headings) >= 2

    def test_multi_pv(self) -> None:
        pvs = [
            PVResult(pv_name=f"pkg-{i}", pv_uuid=f"pv-{i}", pv_slug=f"pkg-{i}")
            for i in range(3)
        ]
        result = ProjectResult(
            project_uuid="proj-1",
            project_name="repo",
            namespace="ns",
            slug="repo",
            out_dir="/tmp/out",
            pv_results=pvs,
        )
        md = build_dependency_callgraph_summary(result)
        # All PV names appear and the count is reflected somewhere in the output
        assert all(pv.pv_name in md for pv in pvs)
        assert str(len(pvs)) in md

    def test_with_dep_metadata_stats(self) -> None:
        result = ProjectResult(
            project_uuid="proj-1",
            project_name="repo",
            namespace="ns",
            slug="repo",
            out_dir="/tmp/out",
            pv_results=[PVResult(pv_name="p", pv_uuid="u", pv_slug="p")],
            dep_metadata_stats={
                "total": 50,
                "direct": 10,
                "transitive": 40,
                "reachable": 5,
                "unreachable": 30,
                "unknown_reachability": 15,
                "by_ecosystem": {"ECOSYSTEM_NPM": 50},
                "by_scope": {},
            },
        )
        md = build_dependency_callgraph_summary(result)
        headings = _parse_headings(md)
        # Stats section adds at least one extra heading beyond the base
        assert len(headings) >= 2
        # The total count value from the stats dict appears in output
        assert str(result.dep_metadata_stats["total"]) in md


def test_retrieve_dep_metadata_full_prefers_project_namespace(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Project namespace is queried first; oss is not tried when tenant rows exist."""
    namespaces: list[str] = []

    def _fake_list(
        *,
        namespace: str,
        filter: str,
        max_pages: int | None = None,
        page_size: int = 500,
    ) -> list[Mock]:
        _ = filter
        _ = max_pages
        _ = page_size
        namespaces.append(namespace)
        if namespace == "tenant.child":
            row = Mock()
            row.model_dump = Mock(return_value={"uuid": "dm-1"})
            return [row]
        return []

    client = MagicMock()
    client.DependencyMetadata.list = Mock(side_effect=_fake_list)

    rows, source_ns, truncated = retrieve_dep_metadata_full(
        client,
        "tenant.child",
        "project-uuid",
    )

    assert source_ns == "tenant.child"
    assert len(rows) == 1
    assert truncated is False
    assert namespaces == ["tenant.child"]
