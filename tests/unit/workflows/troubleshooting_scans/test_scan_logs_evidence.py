"""Unit tests for acquire_scan_logs."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

from endorlabs.workflows.troubleshooting_scans.scan_logs_evidence import (
    acquire_scan_logs,
)


def test_acquire_scan_logs_ok() -> None:
    client = Mock()
    client.ScanResult.get_logs.return_value = [
        SimpleNamespace(
            timestamp="2024-01-01T00:00:00Z",
            level="INFO",
            json_payload={"msg": "hello"},
            tags=None,
        )
    ]
    evidence = acquire_scan_logs(
        client,
        scan_result_uuid="s-1",
        namespace="tenant.child",
        batch_size=10,
        max_rounds=2,
        start_time="2024-01-01T00:00:00Z",
        end_time="2024-01-02T00:00:00Z",
    )
    assert evidence.log_outcome == "ok"
    assert evidence.count == 1
    assert evidence.messages[0]["json_payload"] == {"msg": "hello"}


def test_acquire_scan_logs_empty() -> None:
    client = Mock()
    client.ScanResult.get_logs.return_value = []
    evidence = acquire_scan_logs(
        client,
        scan_result_uuid="s-1",
        namespace="tenant.child",
        end_time="2024-01-02T00:00:00Z",
    )
    assert evidence.log_outcome == "empty"
    assert evidence.count == 0


def test_acquire_scan_logs_error() -> None:
    client = Mock()
    client.ScanResult.get_logs.side_effect = RuntimeError("denied")
    evidence = acquire_scan_logs(
        client,
        scan_result_uuid="s-1",
        namespace="tenant.child",
        end_time="2024-01-02T00:00:00Z",
    )
    assert evidence.log_outcome == "error"
    assert evidence.status == "error"
    assert "denied" in evidence.detail
