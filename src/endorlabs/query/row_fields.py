"""Project row field accessors for query-plane helpers."""

from __future__ import annotations

from typing import Any, cast


def project_uuid(project: Any) -> str:
    """Return project UUID from a model or dict row."""
    if isinstance(project, dict):
        project_dict = cast("dict[str, Any]", project)
        return str(project_dict.get("uuid") or "")
    return str(getattr(project, "uuid", None) or "")


def project_namespace(project: Any) -> str | None:
    """Return wire namespace from a model or dict row."""
    ns = getattr(project, "namespace", None)
    if ns:
        return str(ns)
    if isinstance(project, dict):
        project_dict = cast("dict[str, Any]", project)
        tm = project_dict.get("tenant_meta")
        if isinstance(tm, dict):
            tenant_meta = cast("dict[str, Any]", tm)
            raw = tenant_meta.get("namespace")
            return str(raw) if raw else None
        return None
    tenant_meta = getattr(project, "tenant_meta", None)
    if tenant_meta is None:
        return None
    if isinstance(tenant_meta, dict):
        tenant_meta_dict = cast("dict[str, Any]", tenant_meta)
        raw = tenant_meta_dict.get("namespace")
        return str(raw) if raw else None
    raw = getattr(tenant_meta, "namespace", None)
    return str(raw) if raw else None
