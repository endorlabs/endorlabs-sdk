"""Resource-oriented Client facade for the Endor Labs SDK.

Provides endorlabs.Client(api_client=..., tenant=...) with .namespaces, etc.,
building ResourceRuntimeFacade instances from declarative registry entries.
All facades are built from the registries in endorlabs.registry.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, Literal, cast

from .api_client import APIClient
from .core.exceptions import ValidationError
from .core.filter import F
from .core.whoami import WhoamiResult
from .facade import FACADE_CLASS_BY_ATTR, ResourceRuntimeFacade
from .registry import CUSTOM_FACADE_REGISTRY, RESOURCE_REGISTRY, ResourceEntry
from .utils.bearer_token import (
    expires_in_seconds,
    jwt_expiration_unverified,
    parse_iso_datetime,
)
from .utils.endorctl_config import (
    endorctl_config_path,
    resolve_client_default_namespace,
)
from .utils.logging_config import get_resource_logger
from .utils.model_validation import get_tags_update_paths
from .utils.polling import wait_until as _wait_until

if TYPE_CHECKING:
    from collections.abc import Callable

_logger = get_resource_logger(__name__)


class Client:
    """Resource-oriented client; holds default namespace and exposes resource facades.

    Use endorlabs.Client(tenant="..."), endorlabs.Client() with
    ``ENDOR_NAMESPACE`` or endorctl ``~/.endorctl/config.yaml`` set, or
    endorlabs.Client(api_client=..., tenant="...").
    Then client.Namespace.list(traverse=True), client.Namespace.get(uuid), etc.
    All resources are driven by the registry in endorlabs.registry.

    When api_client is not passed, Client creates an APIClient and owns it.
    Use ``with endorlabs.Client(tenant="...") as client:`` or call
    ``client.close()`` when done to release connections. When api_client is
    passed, the caller owns it and must close it themselves.

    Transport options (when creating APIClient): timeout, content_type,
    accept_encoding, max_retries, base_url. Explicit args take precedence over
    environment variables (``ENDOR_REQUEST_TIMEOUT``, ``ENDOR_API_TIMEOUT``).
    Other APIClient options (auth, logging_level, etc.) go via **client_kwargs.
    Use content_type="application/json" if compact responses cause validation issues.

    Route accessors (``list_by_project``, ``list_for_context``, …) expect **resource
    objects** from ``.get()`` or ``.list()`` — not UUID strings. They return ``list[T]``
    like ``.list()``; stitch accessors (``to_*``) return ``RouteResult`` (``.values``).

    Example::

        with endorlabs.Client(tenant="tenant.namespace") as client:
            print(client.whoami())
            projects = client.Project.list(traverse=True, max_pages=1)
            project = projects[0]
            scans = client.ScanResult.list_by_project(project, limit=1)
            if scans:
                findings = client.Finding.list_for_context(scans[0], max_pages=1)

    Pagination: ``.list()`` defaults to server page size (~100). Use ``max_pages`` to
    cap fetch depth; ``limit=N`` is an alias for ``page_size=N``.
    """

    def __init__(
        self,
        api_client: APIClient | None = None,
        tenant: str | None = None,
        *,
        timeout: float | None = None,
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
        self._default_namespace, ns_source = resolve_client_default_namespace(tenant)
        if ns_source == "env":
            _logger.info("Default namespace from ENDOR_NAMESPACE environment variable")
        elif ns_source == "endorctl_config":
            _logger.info(
                "Default namespace from endorctl config %s",
                endorctl_config_path(),
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
        facade_cls = FACADE_CLASS_BY_ATTR.get(entry.attr_name, ResourceRuntimeFacade)
        return facade_cls(
            self._client,
            self._default_namespace,
            entry,
            tags_paths=tags_paths,
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

    def _whoami_from_user_info(self, user_info: dict[str, object]) -> WhoamiResult:
        """Build WhoamiResult from ``/v1/auth`` payload."""
        identity = self._identity_from_user_info(user_info)
        auth_source = user_info.get("authentication_source")
        authentication_source = (
            str(auth_source) if isinstance(auth_source, str) and auth_source else None
        )
        expiration_time: datetime | None = None
        expiration_source: Literal["v1_auth", "jwt", "api_key_exchange"] | None = None
        for key in ("expiration_time", "expirationTime"):
            raw = user_info.get(key)
            if isinstance(raw, str) and raw:
                expiration_time = parse_iso_datetime(raw)
                if expiration_time is not None:
                    expiration_source = "v1_auth"
                break
        remaining = expires_in_seconds(expiration_time)
        is_expired = remaining <= 0 if remaining is not None else None
        auth_type: Literal["api-key", "browser"] | None = None
        if self._client is not None:
            auth_type = self._client.auth_type
        return WhoamiResult(
            identity=identity,
            authentication_source=authentication_source,
            expiration_time=expiration_time,
            expires_in_seconds=remaining,
            is_expired=is_expired,
            auth_type=auth_type,
            expiration_source=expiration_source,
        )

    def _whoami_from_bearer_jwt(self, token: str) -> WhoamiResult | None:
        """JWT expiry fallback when ``/v1/auth`` is unavailable."""
        expiration_time = jwt_expiration_unverified(token)
        if expiration_time is None:
            return None
        remaining = expires_in_seconds(expiration_time)
        auth_type: Literal["api-key", "browser"] | None = None
        if self._client is not None:
            auth_type = self._client.auth_type
        return WhoamiResult(
            identity=None,
            expiration_time=expiration_time,
            expires_in_seconds=remaining,
            is_expired=remaining <= 0 if remaining is not None else None,
            auth_type=auth_type,
            expiration_source="jwt",
        )

    def _whoami_from_api_key_exchange(self) -> WhoamiResult | None:
        """Attach API-key exchange expiry when ``/v1/auth`` omits expiration_time."""
        if self._client is None or not self._client.is_api_key_auth:
            return None
        token_expires = getattr(self._client, "_token_expires", None)
        if token_expires is None:
            return None
        remaining = expires_in_seconds(token_expires)
        return WhoamiResult(
            identity=None,
            expiration_time=token_expires,
            expires_in_seconds=remaining,
            is_expired=remaining <= 0 if remaining is not None else None,
            auth_type="api-key",
            expiration_source="api_key_exchange",
        )

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

    def whoami(self) -> WhoamiResult:
        """Resolve identity and optional bearer session metadata.

        Queries ``GET /v1/auth`` first. For bearer/browser auth, when the token is
        expired and ``/v1/auth`` is unavailable, falls back to JWT ``exp`` decode.
        API-key auth may fall back to AuthorizationPolicy lookup for identity and
        uses exchange metadata when ``/v1/auth`` omits ``expiration_time``.

        Returns:
            ``WhoamiResult`` — use ``str(result)`` or ``result.identity`` for the
            email/username; inspect ``expiration_time`` / ``expires_in_seconds`` for
            bearer sessions.
        """
        if self._client is None:
            raise ValidationError("Client is closed.")

        user_info = self._client.get_user_info()
        if isinstance(user_info, dict) and user_info:
            result = self._whoami_from_user_info(user_info)
            if result.identity:
                return result
            if result.expiration_time is not None:
                return result

        session: WhoamiResult | None = None
        if self._client.auth_type == "browser":
            token = self._client.bearer_token_for_metadata()
            if isinstance(token, str) and token:
                session = self._whoami_from_bearer_jwt(token)
        elif self._client.is_api_key_auth:
            session = self._whoami_from_api_key_exchange()

        identity: str | None = None
        if self._client.is_api_key_auth and self._client.key:
            identity = self._whoami_from_auth_policy_fallback(self._client.key)

        if session is not None:
            return WhoamiResult(
                identity=identity or session.identity,
                authentication_source=session.authentication_source,
                expiration_time=session.expiration_time,
                expires_in_seconds=session.expires_in_seconds,
                is_expired=session.is_expired,
                auth_type=session.auth_type,
                expiration_source=session.expiration_source,
            )

        if identity:
            auth_type: Literal["api-key", "browser"] | None = self._client.auth_type
            return WhoamiResult(identity=identity, auth_type=auth_type)

        return WhoamiResult(identity=None, auth_type=self._client.auth_type)

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


_init_doc = (Client.__doc__ or "").split("\n\n", 1)[0].strip()
if _init_doc:
    Client.__init__.__doc__ = _init_doc
