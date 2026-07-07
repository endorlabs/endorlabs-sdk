"""Estate session bootstrap: single topology discovery per session."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from endorlabs import Client
    from endorlabs.query.topology import TopologySnapshot


def bootstrap_topology(
    client: Client,
    namespace: str,
    *,
    traverse: bool = True,
    max_pages: int | None = None,
    exclude_sbom: bool = False,
) -> TopologySnapshot:
    """Single discovery for online dashboard + offline collect preflight."""
    return client.Query.Project.discover(
        namespace,
        traverse=traverse,
        max_pages=max_pages,
        exclude_sbom=exclude_sbom,
    )
