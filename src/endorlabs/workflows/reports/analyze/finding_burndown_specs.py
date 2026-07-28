"""Category specs for FindingLog burndown matrices (SCA + code findings).

Each spec drives the same ``build_category_burndown_block`` path: base filter,
severity×facet cells, path/tag redistribute. SCA uses ``expand="reach"`` so
``all`` stays RF+PRF and ``unreachable`` is derived.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from endorlabs.filters import (
    FALSE_POSITIVE_TAG_CLAUSE,
    INVALID_SECRET_TAG_CLAUSE,
    TRUE_POSITIVE_TAG_CLAUSE,
    VALID_SECRET_TAG_CLAUSE,
    ai_sast_log_base_filter,
    main_context_vulnerability_filter,
    sast_log_base_filter,
    secrets_log_base_filter,
)
from endorlabs.workflows.findings.finding_log_trends import (
    FINDING_CRITERIA,
    SEVERITY_REACH_CELLS,
)

CATEGORY_SCA = "sca"
CATEGORY_SAST = "sast"
CATEGORY_AI_SAST = "ai_sast"
CATEGORY_SECRETS = "secrets"

CODE_CATEGORIES: tuple[str, ...] = (
    CATEGORY_SAST,
    CATEGORY_AI_SAST,
    CATEGORY_SECRETS,
)

SCA_FACET_KEYS: tuple[str, ...] = (
    "all",
    "reachable",
    "prf",
    "prd",
    "unreachable",
    "unreachable_function",
    "unreachable_dependency",
)
SAST_FACET_KEYS: tuple[str, ...] = ("all", "true_positive", "false_positive")
AI_SAST_FACET_KEYS: tuple[str, ...] = ("all",)
SECRETS_FACET_KEYS: tuple[str, ...] = ("all", "valid", "invalid")

SAST_CRITERIA = (
    "Critical/High · main context · FINDING_CATEGORY_SAST · "
    "triage facets (all / true_positive / false_positive)"
)
AI_SAST_CRITERIA = (
    "Critical/High · main context · FINDING_CATEGORY_SAST + FINDING_TAGS_AI "
    "(AI detection agent)"
)
SECRETS_CRITERIA = (
    "Critical/High · main context · FINDING_CATEGORY_SECRETS · "
    "validity facets (all / valid / invalid)"
)


def sev_facet_cells(
    facets: tuple[tuple[str, str], ...],
) -> tuple[tuple[str, str, str, str], ...]:
    """Build Crit/High × facet cell rows ``(sev, facet, level, clause)``."""
    cells: list[tuple[str, str, str, str]] = []
    for sev, level in (("critical", "CRITICAL"), ("high", "HIGH")):
        for facet, clause in facets:
            cells.append((sev, facet, level, clause))
    return tuple(cells)


SAST_CELLS = sev_facet_cells(
    (
        ("all", ""),
        ("true_positive", TRUE_POSITIVE_TAG_CLAUSE),
        ("false_positive", FALSE_POSITIVE_TAG_CLAUSE),
    )
)
AI_SAST_CELLS = sev_facet_cells((("all", ""),))
SECRETS_CELLS = sev_facet_cells(
    (
        ("all", ""),
        ("valid", VALID_SECRET_TAG_CLAUSE),
        ("invalid", INVALID_SECRET_TAG_CLAUSE),
    )
)

CategorySpec = dict[str, Any]

CATEGORY_SPECS: dict[str, CategorySpec] = {
    CATEGORY_SCA: {
        "base_filter": main_context_vulnerability_filter,
        "cells": SEVERITY_REACH_CELLS,
        "facet_keys": SCA_FACET_KEYS,
        "expand": "reach",
        "criteria": FINDING_CRITERIA,
        "seed_facet_clause": SEVERITY_REACH_CELLS[0][3],
    },
    CATEGORY_SAST: {
        "base_filter": sast_log_base_filter,
        "cells": SAST_CELLS,
        "facet_keys": SAST_FACET_KEYS,
        "expand": "severity",
        "criteria": SAST_CRITERIA,
        "seed_facet_clause": "",
    },
    CATEGORY_AI_SAST: {
        "base_filter": ai_sast_log_base_filter,
        "cells": AI_SAST_CELLS,
        "facet_keys": AI_SAST_FACET_KEYS,
        "expand": "severity",
        "criteria": AI_SAST_CRITERIA,
        "seed_facet_clause": "",
    },
    CATEGORY_SECRETS: {
        "base_filter": secrets_log_base_filter,
        "cells": SECRETS_CELLS,
        "facet_keys": SECRETS_FACET_KEYS,
        "expand": "severity",
        "criteria": SECRETS_CRITERIA,
        "seed_facet_clause": "",
    },
}


def get_category_spec(category_key: str) -> CategorySpec:
    """Return a burndown category spec or raise ``KeyError``."""
    return CATEGORY_SPECS[category_key]


def base_filter_for(category_key: str) -> Callable[[], str]:
    return get_category_spec(category_key)["base_filter"]
