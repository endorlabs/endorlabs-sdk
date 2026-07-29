"""Unit tests for code-findings (SAST/Secrets/AI-SAST) burndown helpers."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

from endorlabs.filters import (
    AI_TAG_CLAUSE,
    ai_sast_log_base_filter,
    sast_log_base_filter,
    secrets_log_base_filter,
)
from endorlabs.workflows.findings.finding_log_trends import (
    empty_series_cell,
    expand_severity_facet_matrix,
)
from endorlabs.workflows.reports.analyze.code_findings_trend import (
    CODE_CATEGORIES,
    SAST_FACET_KEYS,
    build_code_findings_burndown_report,
)


def test_code_category_base_filters() -> None:
    assert "FINDING_CATEGORY_SAST" in sast_log_base_filter()
    assert AI_TAG_CLAUSE in ai_sast_log_base_filter()
    assert "FINDING_CATEGORY_SECRETS" in secrets_log_base_filter()


def test_expand_severity_facet_matrix() -> None:
    cats = ["01/05", "01/12"]
    caption = "2w"

    def cell(n: int) -> dict[str, Any]:
        c = empty_series_cell(cats, caption)
        c["weeklyNew"] = [n, 0]
        c["weeklyResolved"] = [0, 0]
        return c

    raw = {
        "critical": {"all": cell(1), "true_positive": cell(2)},
        "high": {"all": cell(3), "true_positive": cell(4)},
    }
    expanded = expand_severity_facet_matrix(
        raw,
        facet_keys=("all", "true_positive"),
        categories=cats,
        period_caption=caption,
    )
    assert expanded["all"]["all"]["weeklyNew"] == [4, 0]
    assert expanded["all"]["true_positive"]["weeklyNew"] == [6, 0]


def test_build_code_findings_burndown_report_shape() -> None:
    cats = ["01/05", "01/12"]
    caption = "2w"
    leaf = "example-tenant.child"
    uid = "00000000-0000-4000-8000-00000000000a"

    def fake_matrix(*_a: Any, **kwargs: Any) -> dict[str, dict[str, dict[str, Any]]]:
        facets = kwargs.get("facet_keys") or SAST_FACET_KEYS
        cell = empty_series_cell(cats, caption)
        return {
            sev: {facet: dict(cell) for facet in facets}
            for sev in ("all", "critical", "high")
        }

    seed = empty_series_cell(cats, caption)

    with (
        patch(
            "endorlabs.workflows.findings.finding_log_trends."
            "query_severity_facet_series_cell",
            return_value=seed,
        ),
        patch(
            "endorlabs.workflows.findings.finding_log_trends."
            "query_severity_facet_matrix",
            side_effect=fake_matrix,
        ),
    ):
        report = build_code_findings_burndown_report(
            MagicMock(),
            tenant="example-tenant",
            projects=[
                {
                    "uuid": uid,
                    "name": "https://github.com/org/a.git",
                    "namespace": leaf,
                    "tags": ["team-alpha"],
                }
            ],
            leaf_namespaces=[leaf],
            path_options=["all", leaf],
            tag_catalog=[
                {"tag": "team-alpha", "projectCount": 1, "projectUuids": [uid]}
            ],
            lookback=2,
            min_projects=1,
            max_workers=2,
        )

    assert report["categories"] == list(CODE_CATEGORIES)
    for key in CODE_CATEGORIES:
        block = report["byCategory"][key]
        assert "seriesFilters" in block
        assert "tagSeries" in block
        assert "all" in block["seriesFilters"]["perPath"]
