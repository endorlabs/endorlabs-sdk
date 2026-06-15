"""Unit tests for call-graph export workflow."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

from endorlabs.core.exceptions import NotFoundError
from endorlabs.resources.call_graph_data import CallGraphDecoded
from endorlabs.workflows.callgraph.export import run_callgraph_export


def test_run_callgraph_export_writes_manifests(tmp_path: Path) -> None:
    pv_ok = SimpleNamespace(
        uuid="pv1",
        meta=SimpleNamespace(name="pypi://pkg@sha"),
    )
    pv_missing = SimpleNamespace(
        uuid="pv2",
        meta=SimpleNamespace(name="pypi://pkg2@sha"),
    )
    decoded = CallGraphDecoded(
        summary={"uuid": "cg-1"},
        callables=[{"method_id": 1, "uri": "a"}],
        edges=[],
        envelope={"uuid": "cg-1", "meta": {"parent_uuid": "pv1"}},
    )
    client = MagicMock()
    client.PackageVersion.list_by_project.return_value = SimpleNamespace(
        values=[pv_missing, pv_ok]
    )

    def _decode(pv: object) -> CallGraphDecoded:
        if getattr(pv, "uuid", None) == "pv2":
            raise NotFoundError("missing")
        return decoded

    client.CallGraphData.decode.side_effect = _decode

    result = run_callgraph_export(
        project_uuid="proj1",
        out_dir=tmp_path,
        list_namespace="tenant.ns",
        max_pages=1,
        page_size=10,
        decode_zstd=True,
        client=client,
    )

    assert result["call_graph_exports_total"] == 1
    assert result["package_versions_total"] == 2
    export_manifest = tmp_path / "callgraph_export_manifest.json"
    assert export_manifest.is_file()
    assert not (tmp_path / "callgraph_sweep_manifest.json").exists()
    body = json.loads(export_manifest.read_text(encoding="utf-8"))
    assert len(body["exports"]) == 1
    assert body["exports"][0]["pv_uuid"] == "pv1"
    assert Path(body["exports"][0]["decoded_callables_file"]).is_file()
