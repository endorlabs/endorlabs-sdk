"""Canonical main-context (default branch) MQL filter fragments."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from endorlabs.core.filter import FilterExpression

MAIN_CONTEXT_TYPE = "CONTEXT_TYPE_MAIN"

# Unquoted enum form (FindingLog / legacy list filters).
MAIN_CONTEXT_CLAUSE = "context.type==CONTEXT_TYPE_MAIN"

# Quoted enum form (facade list filters).
MAIN_CONTEXT_LIST_FILTER = f'context.type=="{MAIN_CONTEXT_TYPE}"'


def main_context_filter(extra: str | FilterExpression | None = None) -> str:
    """Combine main-context filter with an optional expression."""
    base = MAIN_CONTEXT_LIST_FILTER
    if extra is None:
        return base
    extra_text = str(extra).strip()
    if not extra_text:
        return base
    return f"({base}) and ({extra_text})"


def pv_main_context_filter() -> str:
    """Main-context PackageVersion list filter."""
    return MAIN_CONTEXT_CLAUSE


def context_partition_filter(
    context: Any,
    *,
    extra: str | FilterExpression | None = None,
) -> str:
    """Build a list filter for one scan plane using context.type and context.id."""
    ctx_type = getattr(context, "type", None)
    if not ctx_type:
        raise ValueError("context.type is required for partition filter")
    clauses = [f'context.type=="{ctx_type}"']
    ctx_id = getattr(context, "id", None)
    if ctx_id:
        clauses.append(f'context.id=="{ctx_id}"')
    base = " and ".join(f"({c})" for c in clauses)
    if extra is None:
        return base
    extra_text = str(extra).strip()
    if not extra_text:
        return base
    return f"({base}) and ({extra_text})"
