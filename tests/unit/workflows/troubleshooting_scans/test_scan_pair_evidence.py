"""Tests for pure scan-pair evidence assembly."""

from __future__ import annotations

from typing import Any

from endorlabs.workflows.troubleshooting_scans.scan_pair_evidence import (
    assemble_scan_pair_evidence,
)


def _scan(uuid: str, *, status: str, create_time: str) -> dict[str, Any]:
    return {
        "uuid": uuid,
        "meta": {"create_time": create_time},
        "spec": {
            "status": status,
            "exit_code": 0,
            "stats": {},
            "environment": {},
            "versions": [],
            "config": {},
        },
    }


def test_preserves_primary_secondary_when_inputs_reversed_in_time() -> None:
    older = _scan("older", status="STATUS_SUCCESS", create_time="2024-01-01T00:00:00Z")
    newer = _scan("newer", status="STATUS_FAILURE", create_time="2024-02-01T00:00:00Z")

    # Caller intentionally names newer as primary (e.g. current failing scan).
    result = assemble_scan_pair_evidence(
        newer,
        older,
        selection_reason="user_supplied",
        concurrent=False,
        primary_logs=["line with content"],
        secondary_logs=["line with content"],
    )

    assert result.primary is not None
    assert result.secondary is not None
    assert result.primary.uuid == "newer"
    assert result.primary.role == "primary"
    assert result.secondary.uuid == "older"
    assert result.secondary.role == "secondary"
    assert result.selection_reason == "user_supplied"
    assert result.concurrency == "not_concurrent"
    assert result.primary_log_outcome == "ok"
    assert result.secondary_log_outcome == "ok"
    assert result.status == "success"
    assert "status" in result.diff["changes"]


def test_concurrency_unknown_when_not_supplied() -> None:
    a = _scan("a", status="STATUS_SUCCESS", create_time="2024-01-01T00:00:00Z")
    b = _scan("b", status="STATUS_SUCCESS", create_time="2024-01-02T00:00:00Z")
    result = assemble_scan_pair_evidence(
        a, b, primary_logs=["ok"], secondary_logs=["ok"]
    )
    assert result.concurrency == "unknown"
    assert result.status == "partial"


def test_acquire_fetches_then_assembles(monkeypatch: Any) -> None:
    from endorlabs.workflows.troubleshooting_scans.scan_pair_evidence import (
        acquire_scan_pair_evidence,
    )

    primary = _scan("p", status="STATUS_FAILURE", create_time="2024-02-01T00:00:00Z")
    secondary = _scan("s", status="STATUS_SUCCESS", create_time="2024-01-01T00:00:00Z")
    client = object()

    def fake_fetch(_client: Any, _ns: str, uuid: str) -> dict[str, Any]:
        return primary if uuid == "p" else secondary

    monkeypatch.setattr(
        "endorlabs.workflows.troubleshooting_scans.scan_pair_evidence.fetch_scan_result",
        fake_fetch,
    )
    result = acquire_scan_pair_evidence(
        client,
        namespace="example-tenant.child",
        primary_scan_result_uuid="p",
        secondary_scan_result_uuid="s",
        selection_reason="heuristic",
        concurrent=False,
    )
    assert result.primary is not None and result.primary.uuid == "p"
    assert result.secondary is not None and result.secondary.uuid == "s"
    assert result.selection_reason == "heuristic"
    assert result.primary_log_outcome == "unknown"


def test_log_error_and_empty_outcomes() -> None:
    a = _scan("a", status="STATUS_SUCCESS", create_time="2024-01-01T00:00:00Z")
    b = _scan("b", status="STATUS_SUCCESS", create_time="2024-01-02T00:00:00Z")
    result = assemble_scan_pair_evidence(
        a,
        b,
        primary_log_error="denied",
        secondary_logs=[],
        concurrent=True,
    )
    assert result.primary_log_outcome == "error"
    assert result.secondary_log_outcome == "empty"
    assert result.concurrency == "concurrent"
    assert result.status == "partial"
