"""Unit tests for compile dependency graph helpers."""

from __future__ import annotations

from endorlabs.filters import (
    MAIN_CONTEXT_LIST_FILTER,
    main_context_filter,
)
from endorlabs.workflows.estate.analyze.compile_graph.pipeline import (
    COMPILE_DEPENDENCY_GRAPH_SCHEMA,
    REGISTRATION_BINARY,
    REGISTRATION_GIT,
    annotate_vertices,
    build_graph_document,
    build_union_nodes,
    classify_project_registrations,
    compute_producer_rankings,
    filter_git_repositories,
    is_git_url_project_name,
    namespace_slug,
    project_union_key,
    registration_type_for_name,
    run_filter_git_repositories,
)
from endorlabs.workflows.estate.analyze.project_map.core import (
    SupportingPackage,
    aggregate_package_anchored_edges,
    row_to_supporting_tuples,
)


def test_namespace_slug() -> None:
    assert namespace_slug("acme") == "acme"
    assert namespace_slug("tenant.acme.backend") == "tenant_acme_backend"


def test_is_git_url_project_name() -> None:
    assert is_git_url_project_name("https://github.com/org/repo")
    assert not is_git_url_project_name("binary-dist_foo-1.0")


def test_registration_type_for_name() -> None:
    assert registration_type_for_name("https://github.com/a") == REGISTRATION_GIT
    assert registration_type_for_name("binary-dist_lib-1.0") == REGISTRATION_BINARY


def test_classify_project_registrations_includes_all() -> None:
    rows = [
        {"uuid": "g1", "name": "https://github.com/a.git", "namespace": "ns"},
        {"uuid": "b1", "name": "binary-dist_lib-1.0", "namespace": "ns"},
    ]
    classified, counts = classify_project_registrations(rows)
    assert len(classified) == 2
    assert counts[REGISTRATION_GIT] == 1
    assert counts[REGISTRATION_BINARY] == 1
    assert classified[0]["registration_type"] == REGISTRATION_GIT
    assert classified[1]["registration_type"] == REGISTRATION_BINARY


def test_filter_git_repositories_legacy_split() -> None:
    rows = [
        {"uuid": "g1", "name": "https://github.com/a.git", "namespace": "ns"},
        {"uuid": "b1", "name": "binary-dist_lib-1.0", "namespace": "ns"},
    ]
    git_rows, binary_rows = filter_git_repositories(rows)
    assert len(git_rows) == 1
    assert len(binary_rows) == 1
    assert git_rows[0]["registration_type"] == REGISTRATION_GIT
    assert binary_rows[0]["registration_type"] == REGISTRATION_BINARY


def test_run_filter_git_repositories_returns_classified() -> None:
    rows = [
        {"uuid": "g1", "name": "https://github.com/a", "namespace": "ns"},
        {"uuid": "b1", "name": "binary-dist_lib-1.0", "namespace": "ns"},
    ]
    graph_projects, counts = run_filter_git_repositories(rows)
    assert len(graph_projects) == 2
    assert counts[REGISTRATION_GIT] == 1
    assert counts[REGISTRATION_BINARY] == 1


def test_direct_only_skips_transitive_dm() -> None:
    spec = {
        "importer_data": {"project_uuid": "consumer"},
        "dependency_data": {
            "package_name": "mvn://com.acme:lib",
            "resolved_version": "1.0",
            "direct": False,
            "public": False,
        },
    }
    produced_by = {("mvn://com.acme:lib", "1.0"): {"producer"}}
    produced_name = {"mvn://com.acme:lib": {"producer"}}
    tuples = row_to_supporting_tuples(
        spec,
        {"consumer"},
        include_public=True,
        produced_by=produced_by,
        produced_name_only=produced_name,
        direct_only=True,
    )
    assert tuples == []


def test_package_anchored_edges_two_anchors() -> None:
    supporting = [
        (
            "c1",
            "p1",
            SupportingPackage(
                package_name="mvn://a",
                package_version="1",
                dependency_kind="direct",
                visibility="private",
                evidence_tier="tier_a_exact",
            ),
        ),
        (
            "c1",
            "p1",
            SupportingPackage(
                package_name="mvn://b",
                package_version="2",
                dependency_kind="direct",
                visibility="public",
                evidence_tier="tier_a_exact",
            ),
        ),
    ]
    edges = aggregate_package_anchored_edges(supporting)
    assert len(edges) == 2
    anchors = {e["linking_package_name"] for e in edges}
    assert anchors == {"mvn://a", "mvn://b"}
    assert all(e["dependency_scope"] == "compile" for e in edges)


def test_build_graph_document_isolated_and_imports() -> None:
    projects = [
        {
            "uuid": "lib",
            "name": "https://github.com/lib",
            "namespace": "ns",
            "registration_type": REGISTRATION_GIT,
        },
        {
            "uuid": "app",
            "name": "https://github.com/app",
            "namespace": "ns",
            "registration_type": REGISTRATION_GIT,
        },
        {
            "uuid": "solo",
            "name": "https://github.com/solo",
            "namespace": "ns",
            "registration_type": REGISTRATION_GIT,
        },
    ]
    aggregated = [
        {
            "from_project_uuid": "app",
            "to_project_uuid": "lib",
            "linking_package_name": "mvn://com.acme:lib",
            "package_version": "1.0",
            "match_tier": "tier_a_exact",
            "visibility": "private",
        }
    ]
    published = {
        "lib": [
            {
                "package_name": "mvn://com.acme:lib",
                "package_version_name": "mvn://com.acme:lib@1.0",
                "package_version": "1.0",
                "pv_uuid": "pv1",
            }
        ]
    }
    doc = build_graph_document(
        namespace="ns",
        projects=projects,
        aggregated_edges=aggregated,
        published_by_project=published,
    )
    assert doc["schema"] == COMPILE_DEPENDENCY_GRAPH_SCHEMA
    assert doc["node_count"] == 3
    assert doc["edge_count"] == 1
    assert doc["isolated_count"] == 1
    solo = next(n for n in doc["nodes"] if "solo" in str(n.get("name")))
    assert solo["isolated"] is True
    assert solo["registration_type"] == REGISTRATION_GIT
    assert solo["in_degree"] == 0
    assert solo["out_degree"] == 0
    lib = next(n for n in doc["nodes"] if "lib" in str(n.get("name")))
    assert len(lib["published_packages"]) == 1
    assert len(lib["imported_by"]) == 1
    app = next(n for n in doc["nodes"] if "app" in str(n.get("name")))
    assert len(app["direct_imports"]) == 1
    assert app["isolated"] is False


def test_build_graph_document_includes_binary_component_node() -> None:
    projects = [
        {
            "uuid": "bin",
            "name": "binary-dist_lib-1.0",
            "namespace": "ns",
            "registration_type": REGISTRATION_BINARY,
        },
        {
            "uuid": "app",
            "name": "https://github.com/app",
            "namespace": "ns",
            "registration_type": REGISTRATION_GIT,
        },
    ]
    doc = build_graph_document(
        namespace="ns",
        projects=projects,
        aggregated_edges=[],
        published_by_project={},
    )
    assert doc["node_count"] == 2
    binary = next(
        n for n in doc["nodes"] if n.get("registration_type") == REGISTRATION_BINARY
    )
    assert binary["git_identity"].startswith("uuid:")
    assert binary["isolated"] is True


def test_project_union_key_normalizes_git_urls() -> None:
    a = project_union_key("https://github.com/org/Repo.git", "u1")
    b = project_union_key("https://github.com/org/repo", "u2")
    assert a == b


def test_build_union_nodes_merges_duplicate_git_urls() -> None:
    projects = [
        {
            "uuid": "u1",
            "name": "https://github.com/org/foo.git",
            "namespace": "a",
            "registration_type": REGISTRATION_GIT,
        },
        {
            "uuid": "u2",
            "name": "https://github.com/org/foo",
            "namespace": "b",
            "registration_type": REGISTRATION_GIT,
        },
    ]
    nodes, uuid_to_node = build_union_nodes(projects, estate_namespace="ns")
    assert len(nodes) == 1
    assert nodes[0]["member_count"] == 2
    assert nodes[0]["git_identity"].startswith("git:")
    assert nodes[0]["registration_type"] == REGISTRATION_GIT
    assert uuid_to_node["u1"] == uuid_to_node["u2"]


def test_compute_producer_rankings() -> None:
    published = {
        "lib": [{"package_name": "mvn://x", "package_version_name": "mvn://x@1"}]
    }
    doc = build_graph_document(
        namespace="ns",
        projects=[
            {
                "uuid": "lib",
                "name": "https://lib",
                "namespace": "ns",
                "registration_type": REGISTRATION_GIT,
            },
            {
                "uuid": "a",
                "name": "https://a",
                "namespace": "ns",
                "registration_type": REGISTRATION_GIT,
            },
            {
                "uuid": "b",
                "name": "https://b",
                "namespace": "ns",
                "registration_type": REGISTRATION_GIT,
            },
        ],
        aggregated_edges=[
            {
                "from_project_uuid": "a",
                "to_project_uuid": "lib",
                "linking_package_name": "mvn://x",
                "package_version": "1",
                "match_tier": "tier_a_exact",
            },
            {
                "from_project_uuid": "b",
                "to_project_uuid": "lib",
                "linking_package_name": "mvn://x",
                "package_version": "1",
                "match_tier": "tier_a_exact",
            },
        ],
        published_by_project=published,
    )
    rankings = compute_producer_rankings(doc, top_n=5)
    assert rankings["producers_with_importers"] == 1
    top = rankings["rankings"][0]
    assert top["importer_count"] == 2
    assert top["inbound_import_count"] == 2


def test_main_context_filter() -> None:
    assert main_context_filter() == MAIN_CONTEXT_LIST_FILTER


def test_detect_communities_membership_covers_all_nodes() -> None:
    import pytest

    pytest.importorskip("igraph")
    pytest.importorskip("leidenalg")
    from endorlabs.workflows.estate.analyze.compile_graph.community_detection import (
        detect_communities,
    )

    import_graph = {
        "namespace": "tenant.ns",
        "nodes": [
            {"node_id": 0, "project_uuid": "a", "namespace": "tenant.ns"},
            {"node_id": 1, "project_uuid": "b", "namespace": "tenant.ns"},
            {"node_id": 2, "project_uuid": "c", "namespace": "tenant.ns"},
        ],
        "edges": [
            {
                "importer_vertex_id": 0,
                "producer_vertex_id": 1,
                "linking_package_name": "mvn://x",
            },
            {
                "importer_vertex_id": 1,
                "producer_vertex_id": 2,
                "linking_package_name": "mvn://y",
            },
        ],
        "isolated_count": 0,
    }
    payload, validation, profiles = detect_communities(import_graph)
    assert validation.ok
    assert payload["node_count"] == 3
    assert len(payload["membership"]) == 3
    assert len(profiles.get("communities") or []) > 0


def test_community_detection_edge_and_vertex_weights() -> None:
    import pytest

    pytest.importorskip("igraph")
    pytest.importorskip("leidenalg")
    from endorlabs.workflows.estate.analyze.compile_graph.community_detection import (
        CommunityDetectionOptions,
        detect_communities,
    )

    import_graph = {
        "namespace": "tenant.ns",
        "nodes": [
            {"node_id": 0, "project_uuid": "a", "in_degree": 0},
            {"node_id": 1, "project_uuid": "b", "in_degree": 2},
        ],
        "edges": [
            {
                "importer_vertex_id": 0,
                "producer_vertex_id": 1,
                "linking_package_name": "mvn://x",
                "import_evidence_count": 5,
            }
        ],
    }
    payload, validation, _ = detect_communities(
        import_graph,
        options=CommunityDetectionOptions(
            edge_weight_source="import_evidence_count",
            vertex_weight_source="inbound_import_count",
        ),
    )
    assert validation.ok
    assert payload["edge_weight_source"] == "import_evidence_count"
    assert payload["vertex_weight_source"] == "inbound_import_count"


def test_annotate_vertices_published_packages_deduped() -> None:
    nodes = [
        {
            "node_id": 0,
            "project_uuid": "u1",
            "project_uuids": ["u1"],
            "name": "https://a",
        },
    ]
    annotate_vertices(
        nodes,
        [],
        published_by_project={
            "u1": [
                {"package_name": "mvn://x", "package_version_name": "mvn://x@1"},
                {"package_name": "mvn://x", "package_version_name": "mvn://x@2"},
            ]
        },
    )
    assert len(nodes[0]["published_packages"]) == 1
