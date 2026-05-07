"""Unit tests for stitched path summaries in context workflow."""

from endorlabs.workflows.reachability.context import _build_stitching


def test_build_stitching_reachable_target() -> None:
    customer_callables = [
        {
            "method_id": 1,
            "uri": "java://com.indeed:java-spring-service$1.0.0/com.indeed.App.entry()",
        },
        {
            "method_id": 2,
            "uri": "java://com.indeed:java-spring-service$1.0.0/org.pkg.Bridge.api()",
        },
    ]
    customer_edges = [{"source_id": 1, "target_id": 2}]
    oss_callables = [
        {"method_id": 20, "uri": "java://org.pkg:dep$1.0/org.pkg.Bridge.api()"},
        {"method_id": 21, "uri": "java://org.pkg:dep$1.0/org.pkg.Vuln.hit()"},
    ]
    oss_edges = [{"source_id": 20, "target_id": 21}]
    out = _build_stitching(
        customer_callables,
        customer_edges,
        oss_callables,
        oss_edges,
        ["/org.pkg.Vuln.hit()"],
    )
    assert out["shared_bridge_norms"] == 1
    assert out["reachable_vulnerable_targets_from_bridges"] == 1


def test_build_stitching_unreachable_target() -> None:
    customer_callables = [
        {
            "method_id": 1,
            "uri": "java://com.indeed:java-spring-service$1.0.0/com.indeed.App.entry()",
        },
        {
            "method_id": 2,
            "uri": "java://com.indeed:java-spring-service$1.0.0/org.pkg.Bridge.api()",
        },
    ]
    customer_edges = [{"source_id": 1, "target_id": 2}]
    oss_callables = [
        {"method_id": 20, "uri": "java://org.pkg:dep$1.0/org.pkg.Bridge.api()"},
        {"method_id": 21, "uri": "java://org.pkg:dep$1.0/org.pkg.Vuln.hit()"},
    ]
    oss_edges = []
    out = _build_stitching(
        customer_callables,
        customer_edges,
        oss_callables,
        oss_edges,
        ["/org.pkg.Vuln.hit()"],
    )
    assert out["shared_bridge_norms"] == 1
    assert out["reachable_vulnerable_targets_from_bridges"] == 0
