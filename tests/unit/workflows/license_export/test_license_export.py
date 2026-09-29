"""Unit tests for dependency + license export helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from endorlabs.filters import main_context_filter
from endorlabs.workflows.license_export.cli import main as license_export_main
from endorlabs.workflows.license_export.inventory import (
    collect_dependency_inventory,
    dedupe_inventory_rows,
    flatten_dm_row,
)
from endorlabs.workflows.license_export.join import (
    JOIN_COLUMNS,
    join_row,
    write_joined_export,
)
from endorlabs.workflows.license_export.resolve import resolve_licenses
from endorlabs.workflows.license_export.spdx import (
    license_resolution_from_package_license,
    license_resolution_from_query,
    primary_spdx_from_query_licenses,
    single_spdx_consensus,
)


def test_main_context_importer_filter() -> None:
    filt = main_context_filter('spec.importer_data.project_uuid=="abc"')
    assert 'context.type=="CONTEXT_TYPE_MAIN"' in filt
    assert 'spec.importer_data.project_uuid=="abc"' in filt


def test_dedupe_inventory_rows() -> None:
    rows = [
        {"project_uuid": "p1", "package_version_uuid": "v1", "package_name": "a"},
        {"project_uuid": "p1", "package_version_uuid": "v1", "package_name": "a"},
        {"project_uuid": "p1", "package_version_uuid": "v2", "package_name": "b"},
        {"project_uuid": "p2", "package_version_uuid": "v1", "package_name": "a"},
    ]
    out = dedupe_inventory_rows(rows)
    assert len(out) == 3
    keys = {(r["project_uuid"], r["package_version_uuid"]) for r in out}
    assert keys == {("p1", "v1"), ("p1", "v2"), ("p2", "v1")}


def test_flatten_dm_row_skips_missing_pv() -> None:
    row = {
        "uuid": "dm1",
        "spec": {
            "dependency_data": {
                "package_name": "go://example",
                "direct": True,
            }
        },
    }
    assert (
        flatten_dm_row(
            row, namespace="example-tenant", project_uuid="p1", project_name="repo"
        )
        is None
    )


def test_flatten_dm_row_extracts_fields() -> None:
    row = {
        "uuid": "dm1",
        "spec": {
            "dependency_data": {
                "package_version_uuid": "pv1",
                "package_name": "npm://lodash",
                "purl": "pkg:npm/lodash@4.17.21",
                "ecosystem": "ECOSYSTEM_NPM",
                "direct": True,
                "reachable": "REACHABILITY_TYPE_REACHABLE",
                "scope": "DEPENDENCY_SCOPE_NORMAL",
                "public": True,
                "pinned": True,
                "internal": False,
                "vendored": False,
                "last_commit": "2026-01-02T03:04:05Z",
            }
        },
    }
    flat = flatten_dm_row(
        row,
        namespace="example-tenant.child",
        project_uuid="proj",
        project_name="https://github.com/org/repo.git",
    )
    assert flat is not None
    assert flat["package_version_uuid"] == "pv1"
    assert flat["purl"] == "pkg:npm/lodash@4.17.21"
    assert flat["ecosystem"] == "ECOSYSTEM_NPM"
    assert flat["direct"] is True


def _package_license(
    *,
    pm: list[str] | None = None,
    declared: list[str] | None = None,
    code: list[str] | None = None,
) -> dict[str, Any]:
    def entries(ids: list[str] | None) -> list[dict[str, str]]:
        return [{"spdx_id": i} for i in (ids or [])]

    return {
        "spec": {
            "package_manager_licenses": entries(pm),
            "declared_code_licenses": entries(declared),
            "code_licenses": entries(code),
        }
    }


def test_single_spdx_consensus_agrees() -> None:
    lic = _package_license(pm=["MIT"], declared=["MIT"], code=["MIT"])
    assert single_spdx_consensus(lic) == "MIT"
    resolved = license_resolution_from_package_license(lic)
    assert resolved is not None
    assert resolved["primary_spdx"] == "MIT"
    assert resolved["resolution"] == "package_license_consensus"


def test_single_spdx_consensus_rejects_multi_license_cluster() -> None:
    # Synthetic multi-license disagreement (not a customer coordinate).
    lic = _package_license(
        pm=["EPL-2.0"],
        declared=["GPL-2.0-only"],
        code=["GPL-2.0-only WITH Classpath-exception-2.0"],
    )
    assert single_spdx_consensus(lic) is None
    assert license_resolution_from_package_license(lic) is None


def test_primary_spdx_from_query_prefers_package_manager() -> None:
    licenses = [
        {"source": "code", "spdx_expr": "GPL-2.0-only", "selected": True},
        {"source": "package_manager", "spdx_expr": "EPL-2.0", "selected": True},
        {"source": "declared", "spdx_expr": "CDDL-1.1", "selected": True},
    ]
    primary, all_ids, flags = primary_spdx_from_query_licenses(licenses)
    assert primary == "EPL-2.0"
    assert "GPL-2.0-only" in all_ids
    assert flags["has_code"] is True
    assert flags["has_package_manager"] is True


def test_license_resolution_from_query_body() -> None:
    body = {
        "spec": {
            "licenses": [
                {"source": "declared", "spdx_expr": "Apache-2.0", "selected": True},
                {"source": "code", "spdx_expr": "MIT", "selected": False},
            ]
        }
    }
    resolved = license_resolution_from_query(body)
    assert resolved["primary_spdx"] == "Apache-2.0"
    assert resolved["all_spdx"] == "Apache-2.0"
    assert resolved["has_declared"] is True
    assert resolved["has_code"] is False


def test_join_row_and_csv_writer(tmp_path: Path) -> None:
    inv = tmp_path / "dependency_inventory.jsonl"
    cache = tmp_path / "license_cache.jsonl"
    inv.write_text(
        json.dumps(
            {
                "namespace": "example-tenant",
                "project_uuid": "p1",
                "project_name": "repo",
                "package_name": "npm://left-pad",
                "package_version_uuid": "pv1",
                "purl": "",
                "ecosystem": "ECOSYSTEM_NPM",
                "direct": True,
                "reachable": "",
                "scope": "",
                "public": True,
                "pinned": False,
                "internal": False,
                "vendored": False,
                "last_commit": "",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    cache.write_text(
        json.dumps(
            {
                "package_version_uuid": "pv1",
                "primary_spdx": "MIT",
                "all_spdx": "MIT",
                "source_count": 1,
                "has_declared": False,
                "has_code": False,
                "has_package_manager": True,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    out = tmp_path / "out.csv"
    result = write_joined_export(
        inventory_path=inv,
        cache_path=cache,
        output_path=out,
        export_format="csv",
    )
    assert result.ok
    assert result.row_count == 1
    text = out.read_text(encoding="utf-8")
    assert "primary_spdx" in text
    assert "MIT" in text
    header = text.splitlines()[0].split(",")
    assert header == list(JOIN_COLUMNS)


def test_join_row_empty_license() -> None:
    row = join_row(
        {
            "namespace": "example-tenant",
            "project_uuid": "p",
            "project_name": "n",
            "package_name": "pkg",
            "package_version_uuid": "pv",
        },
        None,
    )
    assert row["primary_spdx"] == ""
    assert row["source_count"] == 0


def test_resolve_licenses_consensus_skips_query(tmp_path: Path) -> None:
    """Resolve is Query-only at the export namespace (batch then per-PV)."""
    client = MagicMock()
    api = MagicMock()
    client._client = api

    def _post(path: str, json: dict | None = None, **_kwargs: Any) -> Any:
        del json
        resp = MagicMock()
        resp.status_code = 200
        resp.raise_for_status = MagicMock()
        if "batch-package-license-queries" in path:
            resp.json.return_value = {
                "spec": {
                    "queries": [
                        {
                            "spec": {
                                "package_version_uuid": "pv-a",
                                "licenses": [
                                    {
                                        "source": "package_manager",
                                        "spdx_expr": "BSD-3-Clause",
                                        "selected": True,
                                    }
                                ],
                            }
                        }
                    ]
                }
            }
        else:
            resp.json.return_value = {
                "spec": {
                    "package_version_uuid": "pv-a",
                    "licenses": [
                        {
                            "source": "package_manager",
                            "spdx_expr": "BSD-3-Clause",
                            "selected": True,
                        }
                    ],
                }
            }
        return resp

    api.post.side_effect = _post
    cache = tmp_path / "cache.jsonl"
    result = resolve_licenses(
        client,
        namespace="example-tenant",
        package_version_uuids=["pv-a"],
        cache_path=cache,
        max_workers=2,
        batch_size=10,
    )
    assert result.ok
    assert result.query_count == 1
    assert result.consensus_count == 0
    assert result.missing_count == 0
    cached = json.loads(cache.read_text(encoding="utf-8").strip())
    assert cached["primary_spdx"] == "BSD-3-Clause"
    assert cached["resolution"] == "package_license_query"


def test_resolve_licenses_queries_on_disagreement(tmp_path: Path) -> None:
    client = MagicMock()
    api = MagicMock()
    client._client = api

    def _post(path: str, json: dict | None = None, **_kwargs: Any) -> Any:
        del json
        resp = MagicMock()
        resp.status_code = 200
        resp.raise_for_status = MagicMock()
        if "batch-package-license-queries" in path:
            resp.json.return_value = {
                "spec": {
                    "queries": [
                        {
                            "spec": {
                                "package_version_uuid": "pv-b",
                                "licenses": [
                                    {
                                        "source": "package_manager",
                                        "spdx_expr": "EPL-2.0",
                                        "selected": True,
                                    }
                                ],
                            }
                        }
                    ]
                }
            }
        else:
            resp.json.return_value = {
                "spec": {
                    "package_version_uuid": "pv-b",
                    "licenses": [
                        {
                            "source": "package_manager",
                            "spdx_expr": "EPL-2.0",
                            "selected": True,
                        }
                    ],
                }
            }
        return resp

    api.post.side_effect = _post

    cache = tmp_path / "cache.jsonl"
    result = resolve_licenses(
        client,
        namespace="example-tenant",
        package_version_uuids=["pv-b"],
        cache_path=cache,
        max_workers=2,
        batch_size=10,
    )
    assert result.query_count == 1
    assert result.consensus_count == 0
    assert api.post.called
    cached = json.loads(cache.read_text(encoding="utf-8").strip())
    assert cached["primary_spdx"] == "EPL-2.0"
    assert cached["resolution"] == "package_license_query"


def test_create_package_license_query_treats_httpx_404_as_missing() -> None:
    """APIClient.post raises HTTPStatusError on 404 — must not become resolve errors."""
    import httpx

    from endorlabs.workflows.license_export.resolve import create_package_license_query

    client = MagicMock()
    api = MagicMock()
    client._client = api
    request = httpx.Request("POST", "https://api.endorlabs.com/v1/x")
    response = httpx.Response(404, request=request)
    api.post.side_effect = httpx.HTTPStatusError(
        "Client error '404 Not Found'",
        request=request,
        response=response,
    )
    assert (
        create_package_license_query(
            client, namespace="example-tenant", package_version_uuid="pv-missing"
        )
        is None
    )


def test_collect_inventory_parallel_writes(tmp_path: Path) -> None:
    client = MagicMock()
    project = MagicMock()
    project.uuid = "proj-1"
    project.tenant_meta = MagicMock()
    project.tenant_meta.namespace = "example-tenant.child"
    project.meta = MagicMock()
    project.meta.name = "https://github.com/org/repo.git"
    topo = MagicMock()
    topo.projects = [project]
    client.Query.Project.discover.return_value = topo
    client.DependencyMetadata.list.return_value = [
        {
            "uuid": "dm1",
            "spec": {
                "dependency_data": {
                    "package_version_uuid": "pv1",
                    "package_name": "npm://pkg",
                    "direct": True,
                    "ecosystem": "ECOSYSTEM_NPM",
                }
            },
        },
        {
            "uuid": "dm2",
            "spec": {
                "dependency_data": {
                    "package_version_uuid": "pv1",
                    "package_name": "npm://pkg",
                    "direct": True,
                    "ecosystem": "ECOSYSTEM_NPM",
                }
            },
        },
    ]
    result = collect_dependency_inventory(
        client,
        namespace="example-tenant.child",
        output_dir=tmp_path,
        max_workers=2,
    )
    assert result.ok
    assert result.row_count == 1
    assert Path(result.inventory_path).is_file()
    row = json.loads(Path(result.inventory_path).read_text(encoding="utf-8").strip())
    assert row["project_name"] == "https://github.com/org/repo.git"
    filt = client.DependencyMetadata.list.call_args.kwargs["filter"]
    assert "CONTEXT_TYPE_MAIN" in filt
    assert "proj-1" in filt
    # Child namespace shards keep traverse=False.
    assert client.DependencyMetadata.list.call_args.kwargs["traverse"] is False


def test_collect_inventory_root_hosted_uses_traverse(
    tmp_path: Path,
) -> None:
    """Tenant-root project shards must list with traverse to pass SDK guard."""
    client = MagicMock()
    project = MagicMock()
    project.uuid = "proj-root"
    project.tenant_meta = MagicMock()
    project.tenant_meta.namespace = "example-tenant"
    project.meta = MagicMock()
    project.meta.name = "https://github.com/org/root-repo.git"
    topo = MagicMock()
    topo.projects = [project]
    client.Query.Project.discover.return_value = topo
    client.DependencyMetadata.list.return_value = []
    result = collect_dependency_inventory(
        client,
        namespace="example-tenant",
        output_dir=tmp_path,
        max_workers=2,
    )
    assert result.status in {"success", "partial"}
    kwargs = client.DependencyMetadata.list.call_args.kwargs
    assert kwargs["namespace"] == "example-tenant"
    assert kwargs["traverse"] is True


def test_cli_requires_namespace(monkeypatch: Any) -> None:
    monkeypatch.delenv("ENDOR_NAMESPACE", raising=False)
    assert license_export_main(["run"]) == 2


def test_cli_help_exits_zero() -> None:
    with pytest.raises(SystemExit) as exc:
        license_export_main(["--help"])
    assert exc.value.code == 0


def test_compose_dm_list_filter_ands_extra() -> None:
    from endorlabs.workflows.license_export.inventory import compose_dm_list_filter

    base = compose_dm_list_filter("proj-1")
    assert "CONTEXT_TYPE_MAIN" in base
    assert 'project_uuid=="proj-1"' in base
    combined = compose_dm_list_filter("proj-1", "spec.dependency_data.direct==true")
    assert combined.startswith("(")
    assert ") and (" in combined
    assert "direct==true" in combined
    assert "CONTEXT_TYPE_MAIN" in combined


def test_project_name_from_meta_name() -> None:
    from endorlabs.workflows.license_export.inventory import project_name_from_project

    project = MagicMock()
    project.meta = MagicMock()
    project.meta.name = "https://github.com/org/repo.git"
    assert project_name_from_project(project) == "https://github.com/org/repo.git"
    project.meta.name = ""
    assert project_name_from_project(project) == ""


def test_collect_inventory_extra_filter_and_mask(tmp_path: Path) -> None:
    client = MagicMock()
    project = MagicMock()
    project.uuid = "proj-1"
    project.tenant_meta = MagicMock()
    project.tenant_meta.namespace = "example-tenant.child"
    project.meta = MagicMock()
    project.meta.name = "https://github.com/org/repo.git"
    topo = MagicMock()
    topo.projects = [project]
    client.Query.Project.discover.return_value = topo
    client.DependencyMetadata.list.return_value = []
    collect_dependency_inventory(
        client,
        namespace="example-tenant.child",
        output_dir=tmp_path,
        max_workers=2,
        extra_filter="spec.dependency_data.direct==true",
        mask="uuid,spec.dependency_data.package_version_uuid",
    )
    kwargs = client.DependencyMetadata.list.call_args.kwargs
    assert "direct==true" in kwargs["filter"]
    assert "CONTEXT_TYPE_MAIN" in kwargs["filter"]
    assert kwargs["mask"] == "uuid,spec.dependency_data.package_version_uuid"


def test_resolve_include_license_object(tmp_path: Path) -> None:
    client = MagicMock()
    api = MagicMock()
    client._client = api

    def _post(path: str, json: dict | None = None, **_kwargs: Any) -> Any:
        del json
        resp = MagicMock()
        resp.status_code = 200
        resp.raise_for_status = MagicMock()
        body = {
            "spec": {
                "package_version_uuid": "pv-obj",
                "licenses": [
                    {"source": "package_manager", "spdx_expr": "MIT", "selected": True}
                ],
            }
        }
        if "batch-package-license-queries" in path:
            resp.json.return_value = {"spec": {"queries": [body]}}
        else:
            resp.json.return_value = body
        return resp

    api.post.side_effect = _post
    cache = tmp_path / "cache.jsonl"
    objects = tmp_path / "license_objects.jsonl"
    result = resolve_licenses(
        client,
        namespace="example-tenant",
        package_version_uuids=["pv-obj"],
        cache_path=cache,
        max_workers=2,
        batch_size=10,
        include_license_object=True,
        objects_path=objects,
    )
    assert result.ok
    assert objects.is_file()
    obj = json.loads(objects.read_text(encoding="utf-8").strip())
    assert obj["package_version_uuid"] == "pv-obj"
    assert obj["source"] == "package_license_query"
    assert "license_object" in obj


def test_join_jsonl_embeds_license_object(tmp_path: Path) -> None:
    inv = tmp_path / "dependency_inventory.jsonl"
    cache = tmp_path / "license_cache.jsonl"
    objects = tmp_path / "license_objects.jsonl"
    inv.write_text(
        json.dumps(
            {
                "namespace": "example-tenant",
                "project_uuid": "p1",
                "project_name": "repo",
                "package_name": "npm://left-pad",
                "package_version_uuid": "pv1",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    cache.write_text(
        json.dumps(
            {
                "package_version_uuid": "pv1",
                "primary_spdx": "MIT",
                "all_spdx": "MIT",
                "source_count": 1,
                "has_declared": False,
                "has_code": False,
                "has_package_manager": True,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    objects.write_text(
        json.dumps(
            {
                "package_version_uuid": "pv1",
                "source": "package_license",
                "license_object": {"spec": {"package_manager_licenses": []}},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    out = tmp_path / "out.jsonl"
    result = write_joined_export(
        inventory_path=inv,
        cache_path=cache,
        output_path=out,
        export_format="jsonl",
        objects_path=objects,
        include_license_object=True,
    )
    assert result.ok
    row = json.loads(out.read_text(encoding="utf-8").strip())
    assert row["primary_spdx"] == "MIT"
    assert "license_object" in row


def test_build_export_summary_shape(tmp_path: Path) -> None:
    from endorlabs.workflows.license_export.summary import (
        build_export_summary,
        format_summary_line,
        write_export_summary,
    )

    summary = build_export_summary(
        namespaces=["example-tenant.child"],
        output_dir=tmp_path,
        export_format="csv",
        workers=4,
        elapsed_seconds=1.5,
        projects_total=10,
        projects_complete=9,
        projects_failed=1,
        inventory_rows=100,
        unique_pvs=80,
        join_rows=100,
        license_consensus=70,
        license_query=5,
        license_missing=5,
        license_with_primary_spdx=75,
        join_paths=[str(tmp_path / "out.csv")],
        license_cache_path=str(tmp_path / "license_cache.jsonl"),
        status="partial",
        message="ok",
    )
    assert summary["projects"]["failed"] == 1
    assert summary["license"]["with_primary_spdx"] == 75
    path = write_export_summary(tmp_path, summary)
    assert path.is_file()
    line = format_summary_line(summary)
    assert "inventory_rows=100" in line
    assert "license_spdx=75" in line


def test_cli_auth_kwargs_from_args() -> None:
    import argparse

    from endorlabs.workflows.common.cli_client import (
        add_client_auth_arguments,
        client_kwargs_from_args,
    )

    parser = argparse.ArgumentParser()
    add_client_auth_arguments(parser)
    args = parser.parse_args(
        [
            "--token",
            "tok",
            "--api-key",
            "k",
            "--api-secret",
            "s",
            "--api",
            "https://api.endorlabs.com",
        ]
    )
    kwargs = client_kwargs_from_args(args)
    assert kwargs == {
        "token": "tok",
        "key": "k",
        "secret": "s",
        "base_url": "https://api.endorlabs.com",
    }
