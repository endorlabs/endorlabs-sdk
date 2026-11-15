"""Unit tests for search_embedded_scan_errors."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

from endorlabs.workflows.troubleshooting_scans.scan_error_hits import (
    search_embedded_scan_errors,
)


def test_search_embedded_scan_errors_matches() -> None:
    client = Mock()
    client.ScanResult.list_by_project.return_value = [
        SimpleNamespace(
            uuid="s-1",
            spec=SimpleNamespace(
                status="STATUS_FAILURE",
                logs=["ok line", "ERROR: toolchain failed"],
            ),
        )
    ]
    project = {
        "uuid": "p-1",
        "tenant_meta": {"namespace": "tenant.child"},
    }
    evidence = search_embedded_scan_errors(
        client,
        projects=[project],
        error_pattern=r"toolchain",
        query_namespace="tenant",
        limit=5,
    )
    assert evidence.hit_count == 1
    assert "toolchain" in evidence.hits[0]["match_line"].lower()
