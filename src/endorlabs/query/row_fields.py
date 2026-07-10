"""Project row field accessors for query-plane helpers.

For typed resource models outside the Query plane, prefer
:func:`endorlabs.utils.namespace.resource_namespace`. This module's
``project_namespace`` is the Query-join row accessor (dict or model).
"""

from __future__ import annotations

from typing import Any, cast

from endorlabs.utils.namespace import resource_namespace as _resource_namespace


def project_uuid(project: Any) -> str:
    """Return project UUID from a model or dict row."""
    if isinstance(project, dict):
        project_dict = cast("dict[str, Any]", project)
        return str(project_dict.get("uuid") or "")
    return str(getattr(project, "uuid", None) or "")


def project_namespace(project: Any) -> str | None:
    """Return wire namespace from a model or dict row.

    Delegates to :func:`endorlabs.utils.namespace.resource_namespace`.
    """
    return _resource_namespace(project)
