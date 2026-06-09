"""Tests for family risk chart and consumer counts."""

from __future__ import annotations

from endorlabs.workflows.estate.analyze.risk.consumer_counts import (
    merge_version_usage_and_consumers,
)
from endorlabs.workflows.estate.export.charts.family_risk import (
    build_family_risk_chart,
    render_family_risk_chart_html,
)


def _finding(
    package: str, *, version: str, level: str = "FINDING_LEVEL_CRITICAL"
) -> dict:
    return {
        "spec": {
            "level": level,
            "target_dependency_package_name": package,
            "target_dependency_version": version,
        }
    }


def test_merge_version_usage_and_consumers_sorts_by_consumer() -> None:
    rows = merge_version_usage_and_consumers(
        {"1.0": 10, "2.0": 3},
        {"1.0": 2, "2.0": 9},
    )
    assert rows[0]["version"] == "2.0"
    assert rows[0]["consumer_count"] == 9


def test_build_family_risk_chart_groups_by_family() -> None:
    findings = [
        _finding(
            "mvn://com.fasterxml.jackson.core:jackson-databind@2.9.8", version="2.9.8"
        ),
        _finding(
            "mvn://com.fasterxml.jackson.core:jackson-databind@2.9.9", version="2.9.9"
        ),
        _finding(
            "pypi://requests@2.31.0", version="2.31.0", level="FINDING_LEVEL_HIGH"
        ),
    ]
    document = build_family_risk_chart(
        findings,
        "tenant",
        top_n=2,
        client=None,
    )
    assert document["schema"] == "endor.risk_family_chart.v1"
    assert len(document["families"]) == 2
    jackson = document["families"][0]
    assert jackson["family_name"] == "mvn://com.fasterxml.jackson.core:jackson-databind"
    assert jackson["findings_critical"] == 2


def test_render_family_risk_chart_html_includes_family() -> None:
    document = build_family_risk_chart(
        [_finding("pypi://django@4.2", version="4.2")],
        "tenant",
        top_n=1,
        client=None,
    )
    # Inject synthetic consumer row for render path
    document["families"][0]["versions"] = [
        {
            "version": "4.2",
            "consumer_count": 5,
            "usage_count": 5,
            "findings_critical": 1,
            "findings_high": 0,
            "findings_total": 1,
            "risk_score": 4.0,
            "risk_intensity": 1.0,
        }
    ]
    html_doc = render_family_risk_chart_html(document)
    assert "pypi://django" in html_doc
    assert "5 consumers" in html_doc
