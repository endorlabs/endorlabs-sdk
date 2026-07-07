"""Normalize list-style MQL filters for Query POST wire dialect."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from endorlabs.core.filter import FilterExpression

# Quoted enum equality from facade / F() output: context.type=="CONTEXT_TYPE_MAIN"
_QUOTED_ENUM_EQ = re.compile(r'==\s*"([A-Z][A-Z0-9_]+)"')

# Quoted enum tokens inside bracket lists: in ["A", "B"] or contains ["A"]
_QUOTED_ENUM_TOKEN = re.compile(r'"([A-Z][A-Z0-9_]+)"')


def to_query_filter(expr: str | FilterExpression) -> str:
    """Convert facade list filters to Query POST MQL (unquoted enum literals)."""
    text = str(expr).strip()
    if not text:
        return text
    text = _QUOTED_ENUM_EQ.sub(r"==\1", text)
    return _QUOTED_ENUM_TOKEN.sub(r"\1", text)
