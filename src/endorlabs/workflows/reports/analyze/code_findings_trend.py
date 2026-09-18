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
    PR_LOOKBACK_WEEKS,
    SCOPE_PR,
    attach_main_pr_scopes,
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
    pr_active_uuids: list[str] | None = None,
    include_pr_scope: bool = True,
) -> dict[str, Any]:
    """Build SAST / AI-SAST / Secrets FindingLog series under path + tag grain.

    *categories* defaults to all code categories; pass a license-filtered
    subset to skip unentitled FindingLog matrices. When *include_pr_scope* is
    true, each category also carries ``scopes.pr`` (CI_RUN Detected/Blocked).
    """
    selected = list(categories) if categories is not None else list(CODE_CATEGORIES)
    unknown = [k for k in selected if k not in CODE_CATEGORIES]
    if unknown:
        raise ValueError(f"unknown code burndown categories: {unknown}")

    by_category: dict[str, Any] = {}
    shared_meta: dict[str, Any] | None = None
    period_caption = ""
    week_categories: list[str] = []
    pr_week_categories: list[str] = []
    pr_period_caption = ""

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
        pr_block = None
        if include_pr_scope:
            allow = list(pr_active_uuids) if pr_active_uuids is not None else None
            pr_block = build_category_burndown_block(
                client,
                tenant=tenant,
                projects=projects,
                leaf_namespaces=leaf_namespaces,
                path_options=path_options,
                tag_catalog=tag_catalog,
                category_key=key,
                lookback=PR_LOOKBACK_WEEKS,
                min_projects=min_projects,
                max_workers=max_workers,
                categories=pr_week_categories or None,
                period_caption=pr_period_caption or None,
                context_scope=SCOPE_PR,
                project_uuid_allowlist=allow,
            )
            if not pr_week_categories:
                pr_week_categories = list(
                    (
                        ((pr_block.get("seriesFilters") or {}).get("perPath") or {})
                        .get("all", {})
                        .get("all", {})
                        .get("all")
                        or {}
                    ).get("categories")
                    or []
                )
            pr_period_caption = str(pr_block.get("periodCaption") or pr_period_caption)
        by_category[key] = attach_main_pr_scopes(
            block,
            pr_block,
            pr_active_uuids=pr_active_uuids,
        )
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
        "prActiveProjectUuids": list(pr_active_uuids or []),
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
