"""Unit tests for the patch-fix report workflow."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from endorlabs.tools.list_sharding import ProjectShard
from endorlabs.workflows.findings.patch_fix_report import (
    _build_finding_filter,
    _compute_signal_breakdown,
    _extract_patch_rows,
    _filter_by_reachability,
    _finding_signal_flags,
    _rollup_patch_fix_rows,
    build_patch_fix_report,
    parse_args,
)


def _finding(
    uuid: str,
    *,
    project_uuid: str = "proj-1",
    target_package: str = "npm://hbs@4.2.0",
    target_version: str = "4.2.0",
    endor_patch_available: bool = False,
    finding_tags: list[str] | None = None,
    upgrade_list: list[dict[str, object]] | None = None,
    finding_type_name: str = "dependency_with_high_severity_vulnerabilities",
    vuln_id: str = "GHSA-test-0001",
    vuln_aliases: list[str] | None = None,
    level: str = "FINDING_LEVEL_HIGH",
    namespace: str = "example-tenant.child",
) -> dict[str, object]:
    return {
        "uuid": uuid,
        "meta": {
            "name": finding_type_name,
            "description": f"{vuln_id}: example summary",
        },
        "tenant_meta": {"namespace": namespace},
        "spec": {
            "project_uuid": project_uuid,
            "level": level,
            "extra_key": vuln_id,
            "target_dependency_package_name": target_package,
            "target_dependency_version": target_version,
            "finding_tags": finding_tags or [],
            "fixing_patch": {"endor_patch_available": endor_patch_available},
            "finding_metadata": {
                "vulnerability": {
                    "meta": {"name": vuln_id, "description": "example summary"},
                    "spec": {
                        "aliases": vuln_aliases or ["CVE-2024-0001"],
                        "summary": "example summary",
                    },
                }
            },
            "fixing_upgrades": (
                {"upgrade_list": upgrade_list} if upgrade_list is not None else None
            ),
        },
    }


def _upgrade_item(
    *,
    direct_dependency_name: str = "npm://hbs",
    from_version: str = "4.2.0",
    to_version: str = "4.2.1",
    upgrade_risk: str = "medium",
) -> dict[str, str]:
    return {
        "package_name": "npm://juice-shop@19.1.1",
        "direct_dependency_name": direct_dependency_name,
        "from_version": from_version,
        "to_version": to_version,
        "upgrade_risk": upgrade_risk,
    }


def test_build_finding_filter_default_gate_is_union() -> None:
    filt = _build_finding_filter(("FINDING_CATEGORY_VULNERABILITY",), None, gate="any")
    assert "spec.fixing_patch.endor_patch_available==true" in filt
    assert "spec.finding_tags contains FINDING_TAGS_FIX_AVAILABLE" in filt
    assert " or " in filt


def test_build_finding_filter_endor_patch_gate_is_strict() -> None:
    filt = _build_finding_filter(
        ("FINDING_CATEGORY_VULNERABILITY",), None, gate="endor-patch"
    )
    assert "spec.fixing_patch.endor_patch_available==true" in filt
    assert "FINDING_TAGS_FIX_AVAILABLE" not in filt


def test_build_finding_filter_fix_available_gate_is_broad_only() -> None:
    filt = _build_finding_filter(
        ("FINDING_CATEGORY_VULNERABILITY",), None, gate="fix-available"
    )
    assert "spec.finding_tags contains FINDING_TAGS_FIX_AVAILABLE" in filt
    assert "endor_patch_available" not in filt


def test_build_finding_filter_includes_severity_and_category() -> None:
    filt = _build_finding_filter(
        ("FINDING_CATEGORY_VULNERABILITY", "FINDING_CATEGORY_SCA"),
        ("critical", "high"),
        gate="any",
    )
    assert "FINDING_CATEGORY_VULNERABILITY" in filt
    assert "FINDING_CATEGORY_SCA" in filt
    assert "spec.level==FINDING_LEVEL_CRITICAL" in filt
    assert "spec.level==FINDING_LEVEL_HIGH" in filt


def test_finding_signal_flags_reads_tags_and_patch_fields() -> None:
    finding = _finding(
        "f-1",
        endor_patch_available=True,
        finding_tags=["FINDING_TAGS_FIX_AVAILABLE", "FINDING_TAGS_REACHABLE_FUNCTION"],
        upgrade_list=[_upgrade_item()],
    )

    flags = _finding_signal_flags(finding)

    assert flags == {
        "fix_available": True,
        "endor_patch_available": True,
        "has_upgrade_path": True,
        "reachable_function": True,
        "potentially_reachable_function": False,
    }


def test_filter_by_reachability_any_is_noop() -> None:
    findings = [_finding("f-1"), _finding("f-2")]
    assert _filter_by_reachability(findings, "any") == findings


def test_filter_by_reachability_reachable_keeps_tagged_only() -> None:
    findings = [
        _finding("f-1", finding_tags=["FINDING_TAGS_REACHABLE_FUNCTION"]),
        _finding("f-2", finding_tags=[]),
        _finding("f-3", finding_tags=["FINDING_TAGS_POTENTIALLY_REACHABLE_FUNCTION"]),
    ]

    kept = _filter_by_reachability(findings, "reachable")

    assert {f["uuid"] for f in kept} == {"f-1", "f-3"}


def test_filter_by_reachability_unreachable_keeps_untagged_only() -> None:
    findings = [
        _finding("f-1", finding_tags=["FINDING_TAGS_REACHABLE_FUNCTION"]),
        _finding("f-2", finding_tags=[]),
    ]

    kept = _filter_by_reachability(findings, "unreachable")

    assert {f["uuid"] for f in kept} == {"f-2"}


def test_compute_signal_breakdown_confirms_set_relationship() -> None:
    findings = [
        # patch available AND fix tag present
        _finding(
            "f-1",
            endor_patch_available=True,
            finding_tags=["FINDING_TAGS_FIX_AVAILABLE"],
        ),
        # fix tag only — a "patch to request" candidate
        _finding(
            "f-2",
            endor_patch_available=False,
            finding_tags=["FINDING_TAGS_FIX_AVAILABLE"],
        ),
        # patch available only (no fix tag) — also has an upgrade path
        _finding(
            "f-3",
            endor_patch_available=True,
            finding_tags=[],
            upgrade_list=[_upgrade_item()],
        ),
    ]

    breakdown = _compute_signal_breakdown(findings)

    assert breakdown["total_findings"] == 3
    assert breakdown["endor_patch_available_count"] == 2
    assert breakdown["fix_available_tag_count"] == 2
    assert breakdown["both_endor_patch_and_fix_tag_count"] == 1
    assert breakdown["neither_endor_patch_nor_fix_tag_count"] == 0
    assert breakdown["patches_to_request_count"] == 1  # f-2 only


def test_extract_patch_rows_flattens_upgrade_list() -> None:
    findings = [
        _finding(
            "f-1",
            upgrade_list=[_upgrade_item(to_version="4.2.1")],
        )
    ]

    rows = _extract_patch_rows(findings)

    assert len(rows) == 1
    row = rows[0]
    assert row["finding_uuid"] == "f-1"
    assert row["package_name"] == "npm://hbs"
    assert row["current_version"] == "4.2.0"
    assert row["patch_version"] == "4.2.1"
    assert row["vuln_id"] == "GHSA-test-0001"
    assert row["vuln_aliases"] == "CVE-2024-0001"
    assert row["severity"] == "HIGH"
    assert row["patch_status"] == "to_request_inferred"
    assert row["fix_available"] is False
    assert row["reachable_function"] is False


def test_extract_patch_rows_marks_available_status() -> None:
    findings = [
        _finding(
            "f-1",
            endor_patch_available=True,
            upgrade_list=[_upgrade_item()],
        )
    ]
    rows = _extract_patch_rows(findings)
    assert rows[0]["patch_status"] == "available"


def test_extract_patch_rows_skips_findings_without_upgrade_list() -> None:
    findings = [
        _finding("f-1", upgrade_list=None),
        _finding("f-2", upgrade_list=[]),
    ]

    rows = _extract_patch_rows(findings)

    assert rows == []


def test_extract_patch_rows_handles_multiple_candidates_per_finding() -> None:
    findings = [
        _finding(
            "f-1",
            upgrade_list=[
                _upgrade_item(direct_dependency_name="npm://hbs", to_version="4.2.1"),
                _upgrade_item(
                    direct_dependency_name="npm://pdfkit", to_version="0.18.0"
                ),
            ],
        )
    ]

    rows = _extract_patch_rows(findings)

    assert len(rows) == 2
    assert {row["package_name"] for row in rows} == {"npm://hbs", "npm://pdfkit"}


def test_rollup_patch_fix_rows_sorts_by_name_then_version() -> None:
    detail_rows = [
        {
            "finding_uuid": "f-2",
            "project_uuid": "p-1",
            "package_name": "npm://zeta",
            "current_version": "1.0.0",
            "patch_version": "2.0.0",
        },
        {
            "finding_uuid": "f-1",
            "project_uuid": "p-1",
            "package_name": "npm://alpha",
            "current_version": "2.0.0",
            "patch_version": "3.0.0",
        },
        {
            "finding_uuid": "f-3",
            "project_uuid": "p-1",
            "package_name": "npm://alpha",
            "current_version": "1.0.0",
            "patch_version": "2.0.0",
        },
    ]

    rows = _rollup_patch_fix_rows("tenant", detail_rows)

    assert [(r["package_name"], r["current_version"]) for r in rows] == [
        ("npm://alpha", "1.0.0"),
        ("npm://alpha", "2.0.0"),
        ("npm://zeta", "1.0.0"),
    ]


def test_rollup_patch_fix_rows_aggregates_counts() -> None:
    detail_rows = [
        {
            "finding_uuid": "f-1",
            "project_uuid": "p-1",
            "package_name": "npm://hbs",
            "current_version": "4.2.0",
            "patch_version": "4.2.1",
        },
        {
            "finding_uuid": "f-1",
            "project_uuid": "p-1",
            "package_name": "npm://hbs",
            "current_version": "4.2.0",
            "patch_version": "4.2.1",
        },
        {
            "finding_uuid": "f-2",
            "project_uuid": "p-2",
            "package_name": "npm://hbs",
            "current_version": "4.2.0",
            "patch_version": "4.2.2",
        },
    ]

    rows = _rollup_patch_fix_rows("tenant", detail_rows)

    assert len(rows) == 1
    row = rows[0]
    assert row["finding_count"] == 2  # distinct finding uuids, not raw row count
    assert row["distinct_patch_version_count"] == 2  # 4.2.1 and 4.2.2
    assert row["distinct_upgrade_path_count"] == 3  # raw candidate rows
    assert row["project_count"] == 2


def test_build_patch_fix_report_end_to_end() -> None:
    client = MagicMock()
    client.Query.Project.discover.return_value = SimpleNamespace(
        project_shards=lambda: [
            ProjectShard(project_uuid="p-1", namespace="tenant.child", label="a"),
        ]
    )
    client.Finding.list_by_project.return_value = [
        _finding(
            "f-1",
            project_uuid="p-1",
            upgrade_list=[_upgrade_item(to_version="4.2.1")],
        ),
        _finding("f-2", project_uuid="p-1", upgrade_list=None),
    ]

    result = build_patch_fix_report(client, "tenant")

    assert result.ok
    assert result.stats.project_count == 1
    assert result.stats.finding_count == 2
    assert result.stats.fixable_finding_count == 1
    assert result.signal_breakdown["total_findings"] == 2
    assert result.table.rows == [
        {
            "namespace": "tenant",
            "package_name": "npm://hbs",
            "current_version": "4.2.0",
            "patch_version": "4.2.1",
            "finding_count": 1,
            "distinct_patch_version_count": 1,
            "distinct_upgrade_path_count": 1,
            "project_count": 1,
        }
    ]


def test_build_patch_fix_report_no_projects_is_success_not_error() -> None:
    client = MagicMock()
    client.Query.Project.discover.return_value = SimpleNamespace(project_shards=list)

    result = build_patch_fix_report(client, "tenant")

    assert result.ok
    assert result.table.rows == []


def test_build_patch_fix_report_discovery_failure_is_error() -> None:
    client = MagicMock()
    client.Query.Project.discover.side_effect = RuntimeError("boom")

    result = build_patch_fix_report(client, "tenant")

    assert result.status == "error"
    assert "boom" in result.errors[0]


def test_build_patch_fix_report_rejects_invalid_gate() -> None:
    client = MagicMock()
    try:
        build_patch_fix_report(client, "tenant", gate="bogus")
    except ValueError as exc:
        assert "gate" in str(exc)
    else:
        raise AssertionError("expected ValueError for invalid gate")


def test_parse_args_defaults_and_gate_reachability_flags() -> None:
    args = parse_args(["--namespace", "tenant"])
    assert args.gate == "any"
    assert args.reachability == "any"

    args = parse_args(
        [
            "--namespace",
            "tenant",
            "--gate",
            "endor-patch",
            "--reachability",
            "reachable",
        ]
    )
    assert args.gate == "endor-patch"
    assert args.reachability == "reachable"


def test_parse_args_repeatable_category_and_severity() -> None:
    args = parse_args(
        [
            "--namespace",
            "tenant",
            "--finding-category",
            "FINDING_CATEGORY_SCA",
            "--finding-category",
            "FINDING_CATEGORY_VULNERABILITY",
            "--severity",
            "CRITICAL",
        ]
    )
    assert args.finding_categories == [
        "FINDING_CATEGORY_SCA",
        "FINDING_CATEGORY_VULNERABILITY",
    ]
    assert args.severities == ["CRITICAL"]
