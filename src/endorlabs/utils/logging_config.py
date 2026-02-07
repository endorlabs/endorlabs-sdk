"""Centralized logging configuration."""

from __future__ import annotations

import logging
import os


def setup_logging(module_name: str = "endorlabs") -> logging.Logger:
    """Set up logging from ENDOR_LOG_LEVEL environment variable."""
    level_str = os.getenv("ENDOR_LOG_LEVEL", "INFO").upper()

    # Convert string to logging level constant
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }

    level = level_map.get(level_str, logging.INFO)

    format_str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    logging.basicConfig(level=level, format=format_str)
    return logging.getLogger(module_name)


# Loggers used by the SDK and HTTP stack; session level is applied to all of these.
_CLIENT_SESSION_LOGGER_NAMES = ("endorlabs", "httpx", "httpcore")


def get_resource_logger(name: str) -> logging.Logger:
    """Return a logger with :class:`RedactingFilter` for resource modules.

    Idempotent: calling twice with the same *name* does not duplicate
    the filter.  Resource modules should use this instead of manually
    constructing and attaching a ``RedactingFilter``.

    Args:
        name: Logger name, typically ``__name__`` of the calling module.

    Returns:
        A :class:`logging.Logger` with credential-redacting filter attached.
    """
    from .redaction import (
        JSON_REDACTION_REPLACEMENT,
        RedactingFilter,
        json_redaction_pattern,
        redaction_pattern,
    )

    logger = logging.getLogger(name)
    # Guard against duplicate filters when called more than once
    if not any(isinstance(f, RedactingFilter) for f in logger.filters):
        logger.addFilter(
            RedactingFilter(
                [
                    redaction_pattern,
                    (json_redaction_pattern, JSON_REDACTION_REPLACEMENT),
                ]
            )
        )
    return logger


def apply_client_session_log_level(level: int) -> None:
    """Set the given numeric level on all loggers used during a client session.

    Called by APIClient when logging_level is set at construction so that
    endorlabs, httpx, and httpcore all honor the client's level for the
    lifetime of that client instance.
    """
    for name in _CLIENT_SESSION_LOGGER_NAMES:
        logging.getLogger(name).setLevel(level)
