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
from .facade import OssResourceFacade, ResourceFacade, SystemResourceFacade
from .registry import CUSTOM_FACADE_REGISTRY, RESOURCE_REGISTRY, ResourceEntry
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

    Transport options (when creating APIClient): timeout, content_type,
    accept_encoding, max_retries, base_url. Explicit args take precedence over
    **client_kwargs. Other APIClient options (auth, logging_level, etc.) go via
    **client_kwargs. Use content_type="application/json" if compact responses
    cause validation issues.
    """

    def __init__(
        self,
        api_client: APIClient | None = None,
        tenant: str | None = None,
        *,
        timeout: float = 60.0,
        content_type: str = "application/jsoncompact",
        accept_encoding: str | None = "gzip, br, zstd",
        max_retries: int = 5,
        base_url: str | None = None,
        **client_kwargs: Any,
    ) -> None:
        super().__init__()
        self._own_client = api_client is None
        if api_client is None:
            api_kwargs: dict[str, Any] = {**client_kwargs}
            api_kwargs["timeout"] = timeout
            api_kwargs["content_type"] = content_type
            api_kwargs["accept_encoding"] = accept_encoding
            api_kwargs["max_retries"] = max_retries
            api_kwargs["base_url"] = base_url
            api_client = APIClient(**api_kwargs)
        self._client: APIClient | None = api_client
        self._default_namespace: str | None = tenant

        # self._client is always set here (assigned above); None only after close().
        for entry in RESOURCE_REGISTRY:
            setattr(self, entry.attr_name, self._build_facade(entry))
        for custom in CUSTOM_FACADE_REGISTRY:
            setattr(
                self,
                custom.attr_name,
                custom.factory(self._client, self._default_namespace),
            )

    # -- Internal factory ---------------------------------------------------

    def _build_facade(
        self, entry: ResourceEntry
    ) -> SystemResourceFacade[Any] | OssResourceFacade[Any] | ResourceFacade[Any]:
        """Build the appropriate facade for *entry* based on its scope."""
        if self._client is None:
            raise RuntimeError("Client is closed.")  # pragma: no cover

        if entry.scope == "system":
            return cast(
                "SystemResourceFacade[Any]",
                SystemResourceFacade[entry.model_class](
                    self._client,
                    self._default_namespace,
                    list_fn=entry.list_fn,
                    list_iter_fn=entry.list_iter_fn,
                    get_fn=entry.get_fn,
                    resource_name=entry.resource_name,
                    parent_kind=entry.parent_kind,
                    tags_paths=[],
                ),
            )

        tags_paths = get_tags_update_paths(entry.model_class) if entry.update_fn else []

        if entry.scope == "oss":
            if entry.get_fn is None:
                raise ValueError("oss scope requires get_fn")
            return cast(
                "OssResourceFacade[Any]",
                OssResourceFacade[entry.model_class](
                    self._client,
                    "oss",
                    list_fn=entry.list_fn,
                    get_fn=entry.get_fn,
                    create_fn=entry.create_fn,
                    update_fn=entry.update_fn,
                    delete_fn=entry.delete_fn,
                    list_iter_fn=entry.list_iter_fn,
                    tags_paths=tags_paths,
                    resource_name=entry.resource_name,
                    parent_kind=entry.parent_kind,
                    build_create_payload_fn=entry.build_create_payload_fn,
                ),
            )

        # tenant scope (entry.scope is None)
        if entry.get_fn is None:
            raise ValueError("tenant scope requires get_fn")
        return cast(
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
                build_create_payload_fn=entry.build_create_payload_fn,
            ),
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
        return

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
