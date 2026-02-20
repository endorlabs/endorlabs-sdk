"""Resource-oriented Client facade for the Endor Labs SDK.

Provides endorlabs.Client(api_client=..., tenant=...) with .namespaces, etc.,
building ResourceFacade instances from declarative registry entries.
All facades are built from the registries in endorlabs.registry.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from .api_client import APIClient

if TYPE_CHECKING:
    from collections.abc import Callable
from .facade import ResourceFacade
from .filter import F
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
        max_retries: int | None = None,
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

    def _build_facade(self, entry: ResourceEntry) -> ResourceFacade[Any]:
        """Build the appropriate facade for *entry* based on its scope."""
        if self._client is None:
            raise RuntimeError("Client is closed.")  # pragma: no cover

        tags_paths = (
            get_tags_update_paths(entry.model_class)
            if "update" in entry.supported_ops
            else []
        )
        return cast(
            "ResourceFacade[Any]",
            ResourceFacade[entry.model_class](
                self._client,
                self._default_namespace,
                entry,
                tags_paths=tags_paths,
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

    def whoami(self) -> str | None:
        """Resolve the current user identity via AuthorizationPolicy.

        When authenticated with an API key, queries AuthorizationPolicy
        resources whose ``spec.clause`` contains the key value. Returns the
        ``meta.name`` of the first matching policy, which typically holds the
        human-readable identity bound to the key.

        Returns:
            The ``meta.name`` of the matching AuthorizationPolicy, or ``None``
            if no match is found or if using browser authentication.
        """
        if self._client is None:
            raise RuntimeError("Client is closed.")
        auth_type: str = self._client._auth_type  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
        if auth_type != "api-key" or not self._client.key:
            return None

        policies: list[Any] = self.authorization_policy.list(  # type: ignore[attr-defined]
            traverse=True,
            filter=F("spec.clause").contains(self._client.key),
            page_size=1,
            max_pages=1,
        )
        if policies:
            policy = cast("Any", policies[0])
            meta = getattr(policy, "meta", None)
            if meta is not None:
                raw_name = getattr(meta, "name", None)
                return str(raw_name) if raw_name else None
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
