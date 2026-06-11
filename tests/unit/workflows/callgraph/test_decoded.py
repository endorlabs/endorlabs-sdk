"""Unit tests for shared callgraph decoded payload shaping."""

from __future__ import annotations

from types import SimpleNamespace

from endorlabs.workflows.callgraph.decoded import decode_payload


def test_decode_payload_shapes_summary_callables_and_edges(monkeypatch) -> None:
    method_a = SimpleNamespace(
        method_id=2,
        uri="java://a$1/pkg.B.b()",
        access="PUBLIC",
        first_line=2,
        last_line=3,
        defined=True,
    )
    method_b = SimpleNamespace(
        method_id=1,
        uri="java://a$1/pkg.A.a()",
        access="PUBLIC",
        first_line=1,
        last_line=1,
        defined=True,
    )
    edge = SimpleNamespace(
        source_id=1,
        target_id=2,
        callsites=[
            SimpleNamespace(call_type="STATIC"),
            SimpleNamespace(call_type="STATIC"),
        ],
    )
    decoded = SimpleNamespace(
        uuid="cg-1",
        namespace="acme",
        parent_uuid="pv-1",
        package_name="java://a",
        language="JAVA",
        version="1.0.0",
        internal_types=[SimpleNamespace(methods=[method_a, method_b])],
        external_types=[],
        call_edges=[edge],
        callable_label=lambda i: {1: method_b.uri, 2: method_a.uri}[i],
    )
    monkeypatch.setattr(
        "endorlabs.workflows.callgraph.proto_decode.decode_callgraph",
        lambda _cg: decoded,
    )

    summary, callables, edges = decode_payload({"uuid": "cg-1", "zstd_bytes": "x"})
    assert summary["uuid"] == "cg-1"
    assert summary["total_callables"] == 2
    assert [row["method_id"] for row in callables] == [1, 2]
    assert edges[0]["source_uri"] == method_b.uri
    assert edges[0]["target_uri"] == method_a.uri
