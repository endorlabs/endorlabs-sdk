"""Unit tests for AI-SAST → Call Graph join glue and prechecks."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from endorlabs.core.exceptions import NotFoundError
from endorlabs.workflows.aisast_callgraph.join import (
    clamp_walk_bounds,
    match_seeds_to_callables,
    patterns_from_seed,
    walk_from_matches,
)
from endorlabs.workflows.aisast_callgraph.precheck import (
    GATE_CG,
    GATE_RV,
    GATE_VECTOR,
    precheck_aisast_and_callgraph,
)
from endorlabs.workflows.aisast_callgraph.run import run_aisast_callgraph_bridge
from endorlabs.workflows.aisast_callgraph.seeds import parse_vector_match
from endorlabs.workflows.aisast_callgraph.targets import (
    is_vuln_id_shaped,
    package_token_from_coordinate,
    path_patterns_for_package,
    resolve_vuln_walk_targets,
)


def test_patterns_from_seed_routes_login() -> None:
    pats = patterns_from_seed(
        {
            "file_path": "juice-shop/routes/login.ts",
            "fqn": "login.login",
            "rest_path": "/rest/user/login",
        }
    )
    assert pats[0] == "routes/login"
    assert "rest_path" not in "".join(pats)
    assert "/rest/user/login" not in pats


def test_patterns_from_seed_stem_and_fqn() -> None:
    pats = patterns_from_seed(
        {
            "file_path": "frontend/src/app/about/about.component.ts",
            "fqn": "AboutComponent.ngOnInit",
        }
    )
    assert pats[0] == "about/about.component"
    assert "ngOnInit" in pats


def test_parse_vector_match_nested_function_info() -> None:
    seed = parse_vector_match(
        {
            "data": "Summary: handles login",
            "score": 0.9,
            "metadata": {
                "fqn": "routes.login",
                "file_path": "routes/login.ts",
                "line_start": 10,
                "function_info": {
                    "is_entry_point": True,
                    "rest_path": "/api/login",
                    "is_source": True,
                },
            },
        }
    )
    assert seed["is_entry_point"] is True
    assert seed["rest_path"] == "/api/login"
    assert seed["fqn"] == "routes.login"


def test_match_seeds_to_callables() -> None:
    callables = [
        {"method_id": 1, "uri": "javascript://pkg/[pkg:1:routes/login]::login()"},
        {"method_id": 2, "uri": "javascript://pkg/[pkg:1:lib/other]::x()"},
    ]
    seeds = [{"file_path": "src/routes/login.ts", "fqn": "login"}]
    rows = match_seeds_to_callables(seeds, callables)
    assert rows[0]["match_count"] == 1
    assert "routes/login" in rows[0]["matched_uris"][0]


def test_walk_from_matches_optional() -> None:
    callables = [
        {"method_id": 1, "uri": "app/routes/login::login()"},
        {"method_id": 2, "uri": "jsonwebtoken/index::sign()"},
    ]
    edges = [
        {
            "source_id": 1,
            "target_id": 2,
            "source_uri": callables[0]["uri"],
            "target_uri": callables[1]["uri"],
        }
    ]
    matches = match_seeds_to_callables(
        [{"file_path": "routes/login.ts", "fqn": "login"}],
        callables,
    )
    walks = walk_from_matches(
        callables,
        edges,
        matches,
        path_to=["jsonwebtoken", "sign"],
        max_depth=4,
    )
    assert walks[0]["path_found"] is True
    assert walks[0]["cg_path_is_not_finding_reachability"] is True


def test_package_token_from_coordinate() -> None:
    assert package_token_from_coordinate("npm://jsonwebtoken@0.4.0") == "jsonwebtoken"
    assert (
        package_token_from_coordinate("maven://org.apache:log4j-core@2.14.1")
        == "log4j-core"
    )
    assert package_token_from_coordinate("GHSA-aaaa-bbbb-cccc") is None


def test_path_patterns_reject_vuln_ids() -> None:
    assert is_vuln_id_shaped("GHSA-aaaa-bbbb-cccc")
    assert is_vuln_id_shaped("CVE-2021-44228")
    assert path_patterns_for_package("GHSA-aaaa-bbbb-cccc") == []
    assert path_patterns_for_package("jsonwebtoken", symbol="sign") == [
        "jsonwebtoken",
        "sign",
    ]


def test_walk_rejects_vuln_id_only_path_to() -> None:
    walks = walk_from_matches(
        [{"method_id": 1, "uri": "routes/login::login()"}],
        [],
        [
            {
                "seed": {"file_path": "routes/login.ts"},
                "path_from_patterns": ["routes/login"],
                "match_count": 1,
            }
        ],
        path_to=["GHSA-aaaa-bbbb-cccc"],
    )
    assert walks[0]["skipped"] == "path_to_was_vuln_id_only"
    assert walks[0]["path_found"] is False


def test_walk_skips_missing_target() -> None:
    callables = [{"method_id": 1, "uri": "app/routes/login::login()"}]
    matches = match_seeds_to_callables(
        [{"file_path": "routes/login.ts", "fqn": "login"}],
        callables,
    )
    walks = walk_from_matches(
        callables,
        [],
        matches,
        path_to=["jsonwebtoken"],
    )
    assert walks[0]["skipped"] == "target_not_in_callgraph"


def test_clamp_walk_bounds() -> None:
    depth, paths, sources = clamp_walk_bounds(
        max_depth=99, max_paths=99, max_source_ids=5
    )
    assert depth == 12
    assert paths == 20
    assert sources == 5


def test_resolve_vuln_walk_targets_from_findings() -> None:
    finding = SimpleNamespace(
        uuid="f1",
        meta=SimpleNamespace(name="dependency_with_critical_vulnerabilities"),
        spec=SimpleNamespace(
            extra_key="GHSA-aaaa-bbbb-cccc",
            target_dependency_package_name="npm://jsonwebtoken@0.4.0",
            finding_tags=["FINDING_TAGS_REACHABLE_FUNCTION"],
            level="FINDING_LEVEL_CRITICAL",
        ),
    )

    def _list_findings(*_a: Any, **_k: Any) -> list[Any]:
        return [finding]

    client = SimpleNamespace(
        Finding=SimpleNamespace(list_by_project=_list_findings),
    )
    targets = resolve_vuln_walk_targets(
        client,
        SimpleNamespace(uuid="proj1"),
        namespace="example-tenant",
        vuln_id="GHSA-aaaa-bbbb-cccc",
        symbol="sign",
    )
    assert len(targets) == 1
    assert targets[0].package_token == "jsonwebtoken"
    assert targets[0].path_to_patterns == ["jsonwebtoken", "sign"]
    assert "GHSA" not in "".join(targets[0].path_to_patterns)
    assert targets[0].as_dict()["cg_path_is_not_finding_reachability"] is True


def _fake_rv(status: str) -> SimpleNamespace:
    return SimpleNamespace(spec=SimpleNamespace(aisast_status=status))


def _fake_pv(uuid: str, *, cg: bool = True) -> SimpleNamespace:
    return SimpleNamespace(
        uuid=uuid,
        meta=SimpleNamespace(name=f"npm://app@{uuid}"),
        spec=SimpleNamespace(call_graph_available=cg),
    )


def _fake_store() -> SimpleNamespace:
    return SimpleNamespace(
        uuid="store-1",
        namespace="example-tenant",
        meta=SimpleNamespace(name="function_summary"),
    )


def _fake_decoded() -> SimpleNamespace:
    return SimpleNamespace(
        callables=[{"method_id": 1, "uri": "routes/login::login()"}],
        edges=[],
    )


def _make_client(
    *,
    versions: list[Any],
    stores: list[Any],
    pvs: list[Any],
    decode_ok: bool = True,
    probe_hits: int = 1,
) -> SimpleNamespace:
    def _list_rv(**_kwargs: Any) -> list[Any]:
        return list(versions)

    def _list_pv(_project: Any, **_kwargs: Any) -> list[Any]:
        return list(pvs)

    def _list_vs(**_kwargs: Any) -> list[Any]:
        return list(stores)

    def _vs_query(**kwargs: Any) -> Any:
        matches: list[dict[str, Any]] = (
            [
                {
                    "data": "fn",
                    "metadata": {
                        "repo": kwargs.get("metadata_filter", {}).get("repo"),
                        "file_path": "routes/login.ts",
                        "fqn": "login",
                        "function_info": {"is_entry_point": True},
                    },
                }
            ]
            if probe_hits
            else []
        )
        return SimpleNamespace(spec=SimpleNamespace(matches=matches))

    def _decode(_pv: Any) -> Any:
        if not decode_ok:
            raise NotFoundError("missing")
        return _fake_decoded()

    return SimpleNamespace(
        RepositoryVersion=SimpleNamespace(list=_list_rv),
        PackageVersion=SimpleNamespace(list_by_project=_list_pv),
        VectorStore=SimpleNamespace(list=_list_vs),
        VectorStoreQuery=SimpleNamespace(create=_vs_query),
        CallGraphData=SimpleNamespace(decode=_decode),
    )


def test_precheck_fails_without_main_aisast_success() -> None:
    project = SimpleNamespace(
        uuid="proj1",
        meta=SimpleNamespace(name="https://github.com/org/repo.git"),
        tenant_meta=SimpleNamespace(namespace="example-tenant"),
    )
    client = _make_client(
        versions=[_fake_rv("PENDING")],
        stores=[_fake_store()],
        pvs=[_fake_pv("pv1")],
    )
    pre = precheck_aisast_and_callgraph(
        client,
        project,
        tenant_root="example-tenant",
        namespace="example-tenant",
    )
    assert pre.ok is False
    assert GATE_RV in pre.failed_gate_ids()


def test_precheck_fails_without_vector_index() -> None:
    project = SimpleNamespace(
        uuid="proj1",
        meta=SimpleNamespace(name="https://github.com/org/repo.git"),
        tenant_meta=SimpleNamespace(namespace="example-tenant"),
    )
    client = _make_client(
        versions=[_fake_rv("SCAN_OBJECT_AISAST_STATUS_SUCCESS")],
        stores=[_fake_store()],
        pvs=[_fake_pv("pv1")],
        probe_hits=0,
    )
    pre = precheck_aisast_and_callgraph(
        client,
        project,
        tenant_root="example-tenant",
        namespace="example-tenant",
    )
    assert pre.ok is False
    assert GATE_VECTOR in pre.failed_gate_ids()


def test_precheck_fails_without_cg_pv() -> None:
    project = SimpleNamespace(
        uuid="proj1",
        meta=SimpleNamespace(name="https://github.com/org/repo.git"),
        tenant_meta=SimpleNamespace(namespace="example-tenant"),
    )
    client = _make_client(
        versions=[_fake_rv("SUCCESS")],
        stores=[_fake_store()],
        pvs=[_fake_pv("pv1", cg=False)],
    )
    pre = precheck_aisast_and_callgraph(
        client,
        project,
        tenant_root="example-tenant",
        namespace="example-tenant",
    )
    assert pre.ok is False
    assert GATE_CG in pre.failed_gate_ids()


def test_run_bridge_success_match_only() -> None:
    project = SimpleNamespace(
        uuid="proj1",
        meta=SimpleNamespace(name="https://github.com/org/repo.git"),
        tenant_meta=SimpleNamespace(namespace="example-tenant"),
    )
    client = _make_client(
        versions=[_fake_rv("SUCCESS")],
        stores=[_fake_store()],
        pvs=[_fake_pv("pv1")],
    )
    result = run_aisast_callgraph_bridge(
        client,
        project,
        tenant="example-tenant",
        namespace="example-tenant",
    )
    assert result.status == "success"
    assert result.precheck["ok"] is True
    assert len(result.seeds) >= 1
    assert result.matches
