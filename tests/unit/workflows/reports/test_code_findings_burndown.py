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
    expand_severity_reach_matrix,
)
from endorlabs.workflows.reports.analyze.code_findings_trend import (
    CODE_CATEGORIES,
    SAST_FACET_KEYS,
    build_code_findings_burndown_report,
)
from endorlabs.workflows.reports.analyze.finding_burndown_specs import (
    SECRETS_CELLS,
    sev_facet_cells,
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
        "medium": {"all": cell(5), "true_positive": cell(6)},
        "low": {"all": cell(7), "true_positive": cell(8)},
    }
    expanded = expand_severity_facet_matrix(
        raw,
        facet_keys=("all", "true_positive"),
        categories=cats,
        period_caption=caption,
    )
    assert expanded["all"]["all"]["weeklyNew"] == [16, 0]
    assert expanded["all"]["true_positive"]["weeklyNew"] == [20, 0]
    assert expanded["medium"]["all"]["weeklyNew"] == [5, 0]
    assert expanded["low"]["all"]["weeklyNew"] == [7, 0]


def test_expand_severity_reach_matrix_sums_four_levels() -> None:
    cats = ["01/05"]
    caption = "1w"

    def cell(n: int) -> dict[str, Any]:
        c = empty_series_cell(cats, caption)
        c["weeklyNew"] = [n]
        c["weeklyResolved"] = [0]
        return c

    raw = {
        sev: {
            "reachable": cell(1),
            "prf": cell(2),
            "prd": cell(0),
            "unreachable_function": cell(0),
            "unreachable_dependency": cell(0),
        }
        for sev in ("critical", "high", "medium", "low")
    }
    expanded = expand_severity_reach_matrix(
        raw, categories=cats, period_caption=caption
    )
    # per-sev all = RF+PRF = 1+2
    assert expanded["critical"]["all"]["weeklyNew"] == [3]
    # top-level all = 4 * 3
    assert expanded["all"]["all"]["weeklyNew"] == [12]
    assert expanded["all"]["reachable"]["weeklyNew"] == [4]


def test_sev_facet_cells_include_medium_low() -> None:
    cells = sev_facet_cells((("all", ""),))
    levels = {row[0] for row in cells}
    assert levels == {"critical", "high", "medium", "low"}
    assert len(SECRETS_CELLS) == 4 * 3  # four sevs x all/valid/invalid


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
            for sev in ("all", "critical", "high", "medium", "low")
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
