"""Resource facade for the resource-oriented Client API.

Provides a generic ResourceFacade[T] that delegates to module-level
list/get/create/update/delete functions and resolves default namespace.
Also provides ScanLogsFacade for the request-based scan logs workflow;
Client attaches it via CUSTOM_FACADE_REGISTRY.
See docs/reference/resources.md (scan_log_request) and
docs/guides/retrieving-scan-results.md.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Generic, TypeGuard, TypeVar, cast

from .exceptions import AmbiguousError, NotFoundError
from .types import ListParameters
from .utils.model_validation import (
    build_filter_from_identity_kwargs,
    get_list_filter_map,
)
from .utils.namespace import resolve_namespace_for_resource

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

    from .api_client import APIClient
    from .resources.scan_log_request import ScanLogLevel, ScanLogRequestLogMessage

T = TypeVar("T")


class ResourceFacade(Generic[T]):
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
        create_fn: Callable[..., T] | None = None,
        update_fn: Callable[..., T] | None = None,
        delete_fn: Callable[..., bool] | None = None,
        list_iter_fn: Callable[..., Iterator[T]] | None = None,
        tags_paths: list[str] | None = None,
        resource_name: str = "",
        parent_kind: str | None = None,
    ) -> None:
        super().__init__()
        self._client = client
        self._default_namespace = default_namespace
        self._list_fn = list_fn
        self._get_fn = get_fn
        self._create_fn = create_fn
        self._update_fn = update_fn
        self._delete_fn = delete_fn
        self._list_iter_fn = list_iter_fn
        self._tags_paths = tags_paths or []
        self._resource_name = resource_name
        self._parent_kind = parent_kind

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
        parent: Any = None,
        **kwargs: Any,
    ) -> list[T]:
        """List resources; uses default namespace when namespace= not passed.

        Flat kwargs include filter, mask, traverse, page_size, page_token,
        sort_by, desc, count, from_date, to_date. When the resource supports
        identity kwargs (e.g. name, git_url), pass them and they are translated
        to filter clauses (e.g. meta.name == 'backend'). When the resource
        supports parent= (registry parent_kind set), pass a parent resource to
        scope the list by namespace and meta.parent_uuid.
        """
        from .models.base import RESOURCE_NAME_TO_TYPE

        if parent is not None:
            if self._parent_kind is None:
                raise ValueError(
                    "This resource does not support list(parent=)."
                ) from None
            namespace = self._ns(
                resolve_namespace_for_resource(parent, self._default_namespace)
            )
        ns = self._ns(namespace)
        resource_type = RESOURCE_NAME_TO_TYPE.get(self._resource_name, "")
        filter_map = get_list_filter_map(resource_type)
        merged_filter, remaining_kwargs = build_filter_from_identity_kwargs(
            filter_map, dict(kwargs)
        )
        if merged_filter is not None:
            remaining_kwargs["filter"] = merged_filter
        if parent is not None:
            parent_uuid = getattr(parent, "uuid", "")
            parent_filter = f'meta.parent_uuid=="{parent_uuid}"'
            existing = remaining_kwargs.get("filter")
            remaining_kwargs["filter"] = (
                f"{existing} AND {parent_filter}" if existing else parent_filter
            )
        lp = self._list_params(list_params, traverse=traverse, **remaining_kwargs)
        return self._list_fn(self._client, ns, lp, max_pages)

    def lookup(
        self,
        traverse: bool = False,
        namespace: str | None = None,
        list_params: ListParameters | None = None,
        max_pages: int = 2,
        parent: Any = None,
        **kwargs: Any,
    ) -> T:
        """Return the single resource matching the given identity kwargs.

        Calls list() with the same kwargs and max_pages (default 2). Returns
        the single item if exactly one matches; raises NotFoundError if none,
        AmbiguousError if more than one.
        """
        items = self.list(
            traverse=traverse,
            namespace=namespace,
            list_params=list_params,
            max_pages=max_pages,
            parent=parent,
            **kwargs,
        )
        if not items:
            raise NotFoundError(
                "No resource matched the given criteria.",
                operation="lookup",
            )
        if len(items) > 1:
            raise AmbiguousError(
                f"Multiple resources ({len(items)}) match; narrow the query.",
                operation="lookup",
            )
        return items[0]

    def list_iter(
        self,
        traverse: bool = False,
        namespace: str | None = None,
        list_params: ListParameters | None = None,
        max_pages: int | None = None,
        parent: Any = None,
        **kwargs: Any,
    ) -> Iterator[T]:
        """Iterate over resources without materializing the full list.

        Accepts the same kwargs as list() (filter, mask, sort_by, desc, etc.).
        When the resource supports parent=, pass a parent resource to scope.
        """
        if self._list_iter_fn is None:
            raise NotImplementedError(
                "This resource does not support list_iter."
            ) from None
        if parent is not None:
            if self._parent_kind is None:
                raise ValueError(
                    "This resource does not support list_iter(parent=)."
                ) from None
            namespace = self._ns(
                resolve_namespace_for_resource(parent, self._default_namespace)
            )
        ns = self._ns(namespace)
        if parent is not None:
            parent_uuid = getattr(parent, "uuid", "")
            parent_filter = f'meta.parent_uuid=="{parent_uuid}"'
            existing = kwargs.get("filter")
            kwargs = {
                **kwargs,
                "filter": f"{existing} AND {parent_filter}"
                if existing
                else parent_filter,
            }
        lp = self._list_params(list_params, traverse=traverse, **kwargs)
        return self._list_iter_fn(self._client, ns, lp, max_pages, **kwargs)

    def _is_resource_like(self, value: Any) -> TypeGuard[T]:
        """Return True if value has uuid and tenant_meta (resource object)."""
        return (
            hasattr(value, "uuid")
            and hasattr(value, "tenant_meta")
            and value is not None
        )

    def get(self, id_or_resource: str | T, namespace: str | None = None) -> T:
        """Get a resource by ID or resource object (anchors to resource ns)."""
        if self._is_resource_like(id_or_resource):
            res = cast("Any", id_or_resource)
            uuid = res.uuid
            ns = (
                self._ns(namespace)
                if namespace is not None
                else self._ns(
                    resolve_namespace_for_resource(res, self._default_namespace)
                )
            )
        else:
            uuid = id_or_resource
            ns = self._ns(namespace)
        return self._get_fn(self._client, ns, uuid)

    def create(
        self,
        payload: Any,
        namespace: str | None = None,
    ) -> T:
        """Create a resource."""
        if self._create_fn is None:
            raise NotImplementedError(
                "This resource does not support create."
            ) from None
        ns = self._ns(namespace)
        return self._create_fn(self._client, ns, payload)

    def update(
        self,
        id_or_resource: str | T,
        payload: Any | None = None,
        *,
        update_mask: str | None = None,
        namespace: str | None = None,
        **kwargs: Any,
    ) -> T:
        """Update by ID or resource object (anchors to resource namespace).

        When update_mask is provided: use it and payload (or resource as payload).
        When update_mask is omitted and kwargs are provided: delegate to
        resource.update(self, **kwargs) so mask is derived from kwargs.
        When both update_mask and kwargs are missing: raise TypeError.
        """
        if self._update_fn is None:
            raise NotImplementedError(
                "This resource does not support update."
            ) from None
        if update_mask is None and not kwargs:
            raise TypeError(
                "provide update_mask (e.g. 'meta.tags') or field kwargs "
                "(e.g. meta_tags=[...])."
            )
        if update_mask is None and kwargs:
            if not self._is_resource_like(id_or_resource):
                raise TypeError(
                    "when using field kwargs, id_or_resource must be a "
                    "resource instance (not a UUID string)."
                )
            res = cast("Any", id_or_resource)
            return res.update(self, **kwargs)
        if self._is_resource_like(id_or_resource):
            res = cast("Any", id_or_resource)
            uuid = res.uuid
            ns = (
                self._ns(namespace)
                if namespace is not None
                else self._ns(
                    resolve_namespace_for_resource(res, self._default_namespace)
                )
            )
            if payload is None:
                payload = res
        else:
            uuid = id_or_resource
            ns = self._ns(namespace)
            if payload is None:
                raise TypeError(
                    "payload is required when id_or_resource is a UUID string."
                )
        return self._update_fn(self._client, ns, uuid, payload, update_mask)

    def delete(
        self,
        name_or_resource: str | T,
        namespace: str | None = None,
        *,
        ignore_missing: bool = False,
    ) -> bool:
        """Delete by ID or resource object (anchors to resource namespace).

        When ignore_missing is True, return False instead of raising
        NotFoundError on 404.
        """
        if self._delete_fn is None:
            raise NotImplementedError(
                "This resource does not support delete."
            ) from None
        if self._is_resource_like(name_or_resource):
            res = cast("Any", name_or_resource)
            uuid = res.uuid
            ns = (
                self._ns(namespace)
                if namespace is not None
                else self._ns(
                    resolve_namespace_for_resource(res, self._default_namespace)
                )
            )
        else:
            uuid = name_or_resource
            ns = self._ns(namespace)
        try:
            return self._delete_fn(self._client, ns, uuid)
        except NotFoundError:
            if ignore_missing:
                return False
            raise

    def tag(
        self,
        id_or_resource: str | T,
        tags: list[str],
        namespace: str | None = None,
    ) -> T:
        """Set meta.tags on a resource (only when this resource supports tags)."""
        if (
            not self._tags_paths
            or "meta.tags" not in self._tags_paths
            or self._update_fn is None
        ):
            raise NotImplementedError("This resource does not support tag.") from None
        resource: T = (
            id_or_resource
            if self._is_resource_like(id_or_resource)
            else self.get(id_or_resource, namespace=namespace)
        )
        uuid: str = getattr(resource, "uuid")  # noqa: B009
        ns = (
            self._ns(namespace)
            if namespace is not None
            else self._ns(
                resolve_namespace_for_resource(resource, self._default_namespace)
            )
        )
        meta = getattr(resource, "meta", None)
        if meta is None:
            raise ValueError("Resource has no meta; cannot set meta.tags.") from None
        model_copy = getattr(resource, "model_copy")  # noqa: B009
        payload = model_copy(update={"meta": meta.model_copy(update={"tags": tags})})
        return self._update_fn(self._client, ns, uuid, payload, "meta.tags")

    def untag(
        self,
        id_or_resource: str | T,
        keys: list[str],
        namespace: str | None = None,
    ) -> T:
        """Remove the given tag values from meta.tags (only when supported)."""
        if (
            not self._tags_paths
            or "meta.tags" not in self._tags_paths
            or self._update_fn is None
        ):
            raise NotImplementedError("This resource does not support untag.") from None
        resource = (
            id_or_resource
            if self._is_resource_like(id_or_resource)
            else self.get(id_or_resource, namespace=namespace)
        )
        uuid = getattr(resource, "uuid")  # noqa: B009
        ns = (
            self._ns(namespace)
            if namespace is not None
            else self._ns(
                resolve_namespace_for_resource(resource, self._default_namespace)
            )
        )
        meta = getattr(resource, "meta", None)
        if meta is None:
            raise ValueError("Resource has no meta; cannot untag meta.tags.") from None
        current: list[str] = getattr(meta, "tags", None) or []
        new_tags: list[str] = [t for t in current if t not in keys]
        model_copy = getattr(resource, "model_copy")  # noqa: B009
        payload = model_copy(
            update={"meta": meta.model_copy(update={"tags": new_tags})}
        )
        return self._update_fn(self._client, ns, uuid, payload, "meta.tags")


class ScanLogsFacade:
    """Facade for retrieving scan logs (request-based API; not in registry).

    Use client.scan_logs.get_logs(scan_result_uuid) after obtaining a scan
    result UUID (e.g. from client.scan_result.list() or .get()).
    """

    def __init__(self, client: APIClient, default_namespace: str | None) -> None:
        super().__init__()
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
        See docs/reference/resources.md (scan_log_request) and
        docs/guides/retrieving-scan-results.md.
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
