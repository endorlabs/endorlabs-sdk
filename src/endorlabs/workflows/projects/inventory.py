"""Tenant project and installation inventory helpers for workflows and skills."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from endorlabs import Client

INSTALLATION_LIST_MASK = (
    "meta.name,tenant_meta.namespace,uuid,"
    "spec.external_id,spec.external_name,spec.login"
)


def build_installation_lookup(
    installations: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Map ``Installation.spec.external_id`` to installation dict rows."""
    lookup: dict[str, dict[str, Any]] = {}
    for row in installations:
        ext_id = (row.get("spec") or {}).get("external_id")
        if ext_id:
            lookup[str(ext_id)] = row
    return lookup


def installation_display_name(installation: dict[str, Any] | None) -> str:
    """Resolve a human-readable installation label for CSV or summaries."""
    if not installation:
        return ""
    spec = installation.get("spec") or {}
    meta_name = (installation.get("meta") or {}).get("name") or ""
    external_name = spec.get("external_name") or ""
    login = spec.get("login") or ""
    if external_name:
        return external_name
    if meta_name and login:
        return f"{meta_name} ({login})"
    return meta_name or login


def fetch_installation_lookup(
    client: Client,
    *,
    traverse: bool = True,
    mask: str = INSTALLATION_LIST_MASK,
    max_pages: int | None = None,
) -> dict[str, dict[str, Any]]:
    """List installations tenant-wide and return an external_id lookup map."""
    kwargs: dict[str, Any] = {"traverse": traverse, "mask": mask}
    if max_pages is not None:
        kwargs["max_pages"] = max_pages
    rows = list(client.Installation.list_iter(**kwargs))
    return build_installation_lookup(rows)
