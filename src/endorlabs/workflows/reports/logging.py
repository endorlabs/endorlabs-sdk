"""Progress milestones and CLI logging for report workflows.

Library code emits milestones via :func:`milestone` (logger only — no
``print``). CLIs call :func:`configure_reports_cli_logging` so INFO
milestones appear on stdout. Loggers use :func:`get_resource_logger`
(``RedactingFilter`` for tokens / API secrets).
"""

from __future__ import annotations

import logging
import os
import sys
from typing import Any, TextIO

from endorlabs.utils.logging_config import get_resource_logger

LOGGER_NAME = "endorlabs.workflows.reports"
logger = get_resource_logger(LOGGER_NAME)


class ReportsCliHandler(logging.StreamHandler):
    """StreamHandler tagged for idempotent :func:`configure_reports_cli_logging`."""


_LEVEL_NAMES = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}


def resolve_log_level(cli_value: str | None = None) -> int:
    """Resolve level from CLI flag or ``ENDOR_LOG_LEVEL`` (default INFO)."""
    raw = (cli_value or os.getenv("ENDOR_LOG_LEVEL") or "INFO").strip().upper()
    return _LEVEL_NAMES.get(raw, logging.INFO)


def configure_reports_cli_logging(
    *,
    level: int | str | None = None,
    stream: TextIO | None = None,
) -> logging.Logger:
    """Attach a single StreamHandler for report CLI progress (idempotent).

    Defaults to **stdout** so operators can monitor stage milestones in the
    same stream as the final ``Wrote …`` lines. Does not call
    ``logging.basicConfig`` (avoids mutating the root logger).
    """
    if isinstance(level, str) or level is None:
        resolved = resolve_log_level(level if isinstance(level, str) else None)
    else:
        resolved = int(level)

    logger.setLevel(resolved)
    target = stream if stream is not None else sys.stdout
    for handler in logger.handlers:
        if isinstance(handler, ReportsCliHandler):
            handler.setLevel(resolved)
            return logger

    handler = ReportsCliHandler(target)
    handler.setLevel(resolved)
    handler.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
    logger.addHandler(handler)
    return logger


def format_milestone(
    workflow: str,
    stage: str,
    message: str = "",
    /,
    **fields: Any,
) -> str:
    """Build a stable milestone line (no I/O).

    Prefer numeric counts and stage labels over raw row dumps. Do not pass
    secrets, tokens, or full API payloads in *fields* — the redacting filter
    catches known credential key shapes, not free-form dumps.
    """
    parts = [f"{workflow}.{stage}"]
    msg = (message or "").strip()
    if msg:
        parts.append(msg)
    for key in sorted(fields):
        val = fields[key]
        if val is None:
            continue
        parts.append(f"{key}={val}")
    return " ".join(parts)


def milestone(
    workflow: str,
    stage: str,
    message: str = "",
    /,
    **fields: Any,
) -> None:
    """Emit an INFO progress milestone for *workflow* / *stage*."""
    logger.info("%s", format_milestone(workflow, stage, message, **fields))
