"""Unit tests for agent context export manifest building."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

from endorlabs.workflows.agent_context import export as export_mod
from endorlabs.workflows.agent_context.export import build_context_manifest, parse_args
from endorlabs.workflows.agent_context.hydration import ProjectResult, PVResult
from endorlabs.workflows.agent_context.package_versions import (
    _iso_timestamp,
    build_index_rows,
    index_row_from_pv,
    list_package_versions_for_index,
    parse_uuid_list_csv,
    select_top_n_uuids_by_update_time,
    source_ref_sha_from_pv,
)
from endorlabs.workflows.agent_context.session_artifacts import (
    FindingsContext,
    PoliciesContext,
    SessionResult,
    VersionsContext,
)
from endorlabs.workflows.projects.resolve import is_hex_project_id


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


def test_build_context_manifest_includes_optional_blocks(tmp_path: Path) -> None:
    pr = ProjectResult(
        project_uuid="p1",
        project_name="proj",
        namespace="t.ns",
        slug="proj",
        out_dir=str(tmp_path),
        dep_metadata_count=4,
        dep_metadata_namespace="t.ns",
    )
    m = build_context_manifest(
        version=2,
        tenant="t",
        project_uuid="p1",
        project_name="proj",
        project_namespace="t.ns",
        cli={"pv_limit": 1, "dep_metadata_max_pages": 2},
        warnings=[],
        project_result=pr,
        out_dir=tmp_path,
        callgraph_sweep={"package_versions_total": 5},
        inventory={"enabled": True},
        selection={"mode": "explicit"},
        hydration={"pass_2_dependency_explorer": {"skipped": False}},
    )
    assert m["inventory"]["enabled"] is True
    assert m["selection"]["mode"] == "explicit"
    assert m["hydration"]["pass_2_dependency_explorer"]["skipped"] is False
    assert m["artifacts"]["dep_metadata_list_namespace"] == "t.ns"
    assert m["artifacts"]["dep_metadata_row_count"] == 4
    assert m["artifacts"]["callgraph_sweep"]["package_versions_total"] == 5


def test_build_context_manifest_includes_session_summaries(tmp_path: Path) -> None:
    pr = ProjectResult(
        project_uuid="p1",
        project_name="proj",
        namespace="t.ns",
        slug="proj",
        out_dir=str(tmp_path),
    )
    session_root = tmp_path / "proj__p1"
    m = build_context_manifest(
        version=2,
        tenant="t",
        project_uuid="p1",
        project_name="proj",
        project_namespace="t.ns",
        cli={"session_summaries": True},
        warnings=[],
        project_result=pr,
        out_dir=tmp_path,
        callgraph_sweep=None,
        inventory=None,
        selection=None,
        hydration=None,
        session_artifacts={
            "enabled": True,
            "session_dir": str(session_root),
            "project_summary_md": str(session_root / "project-summary.md"),
            "findings_total": 3,
        },
    )
    assert m["artifacts"]["session_summaries"]["findings_total"] == 3


def test_source_ref_sha_from_pv_version_fallback() -> None:
    pv = SimpleNamespace(
        spec=SimpleNamespace(
            source_code_reference=SimpleNamespace(
                ref=None,
                sha=None,
                version=SimpleNamespace(ref="refs/heads/main", sha="abc123"),
            )
        )
    )
    ref, sha = source_ref_sha_from_pv(pv)
    assert ref == "refs/heads/main"
    assert sha == "abc123"


def test_index_row_from_pv_serializes_metadata() -> None:
    pv = SimpleNamespace(
        uuid="pv1",
        meta=SimpleNamespace(
            name="npm://pkg@1.2.3",
            create_time="2024-01-01T00:00:00Z",
            update_time="2024-01-02T00:00:00Z",
            upsert_time="2024-01-03T00:00:00Z",
        ),
        spec=SimpleNamespace(
            ecosystem="ECOSYSTEM_NPM",
            language="LANGUAGE_JAVASCRIPT",
            package_name="npm://pkg",
            relative_path="src",
            call_graph_available=True,
            precomputed_call_graph_state=SimpleNamespace(
                model_dump=lambda **_: {"status": "READY"}
            ),
            source_code_reference=SimpleNamespace(ref="r", sha="s", version=None),
        ),
    )
    row = index_row_from_pv(pv, project_uuid="p1", namespace="t.ns")
    assert row["pv_uuid"] == "pv1"
    assert row["project_uuid"] == "p1"
    assert row["namespace"] == "t.ns"
    assert row["precomputed_call_graph_state"] == {"status": "READY"}
    assert row["source_ref"] == "r"
    assert row["source_sha"] == "s"


def test_build_index_rows_maps_all_entries() -> None:
    pvs = [
        SimpleNamespace(uuid="a", meta=SimpleNamespace(name="npm://a@1"), spec=None),
        SimpleNamespace(uuid="b", meta=SimpleNamespace(name="npm://b@1"), spec=None),
    ]
    rows = build_index_rows(pvs, project_uuid="p1", namespace="n1")
    assert [r["pv_uuid"] for r in rows] == ["a", "b"]
    assert all(r["project_uuid"] == "p1" for r in rows)


def test_list_package_versions_for_index_truncated_and_sorted() -> None:
    class FakeClient:
        class PackageVersion:
            @staticmethod
            def list(**_kwargs):
                return [
                    SimpleNamespace(
                        uuid="2",
                        meta=SimpleNamespace(name="npm://z@1"),
                        spec=None,
                    ),
                    SimpleNamespace(
                        uuid="1",
                        meta=SimpleNamespace(name="npm://a@1"),
                        spec=None,
                    ),
                ]

    with patch("endorlabs.workflows.agent_context.package_versions.LOGGER.warning"):
        pvs, meta = list_package_versions_for_index(
            FakeClient(),
            namespace="n1",
            project_uuid="p1",
            max_pages=1,
            page_size=2,
            deterministic=True,
        )
    assert [pv.uuid for pv in pvs] == ["1", "2"]
    assert meta["truncated"] is True
    assert meta["capacity_rows"] == 2
    assert meta["coverage_mode"] == "truncated_at_capacity"


def test_parse_args_defaults(monkeypatch) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "prog",
            "--tenant",
            "t",
            "--project",
            "p",
        ],
    )
    args = parse_args()
    assert isinstance(args, argparse.Namespace)
    assert args.pv_limit == 5
    assert args.pv_index is True
    assert args.callgraph_sweep is False
    assert args.decode_zstd is False


def test_main_rejects_index_only_with_top_n() -> None:
    args = SimpleNamespace(
        tenant="t",
        namespace="",
        project="p",
        output_dir=".tmp",
        pv_limit=5,
        dep_metadata_max_pages=10,
        deterministic=False,
        pv_index=True,
        pv_index_max_pages=50,
        pv_index_page_size=200,
        index_only=True,
        hydrate_pv_uuids="",
        hydrate_top_n=1,
        pv_list_max_pages=50,
        pv_list_page_size=200,
        callgraph_sweep=False,
        callgraph_max_pages=50,
        callgraph_page_size=200,
        decode_zstd=False,
        session_summaries=False,
    )
    with patch.object(export_mod, "parse_args", return_value=args):
        assert export_mod.main() == 2


def test_main_rejects_index_only_with_hydrate_uuids() -> None:
    args = SimpleNamespace(
        tenant="t",
        namespace="",
        project="p",
        output_dir=".tmp",
        pv_limit=5,
        dep_metadata_max_pages=10,
        deterministic=False,
        pv_index=True,
        pv_index_max_pages=50,
        pv_index_page_size=200,
        index_only=True,
        hydrate_pv_uuids="abc",
        hydrate_top_n=0,
        pv_list_max_pages=50,
        pv_list_page_size=200,
        callgraph_sweep=False,
        callgraph_max_pages=50,
        callgraph_page_size=200,
        decode_zstd=False,
        session_summaries=False,
    )
    with patch.object(export_mod, "parse_args", return_value=args):
        assert export_mod.main() == 2


def test_main_rejects_top_n_without_index() -> None:
    args = SimpleNamespace(
        tenant="t",
        namespace="",
        project="p",
        output_dir=".tmp",
        pv_limit=5,
        dep_metadata_max_pages=10,
        deterministic=False,
        pv_index=False,
        pv_index_max_pages=50,
        pv_index_page_size=200,
        index_only=False,
        hydrate_pv_uuids="",
        hydrate_top_n=3,
        pv_list_max_pages=50,
        pv_list_page_size=200,
        callgraph_sweep=False,
        callgraph_max_pages=50,
        callgraph_page_size=200,
        decode_zstd=False,
        session_summaries=False,
    )
    with patch.object(export_mod, "parse_args", return_value=args):
        assert export_mod.main() == 2


def test_iso_timestamp_handles_isoformat_errors() -> None:
    class BadTime:
        def isoformat(self):
            raise ValueError("bad")

    assert _iso_timestamp(BadTime()) is None
    assert _iso_timestamp(123) == "123"


def test_source_ref_sha_from_pv_missing_spec_or_scr() -> None:
    assert source_ref_sha_from_pv(SimpleNamespace(spec=None)) == (None, None)
    assert source_ref_sha_from_pv(
        SimpleNamespace(spec=SimpleNamespace(source_code_reference=None))
    ) == (None, None)


def test_index_row_from_pv_stringifies_non_dict_pcg_state() -> None:
    pv = SimpleNamespace(
        uuid="pvx",
        meta=SimpleNamespace(
            name="", create_time=None, update_time=None, upsert_time=None
        ),
        spec=SimpleNamespace(
            ecosystem=None,
            language=None,
            package_name=None,
            relative_path=None,
            call_graph_available=None,
            precomputed_call_graph_state=object(),
            source_code_reference=None,
        ),
    )
    row = index_row_from_pv(pv, project_uuid="p1", namespace="n1")
    assert row["pv_name"] == "pvx"
    assert isinstance(row["precomputed_call_graph_state"], str)


def test_main_index_only_success_flow(tmp_path: Path) -> None:
    args = SimpleNamespace(
        tenant="root",
        namespace="root.ns",
        project="proj-name",
        output_dir=str(tmp_path),
        pv_limit=5,
        dep_metadata_max_pages=10,
        deterministic=False,
        pv_index=False,
        pv_index_max_pages=1,
        pv_index_page_size=1,
        index_only=True,
        hydrate_pv_uuids="",
        hydrate_top_n=0,
        pv_list_max_pages=1,
        pv_list_page_size=1,
        callgraph_sweep=False,
        callgraph_max_pages=1,
        callgraph_page_size=1,
        decode_zstd=False,
        session_summaries=False,
    )
    proj = SimpleNamespace(
        uuid="p1",
        meta=SimpleNamespace(name="repo"),
        tenant_meta=SimpleNamespace(namespace="root.ns"),
    )
    fake_client = SimpleNamespace(_client=object(), close=lambda: None)

    with (
        patch.object(export_mod, "parse_args", return_value=args),
        patch(
            "endorlabs.workflows.agent_context.export.endorlabs.Client",
            return_value=fake_client,
        ),
        patch(
            "endorlabs.workflows.agent_context.export.resolve_project",
            return_value=proj,
        ),
        patch("endorlabs.workflows.agent_context.export.slugify", return_value="repo"),
        patch("endorlabs.workflows.agent_context.export.write_json"),
        patch("endorlabs.workflows.agent_context.export._write_text"),
        patch("endorlabs.workflows.agent_context.export.print"),
    ):
        assert export_mod.main() == 0


def test_main_session_summaries_writes_manifest_pointers(tmp_path: Path) -> None:
    args = SimpleNamespace(
        tenant="root",
        namespace="root.ns",
        project="proj-name",
        output_dir=str(tmp_path),
        pv_limit=5,
        dep_metadata_max_pages=10,
        deterministic=False,
        pv_index=False,
        pv_index_max_pages=1,
        pv_index_page_size=1,
        index_only=True,
        hydrate_pv_uuids="",
        hydrate_top_n=0,
        pv_list_max_pages=1,
        pv_list_page_size=1,
        callgraph_sweep=False,
        callgraph_max_pages=1,
        callgraph_page_size=1,
        decode_zstd=False,
        session_summaries=True,
    )
    proj = SimpleNamespace(
        uuid="p1",
        meta=SimpleNamespace(name="repo"),
        tenant_meta=SimpleNamespace(namespace="root.ns"),
    )
    fake_client = SimpleNamespace(_client=object(), close=lambda: None)
    session_result = SessionResult(
        session_dir=str(tmp_path),
        status="success",
        findings=FindingsContext(total=2),
        policies=PoliciesContext(total=1),
        versions=VersionsContext(total=4),
    )
    manifest_payload: dict[str, Any] = {}

    def _capture_manifest(_path: str, payload: dict[str, Any], **_: object) -> None:
        manifest_payload.update(payload)

    with (
        patch.object(export_mod, "parse_args", return_value=args),
        patch(
            "endorlabs.workflows.agent_context.export.endorlabs.Client",
            return_value=fake_client,
        ),
        patch(
            "endorlabs.workflows.agent_context.export.resolve_project",
            return_value=proj,
        ),
        patch(
            "endorlabs.workflows.agent_context.export.create_session",
            return_value=session_result,
        ) as mock_create_session,
        patch(
            "endorlabs.workflows.agent_context.export.build_project_session_key",
            return_value="repo__p1",
        ),
        patch("endorlabs.workflows.agent_context.export.slugify", return_value="repo"),
        patch(
            "endorlabs.workflows.agent_context.export.write_json",
            side_effect=_capture_manifest,
        ),
        patch("endorlabs.workflows.agent_context.export._write_text"),
        patch("endorlabs.workflows.agent_context.export.print"),
    ):
        assert export_mod.main() == 0

    mock_create_session.assert_called_once()
    session_block = manifest_payload["artifacts"]["session_summaries"]
    assert session_block["enabled"] is True
    assert session_block["findings_total"] == 2
    assert session_block["policies_total"] == 1
    assert session_block["versions_total"] == 4
    assert session_block["project_summary_md"].endswith("project-summary.md")
