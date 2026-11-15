"""SupportedToolChainVersion catalog reads (platform ``system`` namespace).

x-internal OpenAPI kind — exposed as a custom Client facade for hosts/skills
without reaching into ``Client._client``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from endorlabs.api_client import APIClient

RESOURCE_PATH = "supported-toolchain-versions"
DEFAULT_NAMESPACE = "system"


def list_supported_toolchain_versions(
    client: APIClient,
    *,
    namespace: str = DEFAULT_NAMESPACE,
    filter_expr: str | None = None,
    max_pages: int | None = None,
    max_items: int | None = None,
) -> list[dict[str, Any]]:
    """Paginate SupportedToolChainVersion rows as plain JSON dicts."""
    url = f"v1/namespaces/{namespace}/{RESOURCE_PATH}"
    params: dict[str, Any] = {}
    if filter_expr:
        params["list_parameters.filter"] = filter_expr
    # ``get_all`` yields decoded JSON objects (dicts) for this path.
    return list(
        client.get_all(url, params=params, max_pages=max_pages, max_items=max_items)
    )
