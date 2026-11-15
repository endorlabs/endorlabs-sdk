"""SupportedToolChainVersion catalog reads (platform ``system`` namespace).

x-internal OpenAPI kind — exposed as a custom Client facade for hosts/skills
without reaching into ``Client._client``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from endorlabs.api_client import APIClient

RESOURCE_PATH = "supported-toolchain-versions"
DEFAULT_NAMESPACE = "system"

Completeness = Literal["complete", "capped", "unknown"]


@dataclass(frozen=True, slots=True)
class ToolchainChoice:
    """Normalized toolchain choice for host recommendation UIs."""

    name: str
    version: str
    ecosystem: str | None = None
    download_url: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ToolchainCatalogResult:
    """Typed catalog page with completeness (denied ≠ empty)."""

    items: tuple[dict[str, Any], ...]
    choices: tuple[ToolchainChoice, ...]
    owner_namespace: str
    completeness: Completeness
    stop_reason: str | None = None


def _as_dict(row: Any) -> dict[str, Any]:
    if isinstance(row, dict):
        return dict(row)
    dump = getattr(row, "model_dump", None)
    if callable(dump):
        data = dump(mode="json", exclude_none=False)
        if isinstance(data, dict):
            return data
    return {}


def normalize_toolchain_choice(row: dict[str, Any]) -> ToolchainChoice:
    """Project one catalog row into a normalized choice (no invented IDs)."""
    meta = row.get("meta") if isinstance(row.get("meta"), dict) else {}
    spec = row.get("spec") if isinstance(row.get("spec"), dict) else {}
    name = str(meta.get("name") or spec.get("name") or row.get("name") or "")
    version = str(
        spec.get("version") or meta.get("version") or row.get("version") or ""
    )
    ecosystem = spec.get("ecosystem") or spec.get("language") or None
    if ecosystem is not None:
        ecosystem = str(ecosystem)
    url = spec.get("download_url") or spec.get("url")
    return ToolchainChoice(
        name=name,
        version=version,
        ecosystem=ecosystem,
        download_url=str(url) if url else None,
        raw=row,
    )


def list_supported_toolchain_versions(
    client: APIClient,
    *,
    namespace: str = DEFAULT_NAMESPACE,
    filter_expr: str | None = None,
    max_pages: int | None = None,
    max_items: int | None = None,
) -> list[dict[str, Any]]:
    """Paginate SupportedToolChainVersion rows as plain JSON dicts."""
    return list(
        list_supported_toolchain_catalog(
            client,
            namespace=namespace,
            filter_expr=filter_expr,
            max_pages=max_pages,
            max_items=max_items,
        ).items
    )


def list_supported_toolchain_catalog(
    client: APIClient,
    *,
    namespace: str = DEFAULT_NAMESPACE,
    filter_expr: str | None = None,
    max_pages: int | None = None,
    max_items: int | None = None,
) -> ToolchainCatalogResult:
    """Paginate toolchain rows with normalized choices and completeness.

    Callers must treat HTTP 403/denied separately from an empty inventory —
    this helper surfaces page ``completeness`` from the transport budget.
    """
    url = f"v1/namespaces/{namespace}/{RESOURCE_PATH}"
    params: dict[str, Any] = {}
    if filter_expr:
        params["list_parameters.filter"] = filter_expr
    pages = list(
        client.iter_pages(
            url,
            params=params,
            owner_namespace=namespace,
            max_pages=max_pages,
            max_items=max_items,
        )
    )
    items: list[dict[str, Any]] = []
    for page in pages:
        items.extend(_as_dict(x) for x in page.items)
    completeness: Completeness = "complete"
    stop_reason: str | None = None
    if pages:
        last = pages[-1]
        completeness = last.completeness
        stop_reason = last.stop_reason
    elif max_pages == 0 or max_items == 0:
        completeness = "capped"
        stop_reason = "max_items" if max_items == 0 else "max_pages"
    choices = tuple(normalize_toolchain_choice(item) for item in items)
    return ToolchainCatalogResult(
        items=tuple(items),
        choices=choices,
        owner_namespace=namespace,
        completeness=completeness,
        stop_reason=stop_reason,
    )
