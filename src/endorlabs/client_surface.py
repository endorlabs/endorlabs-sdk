"""Resource-oriented Client facade for the Endor Labs SDK.

Provides endorlabs.Client(api_client=..., tenant=...) with .namespaces, etc.,
delegating to existing module-level list/get/create/update/delete functions.
All facades are built from the registries in endorlabs.registry.
"""

from __future__ import annotations

from typing import Any

from .api_client import APIClient
from .facade import ResourceFacade
from .registry import CUSTOM_FACADE_REGISTRY, RESOURCE_REGISTRY


class Client:
    """Resource-oriented client; holds default namespace and exposes resource facades.

    Use endorlabs.Client(tenant="...") or
    endorlabs.Client(api_client=..., tenant="...").
    Then client.namespaces.list(traverse=True), client.namespaces.get(uuid), etc.
    All resources are driven by the registry in endorlabs.registry.
    """

    def __init__(
        self,
        api_client: APIClient | None = None,
        tenant: str | None = None,
        **client_kwargs: Any,
    ) -> None:
        if api_client is None:
            api_client = APIClient(**client_kwargs)
        self._client: APIClient = api_client
        self._default_namespace: str | None = tenant

        for entry in RESOURCE_REGISTRY:
            facade = ResourceFacade[entry.model_class](
                self._client,
                self._default_namespace,
                list_fn=entry.list_fn,
                get_fn=entry.get_fn,
                create_fn=entry.create_fn,
                update_fn=entry.update_fn,
                delete_fn=entry.delete_fn,
            )
            setattr(self, entry.attr_name, facade)
        for entry in CUSTOM_FACADE_REGISTRY:
            setattr(
                self,
                entry.attr_name,
                entry.factory(self._client, self._default_namespace),
            )
