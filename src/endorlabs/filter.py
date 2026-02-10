"""Composable filter builder for Endor Labs API queries.

Provides a type-safe, injection-resistant way to build filter expressions
for the ``list_parameters.filter`` API parameter. All 12 API filter
operators are supported, with ``&`` (AND) and ``|`` (OR) for composition.

Usage::

    from endorlabs import F

    # Simple equality
    client.finding.list(filter=F("spec.level") == "FINDING_LEVEL_CRITICAL")

    # Composition
    client.finding.list(
        filter=(
            F("spec.finding_tags").contains("FINDING_TAGS_REACHABLE_FUNCTION")
            & (F("spec.level").is_in("FINDING_LEVEL_CRITICAL", "FINDING_LEVEL_HIGH"))
        ),
        traverse=True,
    )

Raw ``filter="..."`` strings are still accepted by the facade for
backwards compatibility.
"""

from __future__ import annotations

import re
from typing import Any, Union, override

# Pattern for enum-like constants: UPPER_CASE or UPPER_CASE_123
_ENUM_RE = re.compile(r"^[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)*$")

# Type alias for values accepted by filter operators
FilterValue = Union[str, int, float, bool, "DateValue", "NowValue"]


def _format_value(value: FilterValue) -> str:
    """Format a single value for the wire format.

    - Enum-like strings (UPPER_CASE_WORDS): unquoted
    - Other strings: double-quoted with internal double-quotes escaped
    - Booleans: lowercase ``true`` / ``false``
    - Numbers: plain repr
    - DateValue / NowValue: their own str()
    """
    if isinstance(value, (DateValue, NowValue)):
        return str(value)
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    # String path — isinstance guard for type narrowing
    if _ENUM_RE.match(value):
        return value
    # Regular string — double-quote with escaping
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _format_list_values(values: tuple[FilterValue, ...]) -> str:
    """Format a list of values for contains/in bracket syntax."""
    return f"[{', '.join(_format_value(v) for v in values)}]"


# ---------------------------------------------------------------------------
# Sentinel value types for date() and now()
# ---------------------------------------------------------------------------


class DateValue:
    """Sentinel for ``date(...)`` filter values."""

    __slots__ = ("_value",)

    def __init__(self, value: str) -> None:
        super().__init__()
        self._value = value

    @override
    def __str__(self) -> str:
        """Return the wire-format ``date(value)``."""
        return f"date({self._value})"

    @override
    def __repr__(self) -> str:
        """Return a debug-friendly representation."""
        return f"DateValue({self._value!r})"


class NowValue:
    """Sentinel for ``now(...)`` relative-time filter values."""

    __slots__ = ("_offset",)

    def __init__(self, offset: str) -> None:
        super().__init__()
        self._offset = offset

    @override
    def __str__(self) -> str:
        """Return the wire-format ``now(offset)``."""
        return f"now({self._offset})"

    @override
    def __repr__(self) -> str:
        """Return a debug-friendly representation."""
        return f"NowValue({self._offset!r})"


# ---------------------------------------------------------------------------
# Expression tree
# ---------------------------------------------------------------------------


class FilterExpression:
    """Base class for all filter expression nodes.

    Supports ``&`` (AND), ``|`` (OR), and ``~`` (invert, exists only).
    Serialize to the API wire format via ``str(expr)``.
    """

    def __and__(self, other: FilterExpression) -> CompositeFilter:
        """Combine with another expression using AND."""
        return CompositeFilter(self, "and", other)

    def __or__(self, other: FilterExpression) -> CompositeFilter:
        """Combine with another expression using OR."""
        return CompositeFilter(self, "or", other)

    def __invert__(self) -> FilterExpression:
        """Negate the expression (only supported on ``exists()`` clauses)."""
        raise TypeError(
            "Cannot invert this expression. "
            "~ (invert) is only supported on exists() clauses."
        )

    @override
    def __str__(self) -> str:  # pragma: no cover — subclasses override
        """Serialize to the API wire-format string."""
        raise NotImplementedError


class Clause(FilterExpression):
    """A single filter clause: ``field op value``."""

    __slots__ = ("_field", "_op", "_value_str")

    def __init__(self, field: str, op: str, value_str: str) -> None:
        super().__init__()
        self._field = field
        self._op = op
        self._value_str = value_str

    @override
    def __str__(self) -> str:
        """Serialize to the API wire-format string."""
        if self._value_str:
            return f"{self._field} {self._op} {self._value_str}"
        # exists / not exists — no value
        return f"{self._field} {self._op}"

    @override
    def __repr__(self) -> str:
        """Return a debug-friendly representation."""
        return f"Clause({self._field!r}, {self._op!r}, {self._value_str!r})"

    @override
    def __invert__(self) -> FilterExpression:
        """Negate ``exists`` to ``not exists`` and vice versa."""
        if self._op == "exists":
            return Clause(self._field, "not exists", "")
        if self._op == "not exists":
            return Clause(self._field, "exists", "")
        raise TypeError(
            "Cannot invert this expression. "
            "~ (invert) is only supported on exists() clauses."
        )


class CompositeFilter(FilterExpression):
    """Two expressions joined by ``and`` or ``or``."""

    __slots__ = ("_left", "_op", "_right")

    def __init__(
        self, left: FilterExpression, op: str, right: FilterExpression
    ) -> None:
        super().__init__()
        self._left = left
        self._op = op
        self._right = right

    @override
    def __str__(self) -> str:
        """Serialize to the API wire-format string with parentheses."""
        return f"({self._left}) {self._op} ({self._right})"

    @override
    def __repr__(self) -> str:
        """Return a debug-friendly representation."""
        return f"CompositeFilter({self._left!r}, {self._op!r}, {self._right!r})"


# ---------------------------------------------------------------------------
# Field reference — the main entry point
# ---------------------------------------------------------------------------


class FieldRef:
    """A field path reference that produces filter clauses via operator methods.

    Created by ``F("field.path")``. Do not instantiate directly.
    """

    __slots__ = ("_path",)
    __hash__ = None  # type: ignore[assignment]  # __eq__ returns Clause, not bool

    def __init__(self, path: str) -> None:
        super().__init__()
        self._path = path

    # -- Comparison operators -----------------------------------------------

    def __eq__(self, other: Any) -> Clause:  # type: ignore[override]
        """Build an equality clause: ``field == value``."""
        return Clause(self._path, "==", _format_value(other))

    def __ne__(self, other: Any) -> Clause:  # type: ignore[override]
        """Build an inequality clause: ``field != value``."""
        return Clause(self._path, "!=", _format_value(other))

    def __lt__(self, other: Any) -> Clause:
        """Build a less-than clause: ``field < value``."""
        return Clause(self._path, "<", _format_value(other))

    def __le__(self, other: Any) -> Clause:
        """Build a less-than-or-equal clause: ``field <= value``."""
        return Clause(self._path, "<=", _format_value(other))

    def __gt__(self, other: Any) -> Clause:
        """Build a greater-than clause: ``field > value``."""
        return Clause(self._path, ">", _format_value(other))

    def __ge__(self, other: Any) -> Clause:
        """Build a greater-than-or-equal clause: ``field >= value``."""
        return Clause(self._path, ">=", _format_value(other))

    # -- List operators -----------------------------------------------------

    def contains(self, *values: FilterValue) -> Clause:
        """Match when a list field contains one or more values (OR semantics)."""
        if not values:
            raise ValueError("contains() requires at least one value")
        return Clause(self._path, "contains", _format_list_values(values))

    def not_contains(self, *values: FilterValue) -> Clause:
        """Match when a list field does NOT contain any of the values."""
        if not values:
            raise ValueError("not_contains() requires at least one value")
        return Clause(self._path, "not contains", _format_list_values(values))

    def is_in(self, *values: FilterValue) -> Clause:
        """Match when the field equals one of the given values (OR semantics)."""
        if not values:
            raise ValueError("is_in() requires at least one value")
        return Clause(self._path, "in", _format_list_values(values))

    def not_in(self, *values: FilterValue) -> Clause:
        """Match when the field does NOT equal any of the given values."""
        if not values:
            raise ValueError("not_in() requires at least one value")
        return Clause(self._path, "not in", _format_list_values(values))

    # -- Regex --------------------------------------------------------------

    def matches(self, pattern: str) -> Clause:
        """Match when the field matches a regex pattern."""
        escaped = pattern.replace("\\", "\\\\").replace('"', '\\"')
        return Clause(self._path, "matches", f'"{escaped}"')

    # -- Existence ----------------------------------------------------------

    def exists(self) -> Clause:
        """Match when the field exists (is not null/empty)."""
        return Clause(self._path, "exists", "")

    def not_exists(self) -> Clause:
        """Match when the field does NOT exist."""
        return Clause(self._path, "not exists", "")

    @override
    def __repr__(self) -> str:
        """Return a debug-friendly representation."""
        return f"F({self._path!r})"


# ---------------------------------------------------------------------------
# Public factory
# ---------------------------------------------------------------------------


class F(FieldRef):
    """Filter builder entry point.

    ``F("field.path")`` returns a field reference whose operator methods
    produce composable filter expressions.

    Examples::

        F("spec.level") == "FINDING_LEVEL_CRITICAL"
        F("spec.finding_tags").contains("FINDING_TAGS_REACHABLE_FUNCTION")
        F("meta.create_time") >= F.date("2024-05-01")
        F("meta.create_time") >= F.now("-72h")

    Compose with ``&`` (AND) and ``|`` (OR)::

        (F("spec.level") == "FINDING_LEVEL_CRITICAL")
        & (F("spec.finding_tags").contains("FINDING_TAGS_FIX_AVAILABLE"))

    """

    @staticmethod
    def date(value: str) -> DateValue:
        """Create a ``date(...)`` value for date comparisons.

        Args:
            value: Date string in ``YYYY-MM-DD`` or RFC 3339 format.
        """
        return DateValue(value)

    @staticmethod
    def now(offset: str) -> NowValue:
        """Create a ``now(...)`` value for relative-time comparisons.

        Args:
            offset: Duration offset, e.g. ``"-72h"``, ``"-15m"``.
        """
        return NowValue(offset)


__all__ = [
    "Clause",
    "CompositeFilter",
    "DateValue",
    "F",
    "FieldRef",
    "FilterExpression",
    "FilterValue",
    "NowValue",
]
