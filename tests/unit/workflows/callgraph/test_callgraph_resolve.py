"""Unit tests for package-version call-graph resolution."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from endorlabs.core.exceptions import NotFoundError
from endorlabs.resources.call_graph_data import CallGraphDecoded
from endorlabs.workflows.callgraph.manifest import resolve_callgraph_export_artifact
from endorlabs.workflows.callgraph.resolve import (
    build_callgraph_pv_inventory,
    order_pvs_for_callgraph,
    pv_call_graph_available,
    resolve_package_version_with_callgraph,
)


def _pv(
    uuid: str,
    *,
    ref: str | None,
    call_graph_available: bool,
) -> SimpleNamespace:
    return SimpleNamespace(
        uuid=uuid,
        meta=SimpleNamespace(name=f"pkg@{uuid}"),
        spec=SimpleNamespace(
            call_graph_available=call_graph_available,
            source_code_reference=SimpleNamespace(
                ref=ref,
                sha="abc",
                version=None,
            ),
        ),
    )


def test_pv_call_graph_available() -> None:
    assert pv_call_graph_available(_pv("a", ref="main", call_graph_available=True))
    assert not pv_call_graph_available(_pv("b", ref="main", call_graph_available=False))


def test_order_pvs_for_callgraph_prefers_main_then_other_refs() -> None:
    feature = _pv("f", ref="refs/heads/feature/x", call_graph_available=True)
    main = _pv("m", ref="refs/heads/main", call_graph_available=True)
    develop = _pv("d", ref="refs/heads/develop", call_graph_available=True)
    no_cg = _pv("n", ref="refs/heads/main", call_graph_available=False)

    ordered = order_pvs_for_callgraph([feature, no_cg, develop, main])
    assert [pv.uuid for pv in ordered] == ["m", "d", "f"]


def test_build_callgraph_pv_inventory_no_available_logs_refs() -> None:
    project = SimpleNamespace(uuid="proj1", meta=SimpleNamespace(name="repo"))
    pvs = [
        _pv("a", ref="refs/heads/feature", call_graph_available=False),
        _pv("b", ref="refs/heads/main", call_graph_available=False),
    ]
    inv = build_callgraph_pv_inventory(project, pvs, namespace="tenant.ns")
    assert inv["call_graph_available_count"] == 0
    assert inv["package_versions_listed"] == 2
    assert "call_graph_available=true" in inv["message"]
    assert "refs/heads/main" in inv["message"]


def test_resolve_package_version_with_callgraph_skips_not_found() -> None:
    pv1 = _pv("pv1", ref="refs/heads/main", call_graph_available=True)
    pv2 = _pv("pv2", ref="refs/heads/develop", call_graph_available=True)
    decoded = CallGraphDecoded(
        summary={},
        callables=[{"method_id": 1, "uri": "a"}],
        edges=[],
        envelope={},
    )
    client = MagicMock()
    client.PackageVersion.list_by_project.return_value = SimpleNamespace(
        values=[pv1, pv2]
    )

    def _decode(pv: object) -> CallGraphDecoded:
        if getattr(pv, "uuid", None) == "pv1":
            raise NotFoundError("missing")
        return decoded

    client.CallGraphData.decode.side_effect = _decode
    project = SimpleNamespace(uuid="proj")

    out = resolve_package_version_with_callgraph(
        client, project, namespace="ns", max_pages=1, page_size=10
    )
    assert out is not None
    pv, dec = out
    assert pv.uuid == "pv2"
    assert dec is decoded


def test_resolve_package_version_with_callgraph_no_available_returns_none() -> None:
    client = MagicMock()
    client.PackageVersion.list_by_project.return_value = SimpleNamespace(
        values=[_pv("x", ref="main", call_graph_available=False)]
    )
    project = SimpleNamespace(uuid="proj", meta=SimpleNamespace(name="r"))
    inventory: dict = {}
    out = resolve_package_version_with_callgraph(
        client,
        project,
        namespace="ns",
        max_pages=1,
        page_size=10,
        inventory_out=inventory,
    )
    assert out is None
    assert inventory["call_graph_available_count"] == 0
    assert "call_graph_available=true" in inventory["message"]


def test_resolve_callgraph_export_artifact() -> None:
    export = {"pass": "callgraph_export_pass_3"}
    assert resolve_callgraph_export_artifact({"callgraph_export": export}) == export
    assert resolve_callgraph_export_artifact({}) is None
    assert resolve_callgraph_export_artifact(None) is None
