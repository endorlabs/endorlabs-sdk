"""Unit tests for packet slice isolation."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from endorlabs.workflows.reports.bundles.executive_packet import build_report_packet


def test_build_report_packet_continues_after_sca_failure() -> None:
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
            side_effect=TimeoutError("read timed out"),
        ),
        patch(
            "endorlabs.workflows.reports.bundles.executive_packet.build_code_findings_burndown_report",
            return_value={
                "lookback": 13,
                "interval": "week",
                "periodCaption": "",
                "categories": [],
                "byCategory": {},
                "tagSeriesMeta": {},
            },
        ),
        patch(
            "endorlabs.workflows.reports.bundles.executive_packet.collect_patches_report",
            return_value={"families": [], "patch_units": []},
        ) as patches_mock,
        patch(
            "endorlabs.workflows.reports.bundles.executive_packet.fetch_license_feature_types",
            return_value={
                "ENDOR_LICENSE_FEATURE_TYPE_SAST",
                "ENDOR_LICENSE_FEATURE_TYPE_AI_SAST",
                "ENDOR_LICENSE_FEATURE_TYPE_SECRETS",
                "ENDOR_LICENSE_FEATURE_TYPE_ENDOR_PATCHING",
            },
        ),
    ):
        cube = build_report_packet(
            client,
            "example-tenant",
            include_version_sprawl=True,
            include_sca_burndown=True,
            include_code_findings_burndown=True,
            include_patches=True,
        )

    assert "scaBurndown" in (cube.get("dataGaps") or [])
    assert (cube.get("reportsMeta") or {}).get("scaBurndown", {}).get(
        "status"
    ) == "failed"
    assert (cube.get("reportsMeta") or {}).get("codeFindingsBurndown", {}).get(
        "status"
    ) == "ok"
    assert (cube.get("reportsMeta") or {}).get("patches", {}).get("status") == "ok"
    patches_mock.assert_called_once()
    kwargs = patches_mock.call_args.kwargs
    assert "shards" in kwargs
    assert kwargs["shards"]
    assert kwargs["shards"][0].project_uuid == "proj-1"
    assert "leaf_namespaces" in kwargs
