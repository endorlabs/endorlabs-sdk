"""Helpers so integration lists respect endor-namespace-scoping.

CI may set ``ENDOR_NAMESPACE`` to the tenant root. Project-scoped kinds then
require ``traverse=True`` (or a child ``namespace=``) or the facade raises
``NamespaceScopingError`` before the network call.

Keep pagination kwargs (``max_pages``, ``page_size``) as *explicit* ``.list()``
keyword arguments so ``test_integration_pagination_guard`` can see them in the AST.
"""

from __future__ import annotations

from typing import Any


def project_scoped_list_kwargs(client: Any, **kwargs: Any) -> dict[str, Any]:
    """Return extra list kwargs (typically ``traverse=True``) for tenant-root clients.

    No-op when the caller already set ``traverse`` / ``parent``, or when the
    client tenant path already contains a child segment (``a.b``).

    When injecting ``traverse``, also default ``concurrent=False`` so
    ``max_pages`` bounds a single sequential traverse page — not one page per
    child namespace (concurrent fan-out). Callers that want fan-out pass
    ``concurrent=True`` explicitly.
    """
    if "traverse" in kwargs or kwargs.get("parent") is not None:
        return kwargs
    ns = getattr(client, "_default_namespace", "") or ""
    if "." not in ns:
        out = {**kwargs, "traverse": True}
        if "concurrent" not in kwargs:
            out["concurrent"] = False
        return out
    return kwargs
