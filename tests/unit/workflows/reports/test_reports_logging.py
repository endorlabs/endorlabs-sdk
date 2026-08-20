"""Unit tests for report workflow progress logging."""

from __future__ import annotations

import io
import logging
from typing import TYPE_CHECKING

from endorlabs.utils.redaction import RedactingFilter
from endorlabs.workflows.reports.logging import (
    LOGGER_NAME,
    ReportsCliHandler,
    configure_reports_cli_logging,
    format_milestone,
    logger,
    milestone,
    resolve_log_level,
)

if TYPE_CHECKING:
    import pytest


def test_format_milestone_stable_field_order() -> None:
    line = format_milestone(
        "packet",
        "discover.done",
        projects=3,
        leaves=2,
        tags=1,
    )
    assert line == "packet.discover.done leaves=2 projects=3 tags=1"


def test_resolve_log_level_defaults_and_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ENDOR_LOG_LEVEL", raising=False)
    assert resolve_log_level(None) == logging.INFO
    assert resolve_log_level("DEBUG") == logging.DEBUG
    monkeypatch.setenv("ENDOR_LOG_LEVEL", "WARNING")
    assert resolve_log_level(None) == logging.WARNING


def test_configure_reports_cli_logging_idempotent_and_redacting() -> None:
    for handler in list(logger.handlers):
        if isinstance(handler, ReportsCliHandler):
            logger.removeHandler(handler)

    stream = io.StringIO()
    configure_reports_cli_logging(level="INFO", stream=stream)
    configure_reports_cli_logging(level="INFO", stream=stream)
    cli_handlers = [h for h in logger.handlers if isinstance(h, ReportsCliHandler)]
    assert len(cli_handlers) == 1
    assert any(isinstance(f, RedactingFilter) for f in logger.filters)
    assert logger.name == LOGGER_NAME

    milestone("packet", "start", sprawl=1)
    text = stream.getvalue()
    assert "INFO packet.start sprawl=1" in text

    for handler in list(logger.handlers):
        if isinstance(handler, ReportsCliHandler):
            logger.removeHandler(handler)
