"""Unit tests for reachability stitching helpers."""

from endorlabs.workflows.reachability.stitch import (
    bfs_multi_source,
    build_adjacency,
    build_norm_index,
    find_bridge_norms,
    normalize_uri,
    reconstruct_path,
)


def test_normalize_uri_strips_package_prefix() -> None:
    uri = "java://org.apache.tomcat.embed:tomcat-embed-core$9.0/org.apache.catalina.authenticator.AuthenticatorBase.invoke()"
    assert (
        normalize_uri(uri)
        == "/org.apache.catalina.authenticator.AuthenticatorBase.invoke()"
    )


def test_find_bridge_norms_shared_nodes() -> None:
    customer = [
        {"method_id": 1, "uri": "java://a$1.0/com.app.Main.run()"},
        {"method_id": 2, "uri": "java://a$1.0/org.shared.Lib.call()"},
    ]
    oss = [
        {"method_id": 10, "uri": "java://b$1.0/org.shared.Lib.call()"},
        {"method_id": 11, "uri": "java://b$1.0/org.other.Foo.x()"},
    ]
    bridges = find_bridge_norms(customer, oss)
    assert bridges == {"/org.shared.Lib.call()"}


def test_bfs_and_reconstruct_path() -> None:
    edges = [{"source_id": 1, "target_id": 2}, {"source_id": 2, "target_id": 3}]
    prev = bfs_multi_source([1], build_adjacency(edges), {3})
    assert reconstruct_path(prev, 3) == [1, 2, 3]


def test_build_norm_index_collects_all_ids() -> None:
    idx = build_norm_index(
        [
            {"method_id": 1, "uri": "java://a$1/x.Y()"},
            {"method_id": 2, "uri": "java://b$1/x.Y()"},
        ]
    )
    assert idx["/x.Y()"] == {1, 2}
