"""Unit tests for opt-in wire-key probe helpers."""

from __future__ import annotations

from unittest.mock import patch

from endorlabs.utils.schema_drift import log_unknown_wire_keys, unknown_wire_keys


def test_unknown_wire_keys_filters_modeled_and_ignored() -> None:
    data = {
        "name": "x",
        "tenant": "ignored",
        "search_score": 1.0,
        "extra": True,
    }
    unknown = unknown_wire_keys(data, {"name", "description"})
    assert unknown == {"extra": True}


def test_log_unknown_wire_keys_emits_warning() -> None:
    with patch("endorlabs.utils.schema_drift.logger.warning") as mock_warning:
        result = log_unknown_wire_keys(
            {"a": 1, "b": 2},
            {"a"},
            context="spec",
            resource_name="Project",
        )
    assert result == {"b": 2}
    mock_warning.assert_called_once()
