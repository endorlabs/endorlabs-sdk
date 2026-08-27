"""Unit tests for packet / patches default output directory naming."""

from __future__ import annotations

from endorlabs.workflows.reports.export.html.render import (
    default_packet_output_dir,
    default_patches_report_dir,
)


def test_default_packet_output_dir_appends_mmddyy() -> None:
    path = default_packet_output_dir("example-tenant", date_suffix="082126")
    assert path.name == "example-tenant-executive-packet-082126"
    assert path.parent.name == "executive-report-packet"


def test_default_patches_report_dir_appends_mmddyy() -> None:
    path = default_patches_report_dir("example-tenant", date_suffix="082126")
    assert path.name == "example-tenant-082126"
    assert path.parent.name == "patches-reports"


def test_default_packet_output_dir_today_suffix_shape() -> None:
    path = default_packet_output_dir("example-tenant")
    assert path.name.startswith("example-tenant-executive-packet-")
    suffix = path.name.rsplit("-", 1)[-1]
    assert len(suffix) == 6 and suffix.isdigit()
