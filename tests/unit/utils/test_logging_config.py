"""Tests for centralized logging configuration utilities."""

import logging

from endorlabs.utils.logging_config import get_resource_logger
from endorlabs.utils.redaction import RedactingFilter


def test_get_resource_logger_returns_logger_with_correct_name() -> None:
    """get_resource_logger returns a logger named after the caller's module."""
    logger = get_resource_logger("endorlabs.resources.project")
    assert logger.name == "endorlabs.resources.project"


def test_get_resource_logger_attaches_redacting_filter() -> None:
    """get_resource_logger attaches exactly one RedactingFilter."""
    name = "endorlabs.resources._test_redact_check"
    logger = get_resource_logger(name)
    redacting_filters = [f for f in logger.filters if isinstance(f, RedactingFilter)]
    assert len(redacting_filters) == 1


def test_get_resource_logger_is_idempotent() -> None:
    """Calling get_resource_logger twice does not duplicate the filter."""
    name = "endorlabs.resources._test_idempotent"
    _ = get_resource_logger(name)
    logger = get_resource_logger(name)
    redacting_filters = [f for f in logger.filters if isinstance(f, RedactingFilter)]
    assert len(redacting_filters) == 1


def test_get_resource_logger_redacts_secrets() -> None:
    """The attached filter redacts sensitive values from log messages."""
    name = "endorlabs.resources._test_redaction"
    logger = get_resource_logger(name)
    record = logging.LogRecord(
        name=name,
        level=logging.DEBUG,
        pathname="",
        lineno=0,
        msg="'secret': 'my-api-secret-value'",
        args=None,
        exc_info=None,
    )
    # Apply all filters (our RedactingFilter should rewrite the message)
    for f in logger.filters:
        if isinstance(f, logging.Filter):
            f.filter(record)
    assert "my-api-secret-value" not in record.msg
    assert "REDACTED" in record.msg
