"""Unit tests for EndorLicense entitlement gating and packet page omission."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

from endorlabs.workflows.reports.analyze.license_entitlements import (
    FEATURE_ENDOR_PATCHING,
    FEATURE_SAST,
    FEATURE_SECRETS,
    SKIP_REASON_NOT_ENTITLED,
    entitled_code_categories,
    feature_types_from_license,
    has_endor_patching,
)
from endorlabs.workflows.reports.analyze.patches import empty_patches_report
from endorlabs.workflows.reports.bundles.executive_packet import build_report_packet
from endorlabs.workflows.reports.export.html.render import render_report_packet

FIXTURES = Path(__file__).resolve().parent / "fixtures"
CUBE_PATH = FIXTURES / "example_tenant_packet.cube.json"


def test_feature_types_from_license_skips_expired_and_excluded() -> None:
    now = datetime(2026, 8, 31, tzinfo=UTC)
    row = {
        "spec": {
            "license_info": [
                {
                    "type": FEATURE_SAST,
                    "expiration_time": (now + timedelta(days=30)).isoformat(),
                },
                {
                    "type": FEATURE_SECRETS,
                    "expiration_time": (now - timedelta(days=1)).isoformat(),
                },
                {"type": FEATURE_ENDOR_PATCHING},
            ],
            "excluded_feature_types": [FEATURE_ENDOR_PATCHING],
        }
    }
    feats = feature_types_from_license(row, now=now)
    assert feats == {FEATURE_SAST}
    assert entitled_code_categories(feats) == ["sast"]
    assert not has_endor_patching(feats)


def test_build_skips_code_and_patches_when_not_entitled() -> None:
    client = MagicMock()
    discovered = {
        "projects": [
            {
                "uuid": "proj-1",
                "name": "https://github.com/org/repo.git",
                "namespace": "example-tenant",
                "tags": [],
                "create_time": "2026-01-01T00:00:00Z",
                "is_sbom": False,
            }
        ],
        "tagCatalog": [],
        "tagCounts": {},
        "leafNamespaces": ["example-tenant"],
        "pathOptions": ["all", "example-tenant"],
    }
    with (
        patch(
            "endorlabs.workflows.reports.bundles.executive_packet.discover_projects",
            return_value=discovered,
        ),
        patch(
            "endorlabs.workflows.reports.bundles.executive_packet.build_onboarding_report",
            return_value={"projectCount": 1, "projects": []},
        ),
        patch(
            "endorlabs.workflows.reports.analyze.onboarding_cadence.collect_onboarding_cadence",
            return_value={},
        ),
        patch(
            "endorlabs.workflows.reports.bundles.executive_packet.collect_leaf_pairs",
            return_value=[],
        ),
        patch(
            "endorlabs.workflows.reports.bundles.executive_packet.build_version_sprawl_report",
            return_value={
                "histKeys": [],
                "ecosystems": [],
                "estate": {},
                "perPath": {},
                "perTag": {},
            },
        ),
        patch(
            "endorlabs.workflows.reports.bundles.executive_packet.build_sca_burndown_report",
            return_value={
                "lookback": 13,
                "tagSeriesMeta": {},
                "throughput": {},
                "seriesFilters": {},
                "tagSeries": {},
            },
        ),
        patch(
            "endorlabs.workflows.reports.bundles.executive_packet.build_code_findings_burndown_report",
        ) as code_mock,
        patch(
            "endorlabs.workflows.reports.bundles.executive_packet.collect_patches_report",
        ) as patches_mock,
        patch(
            "endorlabs.workflows.reports.bundles.executive_packet.fetch_license_feature_types",
            return_value={"ENDOR_LICENSE_FEATURE_TYPE_SCA"},
        ),
    ):
        cube = build_report_packet(
            client,
            "example-tenant",
            include_code_findings_burndown=True,
            include_patches=True,
        )

    code_mock.assert_not_called()
    patches_mock.assert_not_called()
    assert cube["reportsMeta"]["codeFindingsBurndown"] == {
        "status": "skipped",
        "reason": SKIP_REASON_NOT_ENTITLED,
    }
    assert cube["reportsMeta"]["patches"] == {
        "status": "skipped",
        "reason": SKIP_REASON_NOT_ENTITLED,
    }


def test_render_omits_skipped_sast_and_patches_pages(tmp_path: Path) -> None:
    import json

    cube = json.loads(CUBE_PATH.read_text(encoding="utf-8"))
    cube["reportsMeta"] = {
        "codeFindingsBurndown": {
            "status": "skipped",
            "reason": SKIP_REASON_NOT_ENTITLED,
        },
        "patches": {"status": "skipped", "reason": "opt_in"},
    }
    cube["reports"]["patches"] = empty_patches_report()
    written = render_report_packet(cube, tmp_path)
    names = {p.name for p in written}
    assert "01-onboarding.html" in names
    assert "03-sca-burndown.html" in names
    assert "04-sast-burndown.html" not in names
    assert "05-endor-patches.html" not in names
    onboarding = (tmp_path / "01-onboarding.html").read_text(encoding="utf-8")
    assert "04-sast-burndown.html" not in onboarding
    assert "05-endor-patches.html" not in onboarding
    readme = (tmp_path / "README.txt").read_text(encoding="utf-8")
    assert "04-sast-burndown.html" not in readme
    assert "05-endor-patches.html" not in readme
    assert not (tmp_path / "data" / "code-path-gap-differentials.csv").exists()
    assert not (tmp_path / "data" / "patches-top-families.csv").exists()
