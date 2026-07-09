"""Tests for QuerySpec and Reference wire serialization."""

from __future__ import annotations

from endorlabs.query import QuerySpec, Reference


def test_query_spec_group_serializes_list_parameters_group() -> None:
    spec = (
        QuerySpec.root("DependencyMetadata")
        .leaf_scope()
        .group("spec.package_version_name", "spec.package_version_version")
    )
    wire = spec.to_wire()
    group = wire["list_parameters"]["group"]
    assert group["aggregation_paths"] == (
        "spec.package_version_name,spec.package_version_version"
    )


def test_reference_count_and_list_wire() -> None:
    ref = (
        Reference("Finding")
        .connect("uuid", "spec.project_uuid")
        .count(filter='context.type=="CONTEXT_TYPE_MAIN"')
    )
    wire = ref.to_wire()
    lp = wire["query_spec"]["list_parameters"]
    assert lp["count"] is True
    assert "CONTEXT_TYPE_MAIN" in lp["filter"]


def test_query_spec_has_no_group_by_time_builder() -> None:
    assert not hasattr(QuerySpec.root("FindingLog"), "group_by_time")


def test_reference_has_no_group_by_time_builder() -> None:
    assert not hasattr(Reference("FindingLog"), "group_by_time")
