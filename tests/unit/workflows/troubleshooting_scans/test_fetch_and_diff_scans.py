"""Tests for fetch_scan_results and diff_scans modules."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from endorlabs.workflows.troubleshooting_scans import diff_scans, fetch_scan_results


def test_fetch_scan_results_requires_project_or_all_projects() -> None:
    args = SimpleNamespace(
        tenant="tenant.ns",
        project_uuid=None,
        project_name=None,
        namespace=None,
        all_projects=False,
        limit=10,
        scan_window=None,
        status_filter=None,
        output_dir=".tmp",
        timestamped=False,
    )
    mock_client = Mock()
    mock_client.Project.list.return_value = []
    with (
        patch(
            "endorlabs.workflows.troubleshooting_scans.fetch_scan_results.Client",
            return_value=mock_client,
        ),
        pytest.raises(ValueError, match="Provide --project-uuid or --project-name"),
    ):
        fetch_scan_results.run(args)


def test_fetch_scan_results_writes_raw_and_summary_artifacts() -> None:
    args = SimpleNamespace(
        tenant="tenant.ns",
        project_uuid="p1",
        project_name=None,
        namespace="tenant.ns",
        all_projects=False,
        limit=10,
        scan_window=5,
        status_filter="STATUS_SUCCESS",
        output_dir=".tmp",
        timestamped=False,
    )
    projects = [
        {
            "uuid": "p1",
            "tenant_meta": {"namespace": "tenant.ns"},
            "meta": {"name": "proj-1"},
        }
    ]
    mock_client = Mock()
    mock_client.Project.list.return_value = [
        Mock(model_dump=Mock(return_value=projects[0])),
    ]
    mock_client.ScanResult.list_by_project = Mock(return_value=[{"uuid": "scan-1"}])
    with (
        patch(
            "endorlabs.workflows.troubleshooting_scans.fetch_scan_results.Client",
            return_value=mock_client,
        ),
        patch(
            "endorlabs.workflows.troubleshooting_scans.fetch_scan_results.scan_result_metrics",
            return_value={"uuid": "scan-1"},
        ),
        patch(
            "endorlabs.workflows.troubleshooting_scans.fetch_scan_results.root_tenant",
            return_value="tenant",
        ),
        patch(
            "endorlabs.workflows.troubleshooting_scans.fetch_scan_results.write_json",
            side_effect=[Path(".tmp/raw.json"), Path(".tmp/summary.json")],
        ) as mock_write_json,
    ):
        result = fetch_scan_results.run(args)

    assert mock_write_json.call_count == 2
    assert result["scan_result_count"] == 1
    assert result["summary_artifact"].endswith("summary.json")


def test_diff_scans_run_raises_when_selected_pairs_missing() -> None:
    args = SimpleNamespace(
        input_pairs=".tmp/pairs.json",
        tenant="tenant.ns",
        namespace="tenant.ns",
        output_dir=".tmp",
        timestamped=False,
    )
    with (
        patch(
            "endorlabs.workflows.troubleshooting_scans.diff_scans.load_json",
            return_value={"selected_pairs": []},
        ),
        pytest.raises(ValueError, match="No selected pairs"),
    ):
        diff_scans.run(args)


def test_diff_scans_run_writes_both_artifacts() -> None:
    args = SimpleNamespace(
        input_pairs=".tmp/pairs.json",
        tenant="tenant.ns",
        namespace="tenant.ns",
        output_dir=".tmp",
        timestamped=False,
    )
    with (
        patch(
            "endorlabs.workflows.troubleshooting_scans.diff_scans.load_json",
            return_value={
                "selected_pairs": [
                    {
                        "primary_scan_result_uuid": "scan-a",
                        "secondary_scan_result_uuid": "scan-b",
                    }
                ]
            },
        ),
        patch(
            "endorlabs.workflows.troubleshooting_scans.diff_scans.Client",
            return_value=Mock(),
        ),
        patch(
            "endorlabs.workflows.troubleshooting_scans.diff_scans.fetch_scan_result",
            side_effect=[
                {"uuid": "scan-a", "spec": {}},
                {"uuid": "scan-b", "spec": {}},
            ],
        ),
        patch(
            "endorlabs.workflows.troubleshooting_scans.diff_scans.scan_result_metrics",
            side_effect=[
                {"uuid": "scan-a", "status": "STATUS_SUCCESS"},
                {"uuid": "scan-b", "status": "STATUS_FAILED"},
            ],
        ),
        patch(
            "endorlabs.workflows.troubleshooting_scans.diff_scans.root_tenant",
            return_value="tenant",
        ),
        patch(
            "endorlabs.workflows.troubleshooting_scans.diff_scans.write_json",
            return_value=Path(".tmp/diff.json"),
        ),
        patch(
            "endorlabs.workflows.troubleshooting_scans.diff_scans.write_text",
            return_value=Path(".tmp/diff.md"),
        ),
    ):
        result = diff_scans.run(args)

    assert result["json_artifact"].endswith("diff.json")
    assert result["md_artifact"].endswith("diff.md")
