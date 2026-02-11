"""Log redaction utilities for Endor Labs SDK.

Provides :class:`RedactingFilter` and pre-compiled patterns for scrubbing
sensitive credential material from log records before they reach any handler.

Threat model
------------
The SDK handles two credential types:

1. **API key + secret** — sent as ``{"key": "…", "secret": "…"}`` in the
   authentication POST to ``v1/auth/api-key``.  That request goes through
   the raw ``httpx.Client`` (not through ``APIClient.post``), so *httpx's
   own* DEBUG logger may emit the payload in **JSON / double-quote** format.
2. **Bearer token** — returned from the auth endpoint and attached as an
   ``Authorization`` header on every subsequent request.  Debug-level
   request logging serialises headers as a Python dict repr
   (single-quote format).  The OAuth callback URL in ``auth_server``
   carries the token as a ``?token=…`` query parameter.

The patterns below cover the repr formats that each credential can appear in.

Used by ``api_client``, ``auth_server``, and resource modules.
"""

import logging
import re
from typing import override

# ---------------------------------------------------------------------------
# Sensitive key names to scrub
# ---------------------------------------------------------------------------
REDACTED_KEYS: list[str] = ["authorization", "secret", "token", "key"]
"""Header / payload keys whose values must never appear in logs.

Covers the ``Authorization`` header, the ``secret`` and ``key`` fields in the
API-key auth payload, and the ``token`` field in auth responses.
"""

# ---------------------------------------------------------------------------
# Pattern 1 - Python dict repr  (single-quote key-value pairs)
# ---------------------------------------------------------------------------
redaction_pattern: str = r"'(" + "|".join(REDACTED_KEYS) + r")':\s*'.*?'"
"""Matches ``'key': 'some-value'`` as produced by ``str(dict)`` / ``repr()``.

Risk: ``APIClient`` debug-logs request headers as Python dicts.  The
``Authorization`` header and any auth-response dicts serialised via ``str()``
use this single-quote format.  Without redaction the bearer token or API
secret would appear verbatim in DEBUG output.
"""

# ---------------------------------------------------------------------------
# Pattern 2 - JSON repr  (double-quote key-value pairs)
# ---------------------------------------------------------------------------
json_redaction_pattern: str = r'"(' + "|".join(REDACTED_KEYS) + r')"\s*:\s*".*?"'
"""Matches ``"key": "some-value"`` as produced by ``json.dumps()`` and httpx.

Risk: The API-key authentication payload (``{"key": "…", "secret": "…"}``)
is POSTed via the raw ``httpx.Client``, bypassing ``APIClient.post`` and its
manual ``_redact_log_data`` helper.  When httpx or httpcore DEBUG logging is
active, the request body is emitted in JSON (double-quote) format.  This
pattern ensures those values are still scrubbed.
"""

JSON_REDACTION_REPLACEMENT: str = r'"\1": "***REDACTED***"'
"""Replacement for :data:`json_redaction_pattern`, preserving JSON structure."""

# ---------------------------------------------------------------------------
# Pattern 3 — URL query-string tokens
# ---------------------------------------------------------------------------
url_token_redaction_pattern: str = r"(token=)[^&\s]+"
"""Matches ``token=<value>`` in URL query strings.

Risk: The OAuth callback handler in ``auth_server`` logs ``self.path`` on
error paths (e.g. "Token not found in redirect: /?token=eyJ…").  The bearer
token appears as a query parameter and must be scrubbed before the message
reaches any handler.
"""

url_token_redaction_replacement: str = r"\1***REDACTED***"
"""Replacement for :data:`url_token_redaction_pattern`."""

# ---------------------------------------------------------------------------
# Default replacement sentinel
# ---------------------------------------------------------------------------
REDACTION_DEFAULT_REPLACEMENT: str = r"'\1': '***REDACTED***'"
"""Replacement used when a pattern is supplied as a bare ``str`` (no explicit
replacement).  Preserves the single-quote dict-repr structure so downstream
consumers can still parse the shape of the log line.
"""


class RedactingFilter(logging.Filter):
    """A :class:`logging.Filter` that rewrites log records to scrub secrets.

    Patterns are compiled once at construction time.  At filter time the
    filter rewrites ``record.msg`` **and** ``record.args`` (both ``dict``
    and ``tuple`` forms) so that sensitive values are replaced *before* the
    message is formatted and handed to any handler.

    The filter never suppresses records — :meth:`filter` always returns
    ``True``.

    Parameters
    ----------
    patterns:
        Each element is either:

        * a regex **string** -- matched with :data:`REDACTION_DEFAULT_REPLACEMENT`
        * a ``(pattern, replacement)`` tuple -- used as-is

        All patterns are compiled with :data:`re.IGNORECASE`.

    """

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
        """Redact sensitive data from the log record.

        Handles three ``record.args`` shapes:

        * **dict** — ``%(name)s`` style formatting; each value is redacted.
        * **tuple** — positional ``%s`` style formatting; each element is
          redacted.
        * **None / other** — no args to process.

        Returns ``True`` unconditionally (records are never suppressed).
        """
        record.msg = self._redact(record.msg)
        if isinstance(record.args, dict):
            record.args = {k: self._redact(v) for k, v in record.args.items()}
        elif isinstance(record.args, tuple):
            record.args = tuple(self._redact(a) for a in record.args)
        return True

    def _redact(self, message: str | object) -> str:
        """Apply all compiled patterns to *message*.

        Non-string values are coerced to ``str`` first so that numeric or
        object args do not raise.
        """
        if not isinstance(message, str):
            message = str(message)
        for pattern, replacement in self._pattern_replacement_pairs:
            message = pattern.sub(replacement, message)
        return message
