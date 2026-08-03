"""Unit tests for executive report packet render + pure builders."""

from __future__ import annotations

import json
from pathlib import Path

from endorlabs.workflows.findings.finding_log_trends import (
    empty_series_cell,
    sum_series_cells,
)
from endorlabs.workflows.reports.analyze.patches import empty_patches_report
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
        "03-sca-burndown.html",
        "04-sast-burndown.html",
        "05-endor-patches.html",
        "packet.cube.json",
        "README.txt",
    }
    assert (tmp_path / "assets" / "endor-logo.png").is_file()
    assert (tmp_path / "assets" / "endor-wordmark.png").is_file()
    data = tmp_path / "data"
    assert (data / "tag-gap-differentials.csv").is_file()
    assert (data / "path-gap-differentials.csv").is_file()
    assert (data / "code-path-gap-differentials.csv").is_file()
    assert (data / "code-tag-gap-differentials.csv").is_file()
    assert (data / "tag-catalog.csv").is_file()
    assert (data / "onboarding-weekly.csv").is_file()
    assert (data / "patches-top-families.csv").is_file()
    assert (data / "patches-versions.csv").is_file()
    assert (data / "patches-units-ranked.csv").is_file()
    assert (data / "EXPORTS.txt").is_file()
    gap_csv = (data / "tag-gap-differentials.csv").read_text(encoding="utf-8")
    assert "gap_delta" in gap_csv
    assert "team-alpha" in gap_csv
    fam_csv = (data / "patches-top-families.csv").read_text(encoding="utf-8")
    assert "jackson-databind" in fam_csv

    onboarding = (tmp_path / "01-onboarding.html").read_text(encoding="utf-8")
    sprawl = (tmp_path / "02-version-sprawl.html").read_text(encoding="utf-8")
    burndown = (tmp_path / "03-sca-burndown.html").read_text(encoding="utf-8")
    sast = (tmp_path / "04-sast-burndown.html").read_text(encoding="utf-8")
    patches = (tmp_path / "05-endor-patches.html").read_text(encoding="utf-8")
    readme = (tmp_path / "README.txt").read_text(encoding="utf-8")

    assert copy_mod.H1_ONBOARDING in onboarding
    assert "assets/endor-wordmark.png" in onboarding
    assert "footer-mark" in onboarding
    assert "site-header" in onboarding
    assert copy_mod.H1_VERSION_SPRAWL in sprawl
    assert "Direct only" in sprawl
    assert "Private only" in sprawl
    assert "Per-ecosystem summary" in sprawl
    assert copy_mod.H1_SCA_BURNDOWN in burndown
    assert copy_mod.H1_SAST_BURNDOWN in sast
    assert 'id="category"' in sast
    assert copy_mod.H1_ENDOR_PATCHES in patches
    assert copy_mod.PURPOSE_ENDOR_PATCHES in patches
    assert "Impact calculator" in patches
    assert 'id="denomMode"' in patches
    assert 'data-mode="fixable"' in patches
    assert 'data-mode="java"' in patches
    assert "Fixable findings" in patches
    assert "Java Crit/High estate" in patches
    assert "05-endor-patches.html" in onboarding
    assert "How to read these metrics" in onboarding
    assert copy_mod.STAT_WINDOW_NET in burndown
    assert copy_mod.PENDING_TAG_CAPTION in burndown
    assert copy_mod.MAIN_THROUGHPUT_LABEL in burndown
    assert copy_mod.TAG_HELP in burndown
    assert copy_mod.AVG_SCANS_PER_PROJECT_LABEL in burndown
    assert copy_mod.TAG_LEADERS_NARROWING in burndown
    assert copy_mod.TAG_LEADERS_WIDENING in burndown
    assert "Gap change" in burndown or "Period Δ" in burndown
    assert "gapTrendLabel" in burndown
    assert "Current gap" in burndown or "Period Δ" in burndown
    assert "team-alpha" in burndown
    assert "team-beta" in burndown
    assert "series pending" in burndown
    assert "Window net (CREATE−DELETE)" in readme
    assert "03-sca-burndown.html" in readme
    assert "04-sast-burndown.html" in readme
    assert "05-endor-patches.html" in readme
    # Chrome order matches Endor Patches: brand header → nav → h1; schema not in chrome.
    for page in (onboarding, sprawl, burndown, sast, patches):
        assert (
            page.index('class="site-header"')
            < page.index('class="nav"')
            < page.index("<h1>")
        )
        meta = page.split('<p class="meta">', 1)[1].split("</p>", 1)[0]
        assert "Schema " not in meta
        assert REPORT_PACKET_SCHEMA not in page

    for text in (onboarding, sprawl, burndown, sast, patches):
        assert "example-tenant" in text.lower()


def test_render_patches_only_omits_uncollected_pages(tmp_path: Path) -> None:
    cube = _load_cube()
    written = render_report_packet(cube, tmp_path, patches_only=True)
    names = {p.name for p in written}

    assert "05-endor-patches.html" in names
    for page in (
        "01-onboarding.html",
        "02-version-sprawl.html",
        "03-sca-burndown.html",
        "04-sast-burndown.html",
    ):
        assert page not in names
        assert not (tmp_path / page).exists()

    data = tmp_path / "data"
    assert (data / "patches-top-families.csv").is_file()
    # Packet-wide slices were never collected; header-only CSVs would mislead.
    assert not (data / "onboarding-weekly.csv").exists()
    assert not (data / "tag-gap-differentials.csv").exists()

    exports = (data / "EXPORTS.txt").read_text(encoding="utf-8")
    assert "patches-top-families.csv" in exports
    assert "onboarding-weekly.csv" not in exports

    readme = (tmp_path / "README.txt").read_text(encoding="utf-8")
    assert "05-endor-patches.html" in readme
    assert "01-onboarding.html" not in readme

    # Chart.js is only referenced by pages 01-04.
    assert not (tmp_path / "assets" / "chart.umd.min.js").exists()
    assert (tmp_path / "assets" / "endor-wordmark.png").is_file()


def test_render_empty_slices_explain_themselves(tmp_path: Path) -> None:
    """Skipped slices must say so rather than render silently empty furniture."""
    cube = _load_cube()
    cube["reports"]["onboarding"] = {"projects": [], "cadence": {}}
    cube["reports"]["versionSprawl"] = {"histKeys": [], "ecosystems": [], "estate": {}}
    cube["reports"]["scaBurndown"] = {"seriesFilters": {"perPath": {}}}
    cube["reports"].pop("findingsBurndown", None)
    cube["reports"]["patches"] = empty_patches_report()
    render_report_packet(cube, tmp_path)

    onboarding = (tmp_path / "01-onboarding.html").read_text(encoding="utf-8")
    sprawl = (tmp_path / "02-version-sprawl.html").read_text(encoding="utf-8")
    burndown = (tmp_path / "03-sca-burndown.html").read_text(encoding="utf-8")
    patches = (tmp_path / "05-endor-patches.html").read_text(encoding="utf-8")

    assert 'id="emptyNotice"' in onboarding
    assert "No project inventory in this packet" in onboarding
    assert "No dependency inventory in this packet" in sprawl
    assert "No SCA burndown series in this packet" in burndown
    assert 'id="patchesEmpty"' in patches
    assert "No Endor Patch data in this packet" in patches


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
            ("npm://example-pkg", "1.0.0", True, True),
            ("npm://example-pkg", "2.0.0", False, True),
            ("pypi://example-lib", "0.1.0", True, False),
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
    estate_all = report["estate"]["all"]["all"]["all"]
    assert estate_all["p"] == 2
    assert report["estate"]["all"]["direct"]["all"]["p"] == 2
    assert report["estate"]["all"]["transitive"]["all"]["p"] == 1
    assert report["estate"]["all"]["all"]["public"]["p"] == 1
    assert report["estate"]["all"]["all"]["private"]["p"] == 1
    assert "team-alpha" in report["perTag"]
    assert "team-beta" in report["perTag"]
    assert "npm" in report["ecosystems"]
    assert "PyPI" in report["ecosystems"]
