"""Unit tests for agent context export manifest building."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from endorlabs.tools.dependency_explorer import (
    ProjectResult,
    PVResult,
)
from scripts.agent_context.export_project_context import (
    build_context_manifest,
)
from scripts.agent_context.package_versions_index import (
    parse_uuid_list_csv,
    select_top_n_uuids_by_update_time,
)
from scripts.agent_context.resolve_project import (
    is_hex_project_id,
)


def test_is_hex_project_id() -> None:
    assert is_hex_project_id("6938f75002eb18a25138ce6f") is True
    assert is_hex_project_id("6938f75002eb18a25138ce6") is False
    assert is_hex_project_id("not-hex") is False


def test_build_context_manifest_minimal(tmp_path: Path) -> None:
    pvr = PVResult(
        pv_name="npm://app@1.0",
        pv_uuid="aa",
        pv_slug="app",
    )
    pr = ProjectResult(
        project_uuid="p1",
        project_name="https://github.com/o/r.git",
        namespace="t.ns",
        slug="o_r",
        out_dir=str(tmp_path),
        pv_results=[pvr],
        dep_metadata_count=0,
    )
    m = build_context_manifest(
        version=2,
        tenant="t",
        project_uuid="p1",
        project_name="r",
        project_namespace="t.ns",
        cli={"pv_limit": 3},
        warnings=["n1"],
        project_result=pr,
        out_dir=tmp_path,
        callgraph_sweep=None,
        inventory=None,
        selection=None,
        hydration=None,
    )
    assert m["version"] == 2
    assert m["subject"]["project_uuid"] == "p1"
    assert m["warnings"] == ["n1"]
    assert m["cli"]["pv_limit"] == 3
    assert m["artifacts"]["package_version_artifacts"][0]["pv_uuid"] == "aa"
    assert m["artifacts"]["callgraph_sweep"] is None
    assert m["artifacts"]["package_versions_index_json"] is None
    assert "inventory" not in m


def test_parse_uuid_list_csv() -> None:
    assert parse_uuid_list_csv("a, b") == ["a", "b"]
    assert parse_uuid_list_csv("x;y") == ["x", "y"]


def test_select_top_n_uuids_by_update_time() -> None:
    rows = [
        {"pv_uuid": "u1", "meta_update_time": "2020-01-01T00:00:00Z"},
        {"pv_uuid": "u2", "meta_update_time": "2021-01-01T00:00:00Z"},
        {"pv_uuid": "u3", "meta_update_time": "2019-01-01T00:00:00Z"},
    ]
    assert select_top_n_uuids_by_update_time(rows, 2) == ["u2", "u1"]
