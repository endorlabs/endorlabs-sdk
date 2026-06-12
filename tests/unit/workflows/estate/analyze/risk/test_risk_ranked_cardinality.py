"""Unit tests for risk-ranked version cardinality analytics."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, Mock, patch

from endorlabs.workflows.estate.analyze.cardinality.columns import (
    RISK_WEIGHTED_CARDINALITY_SCHEMA,
)
from endorlabs.workflows.estate.analyze.cardinality.group_list import (
    grouped_count_list_parameters_for_package_name,
)
from endorlabs.workflows.estate.analyze.risk.cardinality import (
    build_risk_document,
    export_risk_ranked_version_cardinality,
)
from endorlabs.workflows.estate.analyze.risk.scoring import (
    CriticalHighCountScorer,
    PackageRiskSummary,
    aggregate_families,
    aggregate_family_findings_by_version,
    aggregate_findings_by_version,
    dm_package_name_for_key,
    join_version_usage_and_risk,
    package_family_name,
    rank_packages,
    resolve_scorer,
)
from endorlabs.workflows.estate.collect.findings import (
    FINDING_LIST_MASK,
    findings_filter_for_project,
    main_context_label,
)
from endorlabs.workflows.estate.filters.main_context import MAIN_CONTEXT_LIST_FILTER


def _finding(
    package: str,
    *,
    version: str = "1.0.0",
    level: str = "FINDING_LEVEL_CRITICAL",
) -> dict:
    return {
        "spec": {
            "level": level,
            "finding_categories": ["FINDING_CATEGORY_SCA"],
            "target_dependency_package_name": package,
            "target_dependency_version": version,
        }
    }


def test_critical_high_scorer_weights() -> None:
    scorer = CriticalHighCountScorer()
    findings = [
        _finding("pypi://a", level="FINDING_LEVEL_CRITICAL"),
        _finding("pypi://a", level="FINDING_LEVEL_HIGH"),
        _finding("pypi://b", level="FINDING_LEVEL_MEDIUM"),
    ]
    summaries = scorer.aggregate_packages(findings)
    assert summaries["pypi://a"].risk_score == 6.0
    assert summaries["pypi://a"].findings_critical == 1
    assert summaries["pypi://a"].findings_high == 1
    assert "pypi://b" not in summaries


def test_rank_packages_tie_break() -> None:
    ranked = rank_packages(
        {
            "b": PackageRiskSummary(package_name="b", risk_score=10, findings_total=2),
            "a": PackageRiskSummary(package_name="a", risk_score=10, findings_total=3),
            "c": PackageRiskSummary(package_name="c", risk_score=5, findings_total=9),
        }
    )
    assert [item.package_name for item in ranked] == ["a", "b", "c"]


def test_package_family_name_strips_embedded_version() -> None:
    assert package_family_name(
        "mvn://com.fasterxml.jackson.core:jackson-databind@2.9.8"
    ) == ("mvn://com.fasterxml.jackson.core:jackson-databind")
    assert dm_package_name_for_key("go://stdlib@go1.13") == "go://stdlib"


def test_join_version_usage_resolves_family_dm_name() -> None:
    scorer = CriticalHighCountScorer()
    finding_key = "mvn://com.fasterxml.jackson.core:jackson-databind@2.9.8"
    findings = [_finding(finding_key, version="2.9.8")]
    version_risk = aggregate_findings_by_version(
        findings,
        scorer=scorer,
        package_name=finding_key,
    )
    usage_rows = [
        {
            "package_name": "mvn://com.fasterxml.jackson.core:jackson-databind",
            "package_version": "2.9.8",
            "usage_count": 12,
        },
        {
            "package_name": "mvn://com.fasterxml.jackson.core:jackson-databind",
            "package_version": "2.9.9",
            "usage_count": 4,
        },
    ]
    joined, warnings = join_version_usage_and_risk(
        usage_rows,
        version_risk,
        package_name=finding_key,
    )
    by_version = {row["version"]: row for row in joined}
    assert by_version["2.9.8"]["usage_count"] == 12
    assert by_version["2.9.8"]["findings_total"] == 1
    assert by_version["2.9.9"]["usage_count"] == 4
    assert by_version["2.9.9"]["findings_total"] == 0
    assert not warnings


def test_join_version_usage_and_risk_orphan_warning() -> None:
    scorer = CriticalHighCountScorer()
    findings = [_finding("pypi://django", version="4.2.0")]
    version_risk = aggregate_findings_by_version(
        findings,
        scorer=scorer,
        package_name="pypi://django",
    )
    usage_rows = [
        {
            "package_name": "pypi://django",
            "package_version": "5.0.0",
            "usage_count": 3,
        }
    ]
    joined, warnings = join_version_usage_and_risk(
        usage_rows,
        version_risk,
        package_name="pypi://django",
    )
    by_version = {row["version"]: row for row in joined}
    assert by_version["5.0.0"]["usage_count"] == 3
    assert by_version["5.0.0"]["risk_score"] == 0.0
    assert by_version["4.2.0"]["orphan"] is True
    assert warnings
    assert "pypi://django (4.2.0)" in warnings[0]


def test_findings_filter_includes_main_context() -> None:
    filt = findings_filter_for_project("proj-uuid")
    assert MAIN_CONTEXT_LIST_FILTER in filt or "CONTEXT_TYPE_MAIN" in filt
    assert "proj-uuid" in filt
    assert "spec.finding_categories contains" in filt
    assert "FINDING_CATEGORY_SCA" in filt
    assert "&&" not in filt
    assert " and " in filt


def test_grouped_list_params_main_context_package() -> None:
    params = grouped_count_list_parameters_for_package_name(
        page_size=100,
        package_name="pypi://requests",
        main_context=True,
    )
    assert params.filter is not None
    assert MAIN_CONTEXT_LIST_FILTER in params.filter
    assert "pypi://requests" in params.filter


def test_build_risk_document_schema() -> None:
    doc = build_risk_document(
        estate_root="tenant",
        scorer_name="critical_high_count",
        ranked=[PackageRiskSummary(package_name="pypi://a", risk_score=4)],
        packages=[],
        warnings=[],
        top_n=1,
    )
    assert doc["schema"] == RISK_WEIGHTED_CARDINALITY_SCHEMA
    assert doc["context_filter"] == main_context_label()
    assert doc["ranking"][0]["rank"] == 1


def test_resolve_scorer_unknown() -> None:
    try:
        resolve_scorer("missing")
    except ValueError as exc:
        assert "missing" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_aggregate_family_findings_by_version_across_coordinate_formats() -> None:
    """Findings with mixed qualified keys roll up to one family by resolved version."""
    scorer = CriticalHighCountScorer()
    family = "mvn://com.fasterxml.jackson.core:jackson-databind"
    findings = [
        _finding(f"{family}@2.9.4", version="2.9.4"),
        _finding(f"{family}@2.9.4", version="2.9.4", level="FINDING_LEVEL_HIGH"),
        _finding(family, version="2.12.6.1"),
        _finding(family, version="2.19.2", level="FINDING_LEVEL_HIGH"),
    ]
    families = aggregate_families(findings, scorer)
    assert families[family].findings_critical == 2
    assert families[family].findings_high == 2
    assert families[family].findings_total == 4

    by_version = aggregate_family_findings_by_version(
        findings,
        family_name=family,
        scorer=scorer,
    )
    assert by_version["2.9.4"].findings_total == 2
    assert by_version["2.12.6.1"].findings_critical == 1
    assert by_version["2.19.2"].findings_high == 1


def test_export_risk_ranked_version_cardinality_mocked() -> None:
    group_key = json.dumps(
        [
            {"key": "spec.dependency_data.package_name", "value": "pypi://django"},
            {"key": "spec.dependency_data.resolved_version", "value": "4.2"},
        ]
    )

    client = MagicMock()
    client.Namespace.list.return_value = []
    client.Project.list.return_value = [
        MagicMock(uuid="proj-1", tenant_meta=MagicMock(namespace="tenant"))
    ]
    client.Finding.list.return_value = [
        {
            "spec": {
                "level": "FINDING_LEVEL_CRITICAL",
                "finding_categories": ["FINDING_CATEGORY_SCA"],
                "target_dependency_package_name": "pypi://django",
                "target_dependency_version": "4.2",
            }
        }
    ]

    from endorlabs.operations.list_response import (
        GroupBucket,
        count_from_wire,
        parse_group_key,
    )

    def _list_groups(**kwargs: object) -> object:
        _ = kwargs
        yield GroupBucket(
            key=group_key,
            parsed=parse_group_key(group_key),
            data={"aggregation_count": {"count": 2}},
            count=count_from_wire({"aggregation_count": {"count": 2}}),
        )

    client.DependencyMetadata.list_groups = Mock(side_effect=_list_groups)

    with patch(
        "endorlabs.workflows.estate.collect.findings.list_estate_namespace_names",
        return_value=["tenant"],
    ):
        with patch(
            "endorlabs.workflows.estate.analyze.risk.cardinality.list_estate_namespace_names",
            return_value=["tenant"],
        ):
            result = export_risk_ranked_version_cardinality(
                client,
                "tenant",
                top_n=1,
            )

    assert result.status in {"success", "partial"}
    assert result.document["schema"] == RISK_WEIGHTED_CARDINALITY_SCHEMA
    assert len(result.document["packages"]) == 1
    assert result.document["packages"][0]["package_name"] == "pypi://django"
    assert result.ranking_table.row_count >= 1
    call_kwargs = client.Finding.list.call_args.kwargs
    assert "CONTEXT_TYPE_MAIN" in call_kwargs["filter"]
    assert call_kwargs["mask"] == FINDING_LIST_MASK


def test_export_version_cardinality_for_package_match_mocked() -> None:
    from endorlabs.workflows.estate.analyze.cardinality.export import (
        export_version_cardinality_for_package_match,
    )

    group_key = json.dumps(
        [
            {"key": "spec.dependency_data.package_name", "value": "pypi://django"},
            {"key": "spec.dependency_data.resolved_version", "value": "4.2"},
        ]
    )
    client = MagicMock()

    from endorlabs.operations.list_response import (
        GroupBucket,
        count_from_wire,
        parse_group_key,
    )

    def _list_groups(**kwargs: object) -> object:
        _ = kwargs
        yield GroupBucket(
            key=group_key,
            parsed=parse_group_key(group_key),
            data={"aggregation_count": {"count": 1}},
            count=count_from_wire({"aggregation_count": {"count": 1}}),
        )

    client.DependencyMetadata.list_groups = Mock(side_effect=_list_groups)

    with (
        patch(
            "endorlabs.workflows.estate.analyze.cardinality.export.discover_estate_namespace_names",
            return_value=["tenant"],
        ),
    ):
        result = export_version_cardinality_for_package_match(
            client,
            "tenant",
            "django",
            exact_package_name="pypi://django",
        )

    assert result.status == "success"
    assert result.stats.package_count == 1


def test_export_version_cardinality_for_package_match_namespace_error() -> None:
    from endorlabs.workflows.estate.analyze.cardinality.export import (
        export_version_cardinality_for_package_match,
    )

    client = MagicMock()
    with patch(
        "endorlabs.workflows.estate.analyze.cardinality.export.discover_estate_namespace_names",
        side_effect=RuntimeError("boom"),
    ):
        result = export_version_cardinality_for_package_match(
            client, "tenant", "django"
        )
    assert result.status == "error"
    assert "Namespace list failed" in result.message


def test_export_version_cardinality_mocked() -> None:
    from endorlabs.workflows.estate.analyze.cardinality.export import (
        export_version_cardinality,
    )

    client = MagicMock()
    usage_row = {
        "estate_root": "tenant",
        "project_uuid": "proj-1",
        "package_name": "pypi://flask",
        "package_version": "2.0",
        "usage_count": 2,
    }

    with (
        patch(
            "endorlabs.workflows.estate.analyze.cardinality.export.discover_estate_namespace_names",
            return_value=["tenant"],
        ),
        patch(
            "endorlabs.workflows.estate.analyze.cardinality.export._fetch_namespace_via_importer_package_versions",
            return_value=([usage_row], 1, 1, 1, []),
        ),
    ):
        result = export_version_cardinality(client, "tenant")

    assert result.status == "success"
    assert result.stats.package_count == 1


def test_export_version_cardinality_all_namespaces_fail() -> None:
    from endorlabs.workflows.estate.analyze.cardinality.export import (
        export_version_cardinality,
    )

    client = MagicMock()
    with (
        patch(
            "endorlabs.workflows.estate.analyze.cardinality.export.discover_estate_namespace_names",
            return_value=["tenant"],
        ),
        patch(
            "endorlabs.workflows.estate.analyze.cardinality.export._fetch_namespace_via_importer_package_versions",
            return_value=([], 0, 0, 0, ["tenant: boom"]),
        ),
    ):
        result = export_version_cardinality(client, "tenant")
    assert result.status == "error"


def test_export_version_cardinality_for_package_match_all_namespaces_fail() -> None:
    from endorlabs.workflows.estate.analyze.cardinality.export import (
        export_version_cardinality_for_package_match,
    )

    client = MagicMock()
    client.DependencyMetadata.list_groups = Mock(side_effect=RuntimeError("boom"))
    with patch(
        "endorlabs.workflows.estate.analyze.cardinality.export.discover_estate_namespace_names",
        return_value=["tenant"],
    ):
        result = export_version_cardinality_for_package_match(
            client, "tenant", "django"
        )
    assert result.status == "error"
