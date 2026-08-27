"""Runtime checks for portable (non-estate) example strings."""

from __future__ import annotations

import re

from endorlabs.core.exceptions import PortableExamplesError

# High-confidence estate tenant path: dotted segments that are not placeholders.
# Do not treat ``example-tenant.child`` as a hit (hyphen is a word boundary for ``\b``).
_NON_PORTABLE_TENANT = re.compile(
    r"(?<![A-Za-z0-9_-])(?!example-tenant\b)(?!oss\b)(?!auri\b)"
    r"([a-z][a-z0-9-]{2,}\.[a-z][a-z0-9.-]{1,})",
    re.IGNORECASE,
)

_PLACEHOLDER_HINT = (
    "Use placeholders only (example-tenant, example-tenant.child, <tenant>, "
    "user@example.com) — see rule endor-portable-examples."
)


def raise_if_nonportable_tenant_literal(value: str, *, field: str = "value") -> None:
    """Raise :class:`PortableExamplesError` when *value* looks like a real tenant path.

    Intended for git-tracked fixtures, skill snippets, and guards — not for live
    ``Client(tenant=…)`` against customer namespaces.
    """
    cleaned = value.strip()
    if not cleaned:
        return
    match = _NON_PORTABLE_TENANT.search(cleaned)
    if match is None:
        return
    token = match.group(0)
    if token.lower().startswith("example-tenant"):
        return
    raise PortableExamplesError(
        f"Non-portable {field} {token!r} in {cleaned!r}. {_PLACEHOLDER_HINT}"
    )


__all__ = ["raise_if_nonportable_tenant_literal"]
