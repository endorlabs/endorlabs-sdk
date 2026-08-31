"""Unit tests for patches opt-in and Java denom leaf reuse."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from endorlabs.workflows.reports.analyze.patches import count_java_maven_crit_high
from endorlabs.workflows.reports.analyze.projects import non_sbom_leaf_namespaces
from endorlabs.workflows.reports.bundles.executive_packet import build_report_packet
from endorlabs.workflows.reports.cli import _namespace_parent, _packet_parser


def test_non_sbom_leaf_namespaces_filters_sbom() -> None:
    projects = [
        {"uuid": "a", "namespace": "example-tenant.app", "is_sbom": False},
        {"uuid": "b", "namespace": "example-tenant.sbom", "is_sbom": True},
        {"uuid": "c", "namespace": "example-tenant.app", "is_sbom": False},
    ]
    assert non_sbom_leaf_namespaces(projects, fallback="example-tenant") == [
        "example-tenant.app"
    ]


def test_count_java_maven_crit_high_skips_discover_when_leaves_given() -> None:
    client = MagicMock()
    client.Finding.count.return_value = 3
    client.Query.Project.discover = MagicMock()
    total, n_leaves = count_java_maven_crit_high(
        client,
        "example-tenant",
        leaf_namespaces=["example-tenant.child"],
    )
    assert total == 3
    assert n_leaves == 1
    client.Query.Project.discover.assert_not_called()
    client.Finding.count.assert_called_once()


def test_build_report_packet_skips_patches_by_default() -> None:
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
        ) as patches_mock,
        patch(
            "endorlabs.workflows.reports.bundles.executive_packet.fetch_license_feature_types",
            return_value=None,
        ),
    ):
        cube = build_report_packet(client, "example-tenant")

    patches_mock.assert_not_called()
    assert (cube.get("reportsMeta") or {}).get("patches", {}).get("status") == "skipped"
    assert (cube.get("reportsMeta") or {}).get("patches", {}).get("reason") == "opt_in"


def test_packet_cli_patches_flag_present() -> None:
    from argparse import ArgumentParser

    parser = ArgumentParser()
    sub = parser.add_subparsers()
    packet = _packet_parser(sub, ns_parent=_namespace_parent())
    ns = packet.parse_args(["-n", "example-tenant", "--patches"])
    assert ns.patches is True
    assert ns.patches_only is False
