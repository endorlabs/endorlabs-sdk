"""Resource-oriented Client facade for the Endor Labs SDK.

Provides endorlabs.Client(api_client=..., tenant=...) with .namespaces, etc.,
building ResourceRuntimeFacade instances from declarative registry entries.
All facades are built from the registries in endorlabs.registry.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any, cast

from .api_client import APIClient

if TYPE_CHECKING:
    from collections.abc import Callable
from .core.exceptions import ValidationError
from .core.filter import F
from .facade import ResourceRuntimeFacade
from .registry import CUSTOM_FACADE_REGISTRY, RESOURCE_REGISTRY, ResourceEntry
from .utils.logging_config import get_resource_logger
from .utils.model_validation import get_tags_update_paths
from .utils.polling import wait_until as _wait_until

_logger = get_resource_logger(__name__)


class Client:
    """Resource-oriented client; holds default namespace and exposes resource facades.

    Use endorlabs.Client(tenant="..."), endorlabs.Client() with
    ``ENDOR_NAMESPACE`` set, or endorlabs.Client(api_client=..., tenant="...").
    Then client.Namespace.list(traverse=True), client.Namespace.get(uuid), etc.
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
        self._default_namespace: str | None = tenant or (
            os.environ.get("ENDOR_NAMESPACE", "").strip() or None
        )

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

    def _build_facade(self, entry: ResourceEntry) -> ResourceRuntimeFacade[Any]:
        """Build the appropriate facade for *entry* based on its scope."""
        if self._client is None:
            raise ValidationError("Client is closed.")  # pragma: no cover

        tags_paths = (
            get_tags_update_paths(entry.model_class)
            if "update" in entry.supported_ops
            else []
        )
        return cast(
            "ResourceRuntimeFacade[Any]",
            ResourceRuntimeFacade[entry.model_class](
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

    def _identity_from_user_info(self, user_info: dict[str, object]) -> str | None:
        """Extract an identity string from ``/v1/auth`` response payload."""
        user = user_info.get("user")
        if not isinstance(user, dict):
            return None
        user_dict = cast("dict[str, object]", user)
        spec = user_dict.get("spec")
        if isinstance(spec, dict):
            spec_dict = cast("dict[str, object]", spec)
            for key in ("email", "user_name"):
                value = spec_dict.get(key)
                if isinstance(value, str) and value:
                    return value
        meta = user_dict.get("meta")
        if isinstance(meta, dict):
            meta_dict = cast("dict[str, object]", meta)
            name = meta_dict.get("name")
            if isinstance(name, str) and name:
                return name
        return None

    def _whoami_from_auth_policy_fallback(self, api_key: str) -> str | None:
        """Best-effort compatibility fallback via AuthorizationPolicy."""
        try:
            policies: list[Any] = self.AuthorizationPolicy.list(  # type: ignore[attr-defined]
                traverse=True,
                concurrent=False,
                filter=F("spec.clause").contains(api_key),
                page_size=1,
                max_pages=1,
            )
        except Exception as exc:
            _logger.debug(
                "AuthorizationPolicy lookup for API key failed: %s", exc, exc_info=True
            )
            return None
        if not policies:
            return None
        policy = cast("Any", policies[0])
        meta = getattr(policy, "meta", None)
        if meta is None:
            return None
        raw_name = getattr(meta, "name", None)
        return str(raw_name) if raw_name else None

    def whoami(self) -> str | None:
        """Resolve the current user identity.

        This method first queries the canonical ``/v1/auth`` user-info endpoint.
        If identity fields are unavailable and API-key auth is active, it falls
        back to the historical AuthorizationPolicy lookup heuristic.

        Returns:
            Resolved identity string (email/username/name), or ``None`` if not found.
        """
        if self._client is None:
            raise ValidationError("Client is closed.")

        user_info = self._client.get_user_info()
        if isinstance(user_info, dict):
            identity = self._identity_from_user_info(user_info)
            if identity:
                return identity

        if not self._client.is_api_key_auth or not self._client.key:
            return None

        return self._whoami_from_auth_policy_fallback(self._client.key)

    def wait_until(
        self,
        predicate: Callable[[], bool],
        timeout: float = 60,
        poll_interval_max: float = 10,
    ) -> bool:
        """Block until predicate returns True or timeout is exceeded.

        Uses jittered exponential backoff (cap at poll_interval_max).
        Typical usage: client.wait_until(
            lambda: client.ScanResult.get(uuid).spec.status == "COMPLETED",
            timeout=120,
        )
        """
        return _wait_until(
            predicate, timeout=timeout, poll_interval_max=poll_interval_max
        )
