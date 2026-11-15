"""HTML-safe JSON and text escaping for report script/DOM boundaries (A02)."""

from __future__ import annotations

import json
from typing import Any


def html_safe_json(value: Any, *, separators: tuple[str, str] = (",", ":")) -> str:
    """Serialize ``value`` for embedding inside a ``<script>`` block.

    Escapes ``<``, ``>``, ``&``, and U+2028/U+2029 so a data string cannot
    break out of the script element. JSON quoting alone is not sufficient.
    """
    raw = json.dumps(value, separators=separators, ensure_ascii=False)
    return (
        raw.replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


def html_escape_text(value: str) -> str:
    """Escape text for HTML text/attribute contexts (not script JSON)."""
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )
