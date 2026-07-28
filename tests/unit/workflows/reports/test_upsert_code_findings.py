"""Unit tests for code-findings packet upsert."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

from endorlabs.workflows.reports.bundles.executive_packet import (
    upsert_code_findings_burndown,
)


def test_upsert_code_findings_keeps_existing_slices() -> None:
    cube: dict[str, Any] = {
        "schema": "endor.report_packet.v0",
        "tenant": "example-tenant",
        "pulledAt": "2026-01-01T00:00:00+00:00",
        "pathOptions": ["all"],
        "leafNamespaces": ["example-tenant.child"],
        "tagCatalog": [],
        "reports": {
            "onboarding": {"allRegistrations": 1},
            "versionSprawl": {"estate": {"kept": True}},
            "scaBurndown": {"lookback": 13, "seriesFilters": {"perPath": {"all": {}}}},
            "findingsBurndown": {"lookback": 13},
        },
    }
    fake_code = {
        "lookback": 13,
        "byCategory": {"sast": {"facetKeys": ["all"]}},
        "tagSeriesMeta": {"seriesReadyCount": 0},
    }
    with (
        patch(
            "endorlabs.workflows.reports.bundles.executive_packet.discover_projects",
            return_value={
                "projects": [],
                "tagCatalog": [],
                "pathOptions": ["all", "example-tenant"],
                "leafNamespaces": ["example-tenant.child"],
            },
        ),
        patch(
            "endorlabs.workflows.reports.bundles.executive_packet."
            "build_code_findings_burndown_report",
            return_value=fake_code,
        ) as build,
    ):
        out = upsert_code_findings_burndown(MagicMock(), cube, lookback=13)

    build.assert_called_once()
    assert out["reports"]["onboarding"]["allRegistrations"] == 1
    assert out["reports"]["versionSprawl"]["estate"]["kept"] is True
    assert out["reports"]["scaBurndown"]["lookback"] == 13
    assert out["reports"]["codeFindingsBurndown"] is fake_code
    assert out["pathOptions"] == ["all", "example-tenant"]
