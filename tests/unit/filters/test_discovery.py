"""Unit tests for filter operator/field discovery (SDK-009)."""

from __future__ import annotations

from endorlabs.filters import (
    describe_filter_fields,
    describe_filter_operators,
)


def test_describe_filter_operators_has_matches_and_contains() -> None:
    discovery = describe_filter_operators()
    names = {op.name for op in discovery.operators}
    assert "matches" in names
    assert "contains" in names
    assert discovery.enum_snippets_relpath.endswith("filter-enum-snippets.md")


def test_describe_filter_fields_finding() -> None:
    fields = describe_filter_fields("Finding")
    assert fields.attr_name == "Finding"
    paths = {f.path for f in fields.fields}
    assert "spec.project_uuid" in paths
    assert "meta.name" in paths
    assert fields.enum_snippets_relpath.endswith("filter-enum-snippets.md")
