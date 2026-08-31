"""Unit tests for packet / patches default output directory naming."""

from __future__ import annotations

from endorlabs.workflows.reports.export.html.render import (
    default_packet_output_dir,
    default_patches_report_dir,
)


def test_default_packet_output_dir_uses_yyyy_mm_dd() -> None:
    path = default_packet_output_dir("example-tenant", date_suffix="2026-08-28")
    assert path.name == "example-tenant-2026-08-28"
    assert path.parent.name == "reports"


def test_default_patches_report_dir_uses_yyyy_mm_dd() -> None:
    path = default_patches_report_dir("example-tenant", date_suffix="2026-08-28")
    assert path.name == "example-tenant-2026-08-28"
    assert path.parent.name == "patches"
    assert path.parent.parent.name == "reports"


def test_default_packet_output_dir_today_suffix_shape() -> None:
    from endorlabs.context.paths import tenant_day_suffix

    path = default_packet_output_dir("example-tenant")
    assert path.name == f"example-tenant-{tenant_day_suffix()}"
