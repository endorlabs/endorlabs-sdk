"""Unit tests for executive report packet render + pure builders."""

from __future__ import annotations

import json
from pathlib import Path

from endorlabs.workflows.findings.finding_log_trends import (
    empty_series_cell,
    sum_series_cells,
)
from endorlabs.workflows.reports.analyze.projects import (
    build_onboarding_report,
    normalize_project_row,
    path_options_from_namespaces,
)
from endorlabs.workflows.reports.analyze.sprawl import build_version_sprawl_report
from endorlabs.workflows.reports.export.html import copy as copy_mod
from endorlabs.workflows.reports.export.html.render import render_report_packet
from endorlabs.workflows.reports.schemas.packet_v0 import (
    REPORT_PACKET_SCHEMA,
    hist_bucket,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures"
CUBE_PATH = FIXTURES / "example_tenant_packet.cube.json"


def _load_cube() -> dict:
    return json.loads(CUBE_PATH.read_text(encoding="utf-8"))


def _assert_portable_fixture_namespaces(cube: dict) -> None:
    assert cube["tenant"] == "example-tenant"
    for key in ("pathOptions", "leafNamespaces"):
        for ns in cube.get(key, []):
            if ns == "all":
                continue
            assert str(ns).startswith("example-tenant"), ns
    reports = cube.get("reports", {})
    if not isinstance(reports, dict):
        return
    for report in reports.values():
        if not isinstance(report, dict):
            continue
        for bucket in ("hierarchyAll", "hierarchyDistinct", "byNamespace"):
            for row in report.get(bucket, []) or []:
                if isinstance(row, dict) and "namespace" in row:
                    assert str(row["namespace"]).startswith("example-tenant"), row


def test_fixture_schema_and_portable_literals() -> None:
    raw = CUBE_PATH.read_text(encoding="utf-8")
    cube = json.loads(raw)
    assert cube["schema"] == REPORT_PACKET_SCHEMA
    _assert_portable_fixture_namespaces(cube)
    assert "example-tenant" in raw


def test_render_packet_captions_and_glossary(tmp_path: Path) -> None:
    cube = _load_cube()
    written = render_report_packet(cube, tmp_path)
    names = {p.name for p in written}
    assert names >= {
        "01-onboarding.html",
        "02-version-sprawl.html",
        "03-findings-burndown.html",
        "packet.cube.json",
        "README.txt",
    }
    assert (tmp_path / "assets" / "endor-logo.png").is_file()
    assert (tmp_path / "assets" / "endor-wordmark.png").is_file()

    onboarding = (tmp_path / "01-onboarding.html").read_text(encoding="utf-8")
    sprawl = (tmp_path / "02-version-sprawl.html").read_text(encoding="utf-8")
    burndown = (tmp_path / "03-findings-burndown.html").read_text(encoding="utf-8")
    readme = (tmp_path / "README.txt").read_text(encoding="utf-8")

    assert copy_mod.H1_ONBOARDING in onboarding
    assert "assets/endor-wordmark.png" in onboarding
    assert "footer-mark" in onboarding
    assert "site-header" in onboarding
    assert copy_mod.H1_VERSION_SPRAWL in sprawl
    assert copy_mod.H1_FINDINGS_BURNDOWN in burndown
    assert "How to read these metrics" in onboarding
    assert copy_mod.STAT_WINDOW_NET in burndown
    assert copy_mod.PENDING_TAG_CAPTION in burndown
    assert copy_mod.MAIN_THROUGHPUT_LABEL in burndown
    assert copy_mod.TAG_HELP in burndown
    assert "team-alpha" in burndown
    assert "team-beta" in burndown
    assert "series pending" in burndown
    assert "Window net (CREATE−DELETE)" in readme
    assert REPORT_PACKET_SCHEMA in onboarding

    for text in (onboarding, sprawl, burndown):
        assert "example-tenant" in text.lower()


def test_path_options_and_normalize() -> None:
    opts = path_options_from_namespaces(["example-tenant.child.leaf"])
    assert opts[0] == "all"
    assert "example-tenant" in opts
    assert "example-tenant.child" in opts
    assert "example-tenant.child.leaf" in opts

    row = normalize_project_row(
        {
            "uuid": "00000000-0000-4000-8000-000000000099",
            "meta": {
                "name": "https://github.com/org/repo.git",
                "tags": ["team-alpha", ""],
                "create_time": "2026-01-10T00:00:00Z",
            },
            "tenant_meta": {"namespace": "example-tenant.child"},
        }
    )
    assert row["tags"] == ["team-alpha"]
    assert row["namespace"] == "example-tenant.child"


def test_onboarding_distinct_vs_all() -> None:
    projects = [
        {
            "uuid": "00000000-0000-4000-8000-000000000001",
            "name": "https://github.com/org/repo.git",
            "namespace": "example-tenant.child",
            "tags": [],
            "create_time": "2026-01-06T12:00:00Z",
        },
        {
            "uuid": "00000000-0000-4000-8000-000000000002",
            "name": "https://github.com/org/repo.git",
            "namespace": "example-tenant.child",
            "tags": [],
            "create_time": "2026-01-13T12:00:00Z",
        },
        {
            "uuid": "00000000-0000-4000-8000-000000000003",
            "name": "https://github.com/org/other.git",
            "namespace": "example-tenant.child",
            "tags": [],
            "create_time": "2026-01-13T12:00:00Z",
        },
    ]
    report = build_onboarding_report(projects)
    assert report["allRegistrations"] == 3
    assert report["distinctRepositories"] == 2
    assert report["duplicateRegistrations"] == 1


def test_sum_series_and_hist_bucket() -> None:
    cats = ["2026-01-05", "2026-01-12"]
    a = empty_series_cell(cats, "2w")
    a["weeklyNew"] = [1, 2]
    a["weeklyResolved"] = [0, 1]
    b = empty_series_cell(cats, "2w")
    b["weeklyNew"] = [3, 0]
    b["weeklyResolved"] = [1, 0]
    merged = sum_series_cells([a, b], categories=cats, period_caption="2w")
    assert merged["weeklyNew"] == [4, 2]
    assert merged["weeklyResolved"] == [1, 1]
    assert merged["cumulativeNew"] == [4, 6]
    assert merged["gaps"] == [3, 4]
    assert hist_bucket(1) == "1"
    assert hist_bucket(3) == "2-3"
    assert hist_bucket(30) == "26+"


def test_version_sprawl_tag_uuid_rollups() -> None:
    leaf_pairs = {
        "example-tenant.child": [
            ("npm://example-pkg", "1.0.0"),
            ("npm://example-pkg", "2.0.0"),
            ("pypi://example-lib", "0.1.0"),
        ]
    }
    projects = [
        {
            "uuid": "00000000-0000-4000-8000-000000000001",
            "name": "https://github.com/org/a.git",
            "namespace": "example-tenant.child",
            "tags": ["team-alpha"],
        },
        {
            "uuid": "00000000-0000-4000-8000-000000000002",
            "name": "https://github.com/org/b.git",
            "namespace": "example-tenant.child",
            "tags": ["team-beta"],
        },
    ]
    catalog = [
        {
            "tag": "team-alpha",
            "projectCount": 1,
            "projectUuids": ["00000000-0000-4000-8000-000000000001"],
        },
        {
            "tag": "team-beta",
            "projectCount": 1,
            "projectUuids": ["00000000-0000-4000-8000-000000000002"],
        },
    ]
    report = build_version_sprawl_report(
        leaf_pairs=leaf_pairs,
        path_options=["all", "example-tenant", "example-tenant.child"],
        projects=projects,
        tag_catalog=catalog,
    )
    assert report["estate"]["all"]["all"]["p"] == 2
    assert "team-alpha" in report["perTag"]
    assert "team-beta" in report["perTag"]
