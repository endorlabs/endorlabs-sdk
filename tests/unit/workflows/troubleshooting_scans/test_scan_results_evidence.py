"""Unit tests for acquire_scan_results."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

from endorlabs.workflows.troubleshooting_scans.scan_results_evidence import (
    acquire_scan_results,
)


def test_acquire_scan_results_single_project() -> None:
    client = Mock()
    client.ScanResult.list_by_project.return_value = [
        SimpleNamespace(
            uuid="s-1",
            spec=SimpleNamespace(status="STATUS_SUCCESS"),
            meta=SimpleNamespace(create_time="2024-01-01T00:00:00Z"),
        )
    ]
    project = {
        "uuid": "p-1",
        "tenant_meta": {"namespace": "tenant.child"},
    }
    evidence = acquire_scan_results(
        client,
        query_namespace="tenant",
        projects=[project],
        limit=10,
    )
    assert evidence.project_count == 1
    assert evidence.scan_result_count == 1
    assert evidence.scan_results[0]["uuid"] == "s-1"
    client.ScanResult.list_by_project.assert_called_once()


def test_acquire_scan_results_empty_projects() -> None:
    client = Mock()
    evidence = acquire_scan_results(
        client,
        query_namespace="tenant",
        projects=[],
        limit=5,
    )
    assert evidence.scan_result_count == 0
    client.ScanResult.list_by_project.assert_not_called()
