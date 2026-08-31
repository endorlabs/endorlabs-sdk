"""Category specs for FindingLog burndown matrices (SCA + code findings).

Each spec drives the same ``build_category_burndown_block`` path: base filter,
severity×facet cells, path/tag redistribute. SCA uses ``expand="reach"`` so
``any`` is unfiltered and ``all`` stays RF+PRF. Dependency-axis reach tags are
omitted (function reach implies dependency reach in the product model).

Code findings: OpenGrep vs AI-SAST share TP/FP triage facets; Secrets uses
valid/invalid only (no TP/FP).
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
    EXACT_SEVERITY_LEVELS,
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

# SCA function-reach options. ``any`` = no reach tag filter (default);
# ``all`` = RF+PRF. Dependency-axis options omitted (RF implies RD).
SCA_FACET_KEYS: tuple[str, ...] = (
    "any",
    "all",
    "reachable",
    "prf",
    "unreachable_function",
)
# Shared triage facets for OpenGrep and AI-SAST (not Secrets).
TRIAGE_FACET_KEYS: tuple[str, ...] = ("all", "true_positive", "false_positive")
SAST_FACET_KEYS: tuple[str, ...] = TRIAGE_FACET_KEYS
AI_SAST_FACET_KEYS: tuple[str, ...] = TRIAGE_FACET_KEYS
SECRETS_FACET_KEYS: tuple[str, ...] = ("all", "valid", "invalid")

SAST_CRITERIA = (
    "All severities (Critical–Low) · main context · OpenGrep SAST "
    "(FINDING_CATEGORY_SAST without FINDING_TAGS_AI) · "
    "triage facets (all / true_positive / false_positive); "
    "UI severity thresholds (Critical+ / High+ / Medium+ / All)"
)
AI_SAST_CRITERIA = (
    "All severities (Critical–Low) · main context · AI-SAST detection "
    "(FINDING_CATEGORY_SAST + FINDING_TAGS_AI) · "
    "triage facets (all / true_positive / false_positive); "
    "UI severity thresholds (Critical+ / High+ / Medium+ / All)"
)
SECRETS_CRITERIA = (
    "All severities (Critical–Low) · main context · FINDING_CATEGORY_SECRETS · "
    "validity facets (all / valid / invalid); no TP/FP triage facets; "
    "UI severity thresholds (Critical+ / High+ / Medium+ / All)"
)


def sev_facet_cells(
    facets: tuple[tuple[str, str], ...],
) -> tuple[tuple[str, str, str, str], ...]:
    """Build Crit/High/Med/Low × facet cell rows ``(sev, facet, level, clause)``."""
    cells: list[tuple[str, str, str, str]] = []
    for sev, level in EXACT_SEVERITY_LEVELS:
        for facet, clause in facets:
            cells.append((sev, facet, level, clause))
    return tuple(cells)


TRIAGE_CELLS = sev_facet_cells(
    (
        ("all", ""),
        ("true_positive", TRUE_POSITIVE_TAG_CLAUSE),
        ("false_positive", FALSE_POSITIVE_TAG_CLAUSE),
    )
)
SAST_CELLS = TRIAGE_CELLS
AI_SAST_CELLS = TRIAGE_CELLS
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
