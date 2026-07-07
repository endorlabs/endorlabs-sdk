"""Unit tests for ScanLogRequest resource helpers."""

from __future__ import annotations

from endorlabs.resources.scan_log_request import ScanLogLevel


def test_scan_log_level_enum() -> None:
    """ScanLogLevel string constants match API wire values."""
    assert ScanLogLevel.ERROR == "LOG_LEVEL_ERROR"
    assert ScanLogLevel.WARNING == "LOG_LEVEL_WARNING"
    assert ScanLogLevel.INFO == "LOG_LEVEL_INFO"
    assert ScanLogLevel.DEBUG == "LOG_LEVEL_DEBUG"
