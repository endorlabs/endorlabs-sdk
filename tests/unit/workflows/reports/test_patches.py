"""Unit tests for Endor Patches report analyze helpers."""

from __future__ import annotations

import json
from pathlib import Path

from endorlabs.workflows.reports.analyze.patches import (
    JAVA_DENOM_FILTER,
    _build_families,
    _finding_risk,
    _patch_units,
    empty_patches_report,
)
from endorlabs.workflows.reports.export.csv.packet_exports import (
    patches_family_rows,
    patches_unit_rows,
)
from endorlabs.workflows.reports.schemas.packet_v0 import PATCHES_RUN_BUCKET


def test_patches_run_bucket() -> None:
    assert PATCHES_RUN_BUCKET == "patches-reports"


def test_java_denom_filter_excludes_dismissed() -> None:
    assert "spec.dismiss != true" in JAVA_DENOM_FILTER
    assert "ECOSYSTEM_MAVEN" in JAVA_DENOM_FILTER


def test_finding_risk_weights() -> None:
    # Crit/High already scoped; RF > RD > PRF; PRF is not "reachable".
    assert (
        _finding_risk(
            {
                "severity": "CRITICAL",
                "reachable_function": True,
                "potentially_reachable_function": False,
            }
        )
        == 3.0
    )  # 2.0 x 1.5
    assert (
        _finding_risk(
            {
                "severity": "CRITICAL",
                "reachable_function": False,
                "reachable_dependency": True,
                "potentially_reachable_function": True,
            }
        )
        == 2.5
    )  # 2.0 x 1.25 — RD beats PRF
    assert (
        _finding_risk(
            {
                "severity": "CRITICAL",
                "reachable_function": False,
                "potentially_reachable_function": True,
            }
        )
        == 2.0
    )  # 2.0 x 1.0 - PRF is not "reachable"
    assert (
        _finding_risk(
            {
                "severity": "HIGH",
                "reachable_function": False,
                "potentially_reachable_function": False,
            }
        )
        == 0.75
    )  # 1.0 x 0.75


def test_build_families_separates_rf_from_prf() -> None:
    rows = [
        {
            "package_name": "mvn://org.example:lib-a",
            "current_version": "1.0.0",
            "finding_uuid": "rf1",
            "severity": "CRITICAL",
            "patch_status": "available",
            "reachable_function": True,
            "potentially_reachable_function": False,
            "project_uuid": "p1",
        },
        {
            "package_name": "mvn://org.example:lib-a",
            "current_version": "1.0.0",
            "finding_uuid": "prf1",
            "severity": "CRITICAL",
            "patch_status": "available",
            "reachable_function": False,
            "potentially_reachable_function": True,
            "project_uuid": "p1",
        },
        {
            "package_name": "mvn://org.example:lib-a",
            "current_version": "1.0.0",
            "finding_uuid": "rd1",
            "severity": "HIGH",
            "patch_status": "available",
            "reachable_function": False,
            "potentially_reachable_function": False,
            "reachable_dependency": True,
            "project_uuid": "p2",
        },
    ]
    families = _build_families(rows, top_n=5)
    vr = families[0]["version_rows"][0]
    assert vr["reachable_function"] == 1
    assert vr["potentially_reachable_function"] == 1
    assert vr["reachable_dependency"] == 1
    assert vr["reachable"] == 1  # RF-only alias
    assert vr["risk_available"] == 3.0 + 2.0 + 1.25


def test_build_families_mixed_version_and_ranking() -> None:
    rows = [
        {
            "package_name": "mvn://org.example:lib-a",
            "current_version": "1.0.0",
            "finding_uuid": "a1",
            "severity": "CRITICAL",
            "patch_status": "available",
            "reachable_function": True,
            "potentially_reachable_function": False,
            "project_uuid": "p1",
        },
        {
            "package_name": "mvn://org.example:lib-b",
            "current_version": "2.0.0",
            "finding_uuid": "b1",
            "severity": "HIGH",
            "patch_status": "available",
            "reachable_function": False,
            "potentially_reachable_function": False,
            "project_uuid": "p2",
        },
        {
            "package_name": "mvn://org.example:lib-b",
            "current_version": "2.0.0",
            "finding_uuid": "b2",
            "severity": "HIGH",
            "patch_status": "to_request_inferred",
            "reachable_function": False,
            "potentially_reachable_function": False,
            "project_uuid": "p2",
        },
    ]
    families = _build_families(rows, top_n=5)
    assert [f["family"] for f in families] == [
        "mvn://org.example:lib-a",
        "mvn://org.example:lib-b",
    ]
    lib_b = families[1]
    mixed = next(v for v in lib_b["version_rows"] if v["version"] == "2.0.0")
    assert mixed["available"] == 1
    assert mixed["to_request"] == 1
    assert mixed["findings"] == 2
    assert mixed["critical"] == 0
    assert mixed["high"] == 2
    assert mixed["projects"] == 1
    assert lib_b["findings"] == 2
    assert lib_b["available_findings"] == 1
    assert lib_b["to_request_findings"] == 1
    assert lib_b["projects"] == 1
    # To Request-only project still counts toward family projects.
    rows_proj = [
        *rows,
        {
            "package_name": "mvn://org.example:lib-b",
            "current_version": "2.0.0",
            "finding_uuid": "b3",
            "severity": "HIGH",
            "patch_status": "to_request_inferred",
            "reachable_function": False,
            "potentially_reachable_function": False,
            "project_uuid": "p3",
        },
    ]
    lib_b2 = _build_families(rows_proj, top_n=5)[1]
    assert lib_b2["projects"] == 2
    assert lib_b2["findings"] == 3
    units = _patch_units(families)
    assert any(u["to_request"] == 1 and u["available"] == 1 for u in units)


def test_empty_patches_and_csv_rows() -> None:
    empty = empty_patches_report()
    assert empty["families"] == []
    assert "estate_java_findings_legacy" not in empty
    cube = {"reports": {"patches": empty}}
    assert patches_family_rows(cube) == []
    assert patches_unit_rows(cube) == []


def test_render_packet_with_empty_patches_slice(tmp_path: Path) -> None:
    from endorlabs.workflows.reports.export.html.render import render_report_packet

    fixture = (
        Path(__file__).resolve().parent / "fixtures" / "example_tenant_packet.cube.json"
    )
    cube = json.loads(fixture.read_text(encoding="utf-8"))
    cube["reports"]["patches"] = empty_patches_report()
    written = render_report_packet(cube, tmp_path)
    patches_html = tmp_path / "05-endor-patches.html"
    assert patches_html in written
    text = patches_html.read_text(encoding="utf-8")
    assert 'id="denomMode"' in text
    assert "assets/endor-wordmark.png" in text
    assert "chart.umd.min.js" not in text
    assert "site-footer" in text
