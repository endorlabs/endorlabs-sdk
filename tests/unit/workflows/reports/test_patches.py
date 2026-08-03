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
    assert (
        _finding_risk(
            {
                "severity": "CRITICAL",
                "reachable_function": True,
                "potentially_reachable_function": False,
            }
        )
        == 12.0
    )
    assert (
        _finding_risk(
            {
                "severity": "HIGH",
                "reachable_function": False,
                "potentially_reachable_function": False,
            }
        )
        == 2.0
    )


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
