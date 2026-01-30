"""Resource facade for the resource-oriented Client API.

Provides a generic ResourceFacade[T] that delegates to module-level
list/get/create/update/delete functions and resolves default namespace.
Also provides ScanLogsFacade for the request-based scan logs workflow;
Client attaches it via CUSTOM_FACADE_REGISTRY.
See docs/guides/scan-logs-and-scan-log-request.md.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .types import ListParameters

if TYPE_CHECKING:
    from collections.abc import Callable

    from .api_client import APIClient
    from .resources.scan_log_request import ScanLogLevel, ScanLogRequestLogMessage


class ResourceFacade[T]:
    """Facade for a single resource type; delegates to module functions.

    Resolves namespace from argument or client default; builds ListParameters
    from convenience kwargs when list_params is not provided.
    """

    def __init__(
        self,
        client: APIClient,
        default_namespace: str | None,
        list_fn: Callable[..., list[T]],
        get_fn: Callable[..., T],
        create_fn: Callable[..., T],
        update_fn: Callable[..., T] | None = None,
        delete_fn: Callable[..., bool] | None = None,
    ) -> None:
        self._client = client
        self._default_namespace = default_namespace
        self._list_fn = list_fn
        self._get_fn = get_fn
        self._create_fn = create_fn
        self._update_fn = update_fn
        self._delete_fn = delete_fn

    def _ns(self, namespace: str | None) -> str:
        ns = namespace if namespace is not None else self._default_namespace
        if ns is None:
            raise ValueError(
                "Namespace required: set tenant= on Client(...) or pass namespace=."
            )
        return ns

    def _list_params(
        self,
        list_params: ListParameters | None,
        traverse: bool = False,
        **kwargs: Any,
    ) -> ListParameters | None:
        if list_params is not None:
            return list_params
        if not kwargs and not traverse:
            return None
        return ListParameters(traverse=traverse or None, **kwargs)

    def list(
        self,
        traverse: bool = False,
        namespace: str | None = None,
        list_params: ListParameters | None = None,
        max_pages: int | None = None,
        **kwargs: Any,
    ) -> list[T]:
        """List resources; uses default namespace when namespace= not passed."""
        ns = self._ns(namespace)
        lp = self._list_params(list_params, traverse=traverse, **kwargs)
        return self._list_fn(self._client, ns, lp, max_pages)

    def get(self, resource_id: str, namespace: str | None = None) -> T:
        """Get a resource by ID."""
        ns = self._ns(namespace)
        return self._get_fn(self._client, ns, resource_id)

    def create(
        self,
        payload: Any,
        namespace: str | None = None,
    ) -> T:
        """Create a resource."""
        ns = self._ns(namespace)
        return self._create_fn(self._client, ns, payload)

    def update(
        self,
        resource_id: str,
        payload: Any,
        update_mask: str,
        namespace: str | None = None,
    ) -> T:
        """Update a resource."""
        if self._update_fn is None:
            raise NotImplementedError(
                "This resource does not support update."
            ) from None
        ns = self._ns(namespace)
        return self._update_fn(self._client, ns, resource_id, payload, update_mask)

    def delete(self, resource_id: str, namespace: str | None = None) -> bool:
        """Delete a resource."""
        if self._delete_fn is None:
            raise NotImplementedError(
                "This resource does not support delete."
            ) from None
        ns = self._ns(namespace)
        return self._delete_fn(self._client, ns, resource_id)


class ScanLogsFacade:
    """Facade for retrieving scan logs (request-based API; not in registry).

    Use client.scan_logs.get_logs(scan_result_uuid) after obtaining a scan
    result UUID (e.g. from client.scan_results.list() or .get()).
    """

    def __init__(self, client: APIClient, default_namespace: str | None) -> None:
        self._client = client
        self._default_namespace = default_namespace

    def _ns(self, namespace: str | None) -> str:
        ns = namespace if namespace is not None else self._default_namespace
        if ns is None:
            raise ValueError(
                "Namespace required: set tenant= on Client(...) or pass namespace=."
            )
        return ns

    def get_logs(
        self,
        scan_result_uuid: str,
        namespace: str | None = None,
        max_entries: int = 100,
        log_levels: list[ScanLogLevel] | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
        newest_first: bool | None = None,
    ) -> list[ScanLogRequestLogMessage]:
        """Retrieve log messages for a scan result.

        Delegates to ScanLogRequest API (POST only); returns spec.log_messages.
        See docs/guides/scan-logs-and-scan-log-request.md.
        """
        from .resources.scan_log_request import get_scan_result_logs

        ns = self._ns(namespace)
        result = get_scan_result_logs(
            self._client,
            ns,
            scan_result_uuid,
            max_entries=max_entries,
            log_levels=log_levels,
            start_time=start_time,
            end_time=end_time,
            newest_first=newest_first,
        )
        return result if result is not None else []
