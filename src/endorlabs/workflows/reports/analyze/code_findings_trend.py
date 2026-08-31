"""SAST / AI-SAST / Secrets FindingLog burndown for the report packet.

Same path/tag grain as SCA burndown via shared category specs
(``finding_burndown_specs`` + ``build_category_burndown_block``). CodeOwners is
omitted in v1 (FindingLog has no ``code_owners`` field).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from endorlabs.workflows.findings.finding_log_trends import CHART_DEFAULT_LOOKBACK
from endorlabs.workflows.reports.analyze.burndown_common import (
    DEFAULT_BURNDOWN_WORKERS,
    build_category_burndown_block,
)
from endorlabs.workflows.reports.analyze.finding_burndown_specs import (
    AI_SAST_FACET_KEYS,
    CATEGORY_AI_SAST,
    CATEGORY_SAST,
    CATEGORY_SECRETS,
    CODE_CATEGORIES,
    SAST_FACET_KEYS,
    SECRETS_FACET_KEYS,
)

if TYPE_CHECKING:
    from endorlabs import Client

# Re-exports for tests / callers.
CODE_CATEGORY_SAST = CATEGORY_SAST
CODE_CATEGORY_AI_SAST = CATEGORY_AI_SAST
CODE_CATEGORY_SECRETS = CATEGORY_SECRETS
__all__ = [
    "AI_SAST_FACET_KEYS",
    "CODE_CATEGORIES",
    "CODE_CATEGORY_AI_SAST",
    "CODE_CATEGORY_SAST",
    "CODE_CATEGORY_SECRETS",
    "SAST_FACET_KEYS",
    "SECRETS_FACET_KEYS",
    "build_code_findings_burndown_report",
]


def build_code_findings_burndown_report(
    client: Client,
    *,
    tenant: str,
    projects: list[dict[str, Any]],
    leaf_namespaces: list[str],
    path_options: list[str],
    tag_catalog: list[dict[str, Any]],
    lookback: int = CHART_DEFAULT_LOOKBACK,
    min_projects: int = 1,
    max_workers: int = DEFAULT_BURNDOWN_WORKERS,
    categories: list[str] | tuple[str, ...] | None = None,
) -> dict[str, Any]:
    """Build SAST / AI-SAST / Secrets FindingLog series under path + tag grain.

    *categories* defaults to all code categories; pass a license-filtered
    subset to skip unentitled FindingLog matrices.
    """
    selected = list(categories) if categories is not None else list(CODE_CATEGORIES)
    unknown = [k for k in selected if k not in CODE_CATEGORIES]
    if unknown:
        raise ValueError(f"unknown code burndown categories: {unknown}")

    by_category: dict[str, Any] = {}
    shared_meta: dict[str, Any] | None = None
    period_caption = ""
    week_categories: list[str] = []

    for key in selected:
        block = build_category_burndown_block(
            client,
            tenant=tenant,
            projects=projects,
            leaf_namespaces=leaf_namespaces,
            path_options=path_options,
            tag_catalog=tag_catalog,
            category_key=key,
            lookback=lookback,
            min_projects=min_projects,
            max_workers=max_workers,
            categories=week_categories or None,
            period_caption=period_caption or None,
        )
        by_category[key] = block
        if not week_categories:
            week_categories = list(
                (
                    ((block.get("seriesFilters") or {}).get("perPath") or {})
                    .get("all", {})
                    .get("all", {})
                    .get("all")
                    or {}
                ).get("categories")
                or []
            )
        period_caption = str(block.get("periodCaption") or period_caption)
        if shared_meta is None:
            shared_meta = block.get("tagSeriesMeta")

    return {
        "lookback": lookback,
        "interval": "week",
        "periodCaption": period_caption,
        "categories": selected,
        "byCategory": by_category,
        "tagSeriesMeta": shared_meta
        or {
            "seriesReady": [],
            "seriesPending": [e["tag"] for e in tag_catalog],
            "seriesReadyCount": 0,
            "seriesPendingCount": len(tag_catalog),
            "pullPolicy": {
                "minProjects": min_projects,
                "mode": "skipped",
                "workers": max_workers,
            },
        },
    }
