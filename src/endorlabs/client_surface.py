"""Resource-oriented Client facade for the Endor Labs SDK.

Provides endorlabs.Client(api_client=..., tenant=...) with .namespaces, etc.,
delegating to existing module-level list/get/create/update/delete functions.
All facades are built from the registries in endorlabs.registry.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from .api_client import APIClient

if TYPE_CHECKING:
    from collections.abc import Callable
from .facade import ResourceFacade
from .models.base import RESOURCE_NAME_TO_TYPE
from .registry import CUSTOM_FACADE_REGISTRY, RESOURCE_REGISTRY
from .utils.model_validation import get_tags_update_paths
from .utils.polling import wait_until as _wait_until


class Client:
    """Resource-oriented client; holds default namespace and exposes resource facades.

    Use endorlabs.Client(tenant="...") or
    endorlabs.Client(api_client=..., tenant="...").
    Then client.namespace.list(traverse=True), client.namespace.get(uuid), etc.
    All resources are driven by the registry in endorlabs.registry.

    When api_client is not passed, Client creates an APIClient and owns it.
    Use ``with endorlabs.Client(tenant="...") as client:`` or call
    ``client.close()`` when done to release connections. When api_client is
    passed, the caller owns it and must close it themselves.
    """

    def __init__(
        self,
        api_client: APIClient | None = None,
        tenant: str | None = None,
        **client_kwargs: Any,
    ) -> None:
        super().__init__()
        self._own_client = api_client is None
        if api_client is None:
            api_client = APIClient(**client_kwargs)
        self._client: APIClient | None = api_client
        self._default_namespace: str | None = tenant

        assert self._client is not None  # Set in __init__; None only after close()
        for entry in RESOURCE_REGISTRY:
            resource_type = RESOURCE_NAME_TO_TYPE.get(entry.resource_name, "")
            tags_paths = get_tags_update_paths(resource_type) if entry.update_fn else []
            facade = cast(
                "ResourceFacade[Any]",
                ResourceFacade[entry.model_class](
                    self._client,
                    self._default_namespace,
                    list_fn=entry.list_fn,
                    get_fn=entry.get_fn,
                    create_fn=entry.create_fn,
                    update_fn=entry.update_fn,
                    delete_fn=entry.delete_fn,
                    list_iter_fn=entry.list_iter_fn,
                    tags_paths=tags_paths,
                    resource_name=entry.resource_name,
                    parent_kind=entry.parent_kind,
                ),
            )
            setattr(self, entry.attr_name, facade)
        for entry in CUSTOM_FACADE_REGISTRY:
            setattr(
                self,
                entry.attr_name,
                entry.factory(self._client, self._default_namespace),
            )

    def close(self) -> None:
        """Release the underlying transport if this Client created it.

        Idempotent. When api_client was passed to __init__, this does nothing.
        """
        if self._own_client and self._client is not None:
            self._client.close()
            self._client = None

    def __enter__(self) -> Client:
        """Enter context manager; return self."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit context manager; close the client. Do not suppress exceptions."""
        self.close()
        return None

    def wait_until(
        self,
        predicate: Callable[[], bool],
        timeout: float = 60,
        poll_interval_max: float = 10,
    ) -> bool:
        """Block until predicate returns True or timeout is exceeded.

        Uses jittered exponential backoff (cap at poll_interval_max).
        Typical usage: client.wait_until(
            lambda: client.scan_result.get(uuid).spec.status == "COMPLETED",
            timeout=120,
        )
        """
        return _wait_until(
            predicate, timeout=timeout, poll_interval_max=poll_interval_max
        )
