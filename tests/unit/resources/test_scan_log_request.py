"""Fast unit tests for scan_log_request resource models."""

from __future__ import annotations

from unittest.mock import patch

from endorlabs.resources.scan_log_request import (
    ScanLogRequest,
    ScanLogRequestSpecCreate,
)


def test_scan_log_request_coerces_dict_spec_and_keeps_logs() -> None:
    model = ScanLogRequest(
        meta={"name": "req-1"},
        spec={
            "max_entries": 5,
            "scan_result_uuid": "scan-1",
            "log_messages": [
                {"level": "LOG_LEVEL_ERROR", "json_payload": {"msg": "boom"}}
            ],
        },
    )
    assert model.spec.max_entries == 5
    assert model.spec.log_messages is not None
    assert model.spec.log_messages[0].level.value == "LOG_LEVEL_ERROR"


def test_scan_log_request_ignores_unknown_fields_in_spec_dict() -> None:
    with patch("endorlabs.resources.scan_log_request.logger.warning") as mock_warning:
        model = ScanLogRequest(
            meta={"name": "req-2"}, spec={"max_entries": 1, "unknown_key": "x"}
        )
    assert model.spec.max_entries == 1
    # Spec dict is converted before field validators execute.
    mock_warning.assert_not_called()


def test_scan_log_request_spec_create_allows_minimal_payload() -> None:
    payload = ScanLogRequestSpecCreate(max_entries=25, execution_id="ci-123")
    assert payload.max_entries == 25
    assert payload.execution_id == "ci-123"
