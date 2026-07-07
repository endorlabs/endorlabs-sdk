"""Unit tests for canonical endorlabs.filters package."""

from __future__ import annotations

from endorlabs.filters import (
    MAIN_CONTEXT_CLAUSE,
    category_filter,
    estate_findings_filter,
    main_context_filter,
    pv_count_filter,
    pv_main_context_filter,
)


def test_main_context_filter_with_extra() -> None:
    filt = main_context_filter('spec.project_uuid=="p1"')
    assert 'context.type=="CONTEXT_TYPE_MAIN"' in filt
    assert "spec.project_uuid" in filt


def test_pv_main_context_filter_matches_clause() -> None:
    assert pv_main_context_filter() == MAIN_CONTEXT_CLAUSE


def test_category_filter_includes_main_context() -> None:
    filt = category_filter("FINDING_CATEGORY_VULNERABILITY")
    assert MAIN_CONTEXT_CLAUSE in filt
    assert "FINDING_CATEGORY_VULNERABILITY" in filt


def test_pv_count_filter_scopes_project() -> None:
    filt = pv_count_filter("abc-123")
    assert 'spec.project_uuid=="abc-123"' in filt


def test_estate_findings_filter_includes_sca_and_vuln() -> None:
    filt = estate_findings_filter()
    assert "FINDING_CATEGORY_SCA" in filt
    assert "FINDING_CATEGORY_VULNERABILITY" in filt


def test_project_scoped_filter_single_source() -> None:
    from endorlabs.filters.project_scope import project_scoped_filter as filters_fn
    from endorlabs.tools.list_sharding import project_scoped_filter as tools_fn

    base = 'spec.level=="FINDING_LEVEL_HIGH"'
    assert tools_fn(base, "p1") == filters_fn(base, "p1")
