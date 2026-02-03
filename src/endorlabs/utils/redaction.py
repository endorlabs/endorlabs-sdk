"""Log redaction utilities for Endor Cockpit SDK.

Provides RedactingFilter and patterns for redacting sensitive keys
(authorization, secret, token, key) from log records. Used by api_client
and auth_server.
"""

import logging
import re
from typing import override

REDACTED_KEYS = ["authorization", "secret", "token", "key"]
redaction_pattern = (
    r"'(" + "|".join(REDACTED_KEYS) + r")':\s*'.*?'"
)  # Regex pattern to redact keys and their values
# URL query style (e.g. ?token=... or &token=...) for OAuth callback logs
url_token_redaction_pattern = r"(token=)[^&\s]+"
url_token_redaction_replacement = r"\1***REDACTED***"
REDACTION_DEFAULT_REPLACEMENT = r"'\1': '***REDACTED***'"


class RedactingFilter(logging.Filter):
    """Filter that redacts sensitive keys from log records."""

    def __init__(
        self,
        patterns: list[str | tuple[str, str]],
    ) -> None:
        super().__init__()
        pairs: list[tuple[re.Pattern[str], str]] = []
        for item in patterns:
            if isinstance(item, str):
                pairs.append(
                    (re.compile(item, re.IGNORECASE), REDACTION_DEFAULT_REPLACEMENT)
                )
            else:
                pattern, replacement = item
                pairs.append((re.compile(pattern, re.IGNORECASE), replacement))
        self._pattern_replacement_pairs = pairs

    @override
    def filter(self, record: logging.LogRecord) -> bool:
        """Redact sensitive data from the log record."""
        record.msg = self._redact(record.msg)
        if isinstance(record.args, dict):
            record.args = {k: self._redact(v) for k, v in record.args.items()}
        return True

    def _redact(self, message: str | object) -> str:
        if not isinstance(message, str):
            message = str(message)
        for pattern, replacement in self._pattern_replacement_pairs:
            message = pattern.sub(replacement, message)
        return message
