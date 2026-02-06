"""Resource facade for the resource-oriented Client API.

Provides SystemResourceFacade[T] (list, list_iter, lookup; get only when
namespace is "oss") for system-owned resources, OssResourceFacade[T]
(namespace fixed to "oss") for oss-scoped resources, and ResourceFacade[T]
(full CRUD where supported) for tenant resources. Also provides ScanLogsFacade
for the request-based scan logs workflow; Client attaches it via
CUSTOM_FACADE_REGISTRY.
See docs/reference/resources.md (scan_log_request) and
docs/guides/retrieving-scan-results.md.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Generic, TypeGuard, TypeVar, cast, override

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


class _ListableFacade(Generic[T]):
    """Base facade: list, list_iter, lookup only. No get/create/update/delete."""

    def __init__(
        self,
        client: APIClient,
        default_namespace: str | None,
        list_fn: Callable[..., list[T]],
        list_iter_fn: Callable[..., Iterator[T]] | None = None,
        resource_name: str = "",
        parent_kind: str | None = None,
        tags_paths: list[str] | None = None,
    ) -> None:
        super().__init__()
        self._client = client
        self._default_namespace = default_namespace
        self._list_fn = list_fn
        self._list_iter_fn = list_iter_fn
        self._resource_name = resource_name
        self._parent_kind = parent_kind
        self._tags_paths = tags_paths or []

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
        """Merge list_params with kwargs; explicit kwargs override list_params."""
        list_param_keys = set(ListParameters.model_fields)
        merged: dict[str, Any] = {}
        if list_params is not None:
            merged = list_params.model_dump(exclude_none=True)
        if traverse:
            merged["traverse"] = True
        for k, v in kwargs.items():
            if k in list_param_keys:
                merged[k] = v
        if not merged:
            return None
        return ListParameters(**merged)

    def list(
        self,
        traverse: bool = False,
        namespace: str | None = None,
        list_params: ListParameters | None = None,
        max_pages: int | None = None,
        parent: Any = None,
        filter: str | None = None,
        mask: str | None = None,
        page_size: int | None = None,
        page_token: str | None = None,
        page_id: str | None = None,
        sort_by: str | None = None,
        desc: bool | None = None,
        count: bool | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
        archive: bool | None = None,
        pr_uuid: str | None = None,
        **kwargs: Any,
    ) -> list[T]:
        """List resources with pagination and filtering.

        Retrieves resources from the specified namespace with optional filtering,
        sorting, and recursive traversal of child namespaces. All list parameters
        map to ``list_parameters.*`` on the wire. Full pagination is always used
        (``list_all=True``).

        Args:
            traverse: When True, recursively queries all child namespaces in the
                hierarchy. Use for tenant-wide queries across all namespaces.
            namespace: Target namespace in canonical form (e.g.,
                ``'tenant.team.project'``). Defaults to the client's configured
                tenant namespace.
            list_params: Full ListParameters object for advanced options like
                grouping and aggregation. Explicit kwargs override values in
                list_params when both are provided.
            max_pages: Maximum number of pages to fetch. None fetches all
                available pages.
            parent: Parent resource object to scope the list by namespace and
                ``meta.parent_uuid``. Only supported when the resource has a
                registered ``parent_kind``.
            filter: Filter expression to select matching resources (e.g.,
                ``'spec.level==FINDING_LEVEL_CRITICAL'``). See API spec for
                supported operators and fields per resource.
            mask: Field mask for response projection (e.g.,
                ``'meta.name,spec.level'``). Limits which fields are returned
                in each resource.
            page_size: Number of results per page. Uses API default if omitted.
            page_token: Continuation token from a previous response's
                ``next_page_token`` for resuming pagination.
            page_id: Alternative pagination start point (aligns with endorctl
                ``--page-id`` flag).
            sort_by: Field path to sort results by (e.g., ``'meta.create_time'``).
            desc: Sort descending when True, ascending when False or omitted.
            count: When True, return count of matching resources instead of
                the resources themselves.
            from_date: Filter to resources created after this date (ISO 8601
                format, e.g., ``'2024-01-01T00:00:00Z'``).
            to_date: Filter to resources created before this date (ISO 8601
                format).
            archive: When True, fetch resources from the archive instead of
                active storage.
            pr_uuid: Scope to resources from a specific PR scan by its UUID.
            **kwargs: Resource-specific identity kwargs (e.g., ``name``,
                ``git_url``) that are translated to filter clauses automatically.

        Returns:
            List of resources matching the query. Empty list if no matches.

        Raises:
            ValueError: When namespace is required but not provided (and no
                client default is set), or when ``parent`` is passed but the
                resource does not support parent scoping.

        Example:
            List all critical findings across all namespaces::

                findings = client.finding.list(
                    traverse=True,
                    filter='spec.level==FINDING_LEVEL_CRITICAL'
                )

            List projects in a specific namespace with field projection::

                projects = client.project.list(
                    namespace='tenant.team',
                    mask='meta.name,spec.git'
                )

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
        # Merge explicit list params into kwargs so they override list_params
        explicit = {
            k: v
            for k, v in (
                ("filter", filter),
                ("mask", mask),
                ("page_size", page_size),
                ("page_token", page_token),
                ("page_id", page_id),
                ("sort_by", sort_by),
                ("desc", desc),
                ("count", count),
                ("from_date", from_date),
                ("to_date", to_date),
                ("archive", archive),
                ("pr_uuid", pr_uuid),
            )
            if v is not None
        }
        list_kwargs = {**kwargs, **explicit}
        resource_type = RESOURCE_NAME_TO_TYPE.get(self._resource_name, "")
        filter_map = get_list_filter_map(resource_type)
        merged_filter, remaining_kwargs = build_filter_from_identity_kwargs(
            filter_map, list_kwargs
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
        filter: str | None = None,
        mask: str | None = None,
        page_size: int | None = None,
        page_token: str | None = None,
        page_id: str | None = None,
        sort_by: str | None = None,
        desc: bool | None = None,
        count: bool | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
        archive: bool | None = None,
        pr_uuid: str | None = None,
        **kwargs: Any,
    ) -> T:
        """Look up a single resource matching the given criteria.

        Convenience method that calls ``list()`` with the provided parameters
        and returns the single matching resource. Use this when you expect
        exactly one result based on identity kwargs or filter criteria.

        Args:
            traverse: When True, recursively queries all child namespaces in the
                hierarchy. Use for tenant-wide queries across all namespaces.
            namespace: Target namespace in canonical form (e.g.,
                ``'tenant.team.project'``). Defaults to the client's configured
                tenant namespace.
            list_params: Full ListParameters object for advanced options like
                grouping and aggregation. Explicit kwargs override values in
                list_params when both are provided.
            max_pages: Maximum number of pages to search through. Defaults to 2
                to limit search scope for lookups.
            parent: Parent resource object to scope the lookup by namespace and
                ``meta.parent_uuid``. Only supported when the resource has a
                registered ``parent_kind``.
            filter: Filter expression to select matching resources (e.g.,
                ``'spec.level==FINDING_LEVEL_CRITICAL'``). See API spec for
                supported operators and fields per resource.
            mask: Field mask for response projection (e.g.,
                ``'meta.name,spec.level'``). Limits which fields are returned.
            page_size: Number of results per page. Uses API default if omitted.
            page_token: Continuation token from a previous response's
                ``next_page_token`` for resuming pagination.
            page_id: Alternative pagination start point (aligns with endorctl
                ``--page-id`` flag).
            sort_by: Field path to sort results by (e.g., ``'meta.create_time'``).
            desc: Sort descending when True, ascending when False or omitted.
            count: When True, return count instead of objects (rarely useful
                for lookup).
            from_date: Filter to resources created after this date (ISO 8601
                format, e.g., ``'2024-01-01T00:00:00Z'``).
            to_date: Filter to resources created before this date (ISO 8601
                format).
            archive: When True, fetch resources from the archive instead of
                active storage.
            pr_uuid: Scope to resources from a specific PR scan by its UUID.
            **kwargs: Resource-specific identity kwargs (e.g., ``name``,
                ``git_url``) that are translated to filter clauses automatically.

        Returns:
            The single resource matching the query.

        Raises:
            NotFoundError: When no resource matches the given criteria.
            AmbiguousError: When multiple resources match; narrow the query
                with more specific criteria.
            ValueError: When namespace is required but not provided (and no
                client default is set).

        Example:
            Look up a project by name::

                project = client.project.lookup(
                    namespace='tenant.team',
                    name='my-project'
                )

            Look up with traverse when namespace is unknown::

                project = client.project.lookup(
                    traverse=True,
                    name='my-project'
                )

        """
        items = self.list(
            traverse=traverse,
            namespace=namespace,
            list_params=list_params,
            max_pages=max_pages,
            parent=parent,
            filter=filter,
            mask=mask,
            page_size=page_size,
            page_token=page_token,
            page_id=page_id,
            sort_by=sort_by,
            desc=desc,
            count=count,
            from_date=from_date,
            to_date=to_date,
            archive=archive,
            pr_uuid=pr_uuid,
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
        filter: str | None = None,
        mask: str | None = None,
        page_size: int | None = None,
        page_token: str | None = None,
        page_id: str | None = None,
        sort_by: str | None = None,
        desc: bool | None = None,
        count: bool | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
        archive: bool | None = None,
        pr_uuid: str | None = None,
        **kwargs: Any,
    ) -> Iterator[T]:
        """Iterate over resources without materializing the full list in memory.

        Returns an iterator that yields resources one at a time, fetching pages
        on demand. Use this for memory-efficient processing of large result sets.

        Args:
            traverse: When True, recursively queries all child namespaces in the
                hierarchy. Use for tenant-wide queries across all namespaces.
            namespace: Target namespace in canonical form (e.g.,
                ``'tenant.team.project'``). Defaults to the client's configured
                tenant namespace.
            list_params: Full ListParameters object for advanced options like
                grouping and aggregation. Explicit kwargs override values in
                list_params when both are provided.
            max_pages: Maximum number of pages to fetch. None fetches all
                available pages.
            parent: Parent resource object to scope the iteration by namespace
                and ``meta.parent_uuid``. Only supported when the resource has a
                registered ``parent_kind``.
            filter: Filter expression to select matching resources (e.g.,
                ``'spec.level==FINDING_LEVEL_CRITICAL'``). See API spec for
                supported operators and fields per resource.
            mask: Field mask for response projection (e.g.,
                ``'meta.name,spec.level'``). Limits which fields are returned
                in each resource.
            page_size: Number of results per page. Uses API default if omitted.
            page_token: Continuation token from a previous response's
                ``next_page_token`` for resuming pagination.
            page_id: Alternative pagination start point (aligns with endorctl
                ``--page-id`` flag).
            sort_by: Field path to sort results by (e.g., ``'meta.create_time'``).
            desc: Sort descending when True, ascending when False or omitted.
            count: When True, return count instead of objects (rarely useful
                for iteration).
            from_date: Filter to resources created after this date (ISO 8601
                format, e.g., ``'2024-01-01T00:00:00Z'``).
            to_date: Filter to resources created before this date (ISO 8601
                format).
            archive: When True, fetch resources from the archive instead of
                active storage.
            pr_uuid: Scope to resources from a specific PR scan by its UUID.
            **kwargs: Resource-specific identity kwargs (e.g., ``name``,
                ``git_url``) that are translated to filter clauses automatically.

        Yields:
            Resources matching the query, one at a time.

        Raises:
            NotImplementedError: When the resource does not support iteration.
            ValueError: When namespace is required but not provided (and no
                client default is set), or when ``parent`` is passed but the
                resource does not support parent scoping.

        Example:
            Process all findings without loading them all into memory::

                for finding in client.finding.list_iter(traverse=True):
                    process(finding)

            Iterate with filtering and early exit::

                for project in client.project.list_iter(
                    namespace='tenant.team',
                    filter='meta.tags contains "reviewed"'
                ):
                    if should_stop(project):
                        break
                    handle(project)

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
        explicit = {
            k: v
            for k, v in (
                ("filter", filter),
                ("mask", mask),
                ("page_size", page_size),
                ("page_token", page_token),
                ("page_id", page_id),
                ("sort_by", sort_by),
                ("desc", desc),
                ("count", count),
                ("from_date", from_date),
                ("to_date", to_date),
                ("archive", archive),
                ("pr_uuid", pr_uuid),
            )
            if v is not None
        }
        list_kwargs = {**kwargs, **explicit}
        if parent is not None:
            parent_uuid = getattr(parent, "uuid", "")
            parent_filter = f'meta.parent_uuid=="{parent_uuid}"'
            existing = list_kwargs.get("filter")
            list_kwargs["filter"] = (
                f"{existing} AND {parent_filter}" if existing else parent_filter
            )
        lp = self._list_params(list_params, traverse=traverse, **list_kwargs)
        return self._list_iter_fn(self._client, ns, lp, max_pages)


class SystemResourceFacade(_ListableFacade[T]):
    """System-owned: list, list_iter, lookup; get only when namespace is "oss".

    For non-oss namespace (e.g. system or tenant), get() raises NotImplementedError;
    use list() instead. When namespace is "oss", get(id, namespace="oss") delegates.
    """

    def __init__(
        self,
        client: APIClient,
        default_namespace: str | None,
        list_fn: Callable[..., list[T]],
        list_iter_fn: Callable[..., Iterator[T]] | None = None,
        get_fn: Callable[..., T] | None = None,
        resource_name: str = "",
        parent_kind: str | None = None,
        tags_paths: list[str] | None = None,
    ) -> None:
        super().__init__(
            client,
            default_namespace,
            list_fn,
            list_iter_fn=list_iter_fn,
            resource_name=resource_name,
            parent_kind=parent_kind,
            tags_paths=tags_paths or [],
        )
        self._get_fn = get_fn

    def get(self, id_or_resource: str | T, namespace: str | None = None) -> T:
        """Get a system-owned resource by ID; only supported for oss namespace.

        Retrieves a single resource by its UUID. For system-owned resources,
        this is only supported when the namespace is ``"oss"``. For other
        namespaces (system or tenant), use ``list()`` with a filter instead.

        Args:
            id_or_resource: Either a UUID string or a resource object. When a
                resource object is passed, the UUID is extracted from it and
                the namespace is derived from the resource's ``tenant_meta``.
            namespace: Target namespace. Must be ``"oss"`` for system-owned
                resources. When omitted and a resource object is passed, the
                namespace is derived from the resource.

        Returns:
            The resource matching the given ID.

        Raises:
            NotImplementedError: When the resource does not support get, or
                when the namespace is not ``"oss"``. Use ``list()`` for
                system/tenant namespaces.
            ValueError: When namespace is required but not provided.

        Example:
            Get a package version from the oss namespace::

                pkg = client.package_version.get(
                    '550e8400-e29b-41d4-a716-446655440000',
                    namespace='oss'
                )

        """
        if self._get_fn is None:
            raise NotImplementedError(
                "This resource does not support get; use list() for system/tenant."
            ) from None
        if hasattr(id_or_resource, "uuid") and hasattr(id_or_resource, "tenant_meta"):
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
        if ns != "oss":
            raise NotImplementedError(
                "GET only supported for oss namespace; use list() for system/tenant."
            ) from None
        return self._get_fn(self._client, "oss", uuid)


class ResourceFacade(_ListableFacade[T]):
    """Facade for resources with get/create/update/delete where supported.

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
        build_create_payload_fn: Callable[..., Any] | None = None,
    ) -> None:
        super().__init__(
            client,
            default_namespace,
            list_fn,
            list_iter_fn=list_iter_fn,
            resource_name=resource_name,
            parent_kind=parent_kind,
            tags_paths=tags_paths,
        )
        self._get_fn = get_fn
        self._create_fn = create_fn
        self._update_fn = update_fn
        self._delete_fn = delete_fn
        self._build_create_payload_fn = build_create_payload_fn

    def _is_resource_like(self, value: Any) -> TypeGuard[T]:
        """Return True if value has uuid and tenant_meta (resource object)."""
        return (
            hasattr(value, "uuid")
            and hasattr(value, "tenant_meta")
            and value is not None
        )

    def get(self, id_or_resource: str | T, namespace: str | None = None) -> T:
        """Get a resource by ID or resource object.

        Retrieves a single resource by its UUID. When a resource object is
        passed, the operation is anchored to that resource's namespace,
        ensuring the correct context for the API call.

        Args:
            id_or_resource: Either a UUID string or a resource object. When a
                resource object is passed, the UUID is extracted from it and
                the namespace is derived from the resource's ``tenant_meta``
                (unless explicitly overridden).
            namespace: Target namespace in canonical form (e.g.,
                ``'tenant.team.project'``). When omitted and a resource object
                is passed, the namespace is derived from the resource.
                Defaults to the client's configured tenant namespace.

        Returns:
            The resource matching the given ID.

        Raises:
            ValueError: When namespace is required but not provided (and no
                client default is set).

        Example:
            Get a project by UUID::

                project = client.project.get(
                    '550e8400-e29b-41d4-a716-446655440000',
                    namespace='tenant.team'
                )

            Refresh a resource (re-fetch with latest data)::

                updated_project = client.project.get(project)

        """
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
        payload: Any = None,
        *,
        name: str | None = None,
        description: str | None = None,
        namespace_uuid: str | None = None,
        namespace: str | None = None,
        **kwargs: Any,
    ) -> T:
        """Create a new resource.

        Supports two creation patterns: payload-based (explicit ``CreateXPayload``
        object) or kwargs-based (when the resource has a ``build_create_payload``
        function). Use kwargs for a simpler API; use payload for full control
        or backward compatibility.

        Args:
            payload: A ``CreateXPayload`` object (e.g., ``CreateProjectPayload``,
                ``CreateNamespacePayload``) containing all required fields for
                creation. Mutually exclusive with kwargs.
            name: Resource name (convenience param merged into kwargs). The
                exact semantics depend on the resource type.
            description: Resource description (convenience param merged into
                kwargs). Typically stored in ``meta.description``.
            namespace_uuid: UUID of the parent namespace (convenience param
                merged into kwargs). Required for some resource types.
            namespace: Target namespace in canonical form (e.g.,
                ``'tenant.team.project'``) where the resource will be created.
                Defaults to the client's configured tenant namespace.
            **kwargs: Resource-specific creation kwargs passed to the resource's
                ``build_create_payload`` function. The allowed set is defined
                by each resource's builder. Mutually exclusive with payload.

        Returns:
            The newly created resource with server-assigned fields (e.g., UUID,
            timestamps) populated.

        Raises:
            NotImplementedError: When the resource does not support create.
            TypeError: When both ``payload`` and kwargs are provided, when
                neither is provided, or when kwargs are provided but the
                resource does not have a ``build_create_payload`` function.
            ValueError: When namespace is required but not provided.

        Example:
            Create a namespace using kwargs (simpler)::

                ns = client.namespace.create(
                    name='my-namespace',
                    namespace='tenant'
                )

            Create a project using payload (full control)::

                from endorlabs.resources.project import CreateProjectPayload

                project = client.project.create(
                    payload=CreateProjectPayload(
                        meta=ProjectMetaCreate(name='my-project'),
                        namespace_uuid='...'
                    ),
                    namespace='tenant.team'
                )

        """
        if self._create_fn is None:
            raise NotImplementedError(
                "This resource does not support create."
            ) from None
        # Merge explicit optional params into kwargs (explicit wins when not None)
        explicit = {
            k: v
            for k, v in (
                ("name", name),
                ("description", description),
                ("namespace_uuid", namespace_uuid),
            )
            if v is not None
        }
        merged = {**kwargs, **explicit}
        if payload is not None and merged:
            raise TypeError("provide either payload= or kwargs for create(), not both.")
        if payload is None and not merged:
            raise TypeError("create() requires payload= or resource-specific kwargs.")
        if payload is None and merged and self._build_create_payload_fn is not None:
            # namespace is consumed by _ns(); do not pass to builder
            create_kwargs = {k: v for k, v in merged.items() if k != "namespace"}
            payload = self._build_create_payload_fn(**create_kwargs)
        elif payload is None and merged and self._build_create_payload_fn is None:
            raise TypeError(
                "create() for this resource requires payload=; kwargs not supported."
            )
        ns = self._ns(namespace)
        return self._create_fn(self._client, ns, payload)

    def update(
        self,
        id_or_resource: str | T,
        payload: Any | None = None,
        *,
        update_mask: str | None = None,
        meta_description: str | None = None,
        meta_tags: list[str] | None = None,
        namespace: str | None = None,
        **kwargs: Any,
    ) -> T:
        """Update a resource using sparse PATCH semantics.

        Supports two update patterns: mask-based (explicit ``update_mask`` with
        payload) or kwargs-based (field kwargs that derive the mask automatically).
        The kwargs pattern is simpler for common updates; the mask pattern gives
        full control.

        Args:
            id_or_resource: Either a UUID string or a resource object. When a
                resource object is passed, the operation is anchored to that
                resource's namespace and the resource itself can serve as the
                payload. For kwargs-based updates, this **must** be a resource
                instance (not a UUID string).
            payload: The resource object containing updated field values. When
                omitted and ``id_or_resource`` is a resource object, that
                resource is used as the payload. Required when ``id_or_resource``
                is a UUID string.
            update_mask: Comma-separated field paths to update (e.g.,
                ``'meta.tags'``, ``'meta.description,spec.scan_state'``). When
                provided, only these fields are patched. When omitted, the mask
                is derived from the provided kwargs.
            meta_description: Updated description (convenience param). Merged
                into kwargs as ``meta_description``. Triggers update of
                ``meta.description``.
            meta_tags: Updated tags list (convenience param). Merged into kwargs
                as ``meta_tags``. Triggers update of ``meta.tags``.
            namespace: Target namespace in canonical form. When omitted and a
                resource object is passed, the namespace is derived from the
                resource's ``tenant_meta``.
            **kwargs: Resource-specific mutable field kwargs. The allowed set is
                defined by the resource's ``get_mutable_fields()``. When provided
                without ``update_mask``, the mask is derived automatically.

        Returns:
            The updated resource with server-applied changes.

        Raises:
            NotImplementedError: When the resource does not support update.
            TypeError: When neither ``update_mask`` nor kwargs are provided,
                when kwargs are provided but ``id_or_resource`` is a UUID string
                (not a resource instance), or when payload is required but
                not provided.
            ValueError: When namespace is required but not provided, or when
                an immutable field is included in the update_mask.

        Example:
            Update using kwargs (simpler, mask derived automatically)::

                updated = client.project.update(
                    project,
                    meta_description='New description',
                    meta_tags=['reviewed', 'production']
                )

            Update using explicit mask (full control)::

                project.meta.description = 'Updated description'
                updated = client.project.update(
                    project,
                    update_mask='meta.description'
                )

            Fluent update via resource method::

                updated = project.update(
                    client.project,
                    meta_tags=['new-tag']
                )

        """
        if self._update_fn is None:
            raise NotImplementedError(
                "This resource does not support update."
            ) from None
        # Merge explicit optional params into kwargs (explicit wins when not None)
        merged_kwargs = dict(kwargs)
        if meta_description is not None:
            merged_kwargs["meta_description"] = meta_description
        if meta_tags is not None:
            merged_kwargs["meta_tags"] = meta_tags
        if update_mask is None and not merged_kwargs:
            raise TypeError(
                "provide update_mask (e.g. 'meta.tags') or field kwargs "
                "(e.g. meta_tags=[...])."
            )
        if update_mask is None and merged_kwargs:
            if not self._is_resource_like(id_or_resource):
                raise TypeError(
                    "when using field kwargs, id_or_resource must be a "
                    "resource instance (not a UUID string)."
                )
            res = cast("Any", id_or_resource)
            return res.update(self, **merged_kwargs)
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
        """Delete a resource by ID or resource object.

        Removes the specified resource from the system. When a resource object
        is passed, the operation is anchored to that resource's namespace,
        ensuring the correct context for the API call.

        Args:
            name_or_resource: Either a UUID string or a resource object. When a
                resource object is passed, the UUID is extracted from it and
                the namespace is derived from the resource's ``tenant_meta``
                (unless explicitly overridden).
            namespace: Target namespace in canonical form (e.g.,
                ``'tenant.team.project'``). When omitted and a resource object
                is passed, the namespace is derived from the resource.
                Defaults to the client's configured tenant namespace.
            ignore_missing: When True, return False instead of raising
                ``NotFoundError`` if the resource does not exist (idempotent
                delete). When False (default), raise ``NotFoundError`` on 404.

        Returns:
            True if the resource was deleted successfully. False if
            ``ignore_missing=True`` and the resource was not found.

        Raises:
            NotImplementedError: When the resource does not support delete.
            NotFoundError: When the resource is not found and
                ``ignore_missing=False``.
            ValueError: When namespace is required but not provided.

        Example:
            Delete a project by resource object::

                client.project.delete(project)

            Delete by UUID with idempotent behavior::

                deleted = client.project.delete(
                    '550e8400-e29b-41d4-a716-446655440000',
                    namespace='tenant.team',
                    ignore_missing=True
                )
                if not deleted:
                    print('Project was already deleted')

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
        """Set the tags on a resource, replacing any existing tags.

        Updates ``meta.tags`` on the resource to the provided list. This is a
        convenience method that wraps ``update()`` with ``update_mask='meta.tags'``.
        Only available for resources that support tagging (have ``meta.tags``
        in their mutable fields).

        Args:
            id_or_resource: Either a UUID string or a resource object. When a
                UUID string is passed, the resource is fetched first to ensure
                the correct payload structure. When a resource object is passed,
                the namespace is derived from the resource's ``tenant_meta``.
            tags: List of tag strings to set on the resource. Replaces any
                existing tags. Use an empty list to clear all tags.
            namespace: Target namespace in canonical form (e.g.,
                ``'tenant.team.project'``). When omitted and a resource object
                is passed, the namespace is derived from the resource.

        Returns:
            The updated resource with the new tags applied.

        Raises:
            NotImplementedError: When the resource does not support tagging.
            ValueError: When namespace is required but not provided, or when
                the resource has no ``meta`` attribute.

        Example:
            Set tags on a project::

                updated = client.project.tag(
                    project,
                    tags=['reviewed', 'production', 'team-a']
                )

            Clear all tags::

                updated = client.project.tag(project, tags=[])

        """
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
        """Remove specific tags from a resource.

        Removes the specified tag values from ``meta.tags``, preserving any
        other existing tags. This is a convenience method that fetches the
        current tags, filters out the specified values, and calls ``update()``
        with ``update_mask='meta.tags'``.

        Args:
            id_or_resource: Either a UUID string or a resource object. When a
                UUID string is passed, the resource is fetched first to get
                the current tags. When a resource object is passed, the
                namespace is derived from the resource's ``tenant_meta``.
            keys: List of tag values to remove. Tags not present in this list
                are preserved. Values not currently in the resource's tags
                are silently ignored.
            namespace: Target namespace in canonical form (e.g.,
                ``'tenant.team.project'``). When omitted and a resource object
                is passed, the namespace is derived from the resource.

        Returns:
            The updated resource with the specified tags removed.

        Raises:
            NotImplementedError: When the resource does not support tagging.
            ValueError: When namespace is required but not provided, or when
                the resource has no ``meta`` attribute.

        Example:
            Remove specific tags from a project::

                # Before: tags=['reviewed', 'production', 'deprecated']
                updated = client.project.untag(
                    project,
                    keys=['deprecated', 'obsolete']  # 'obsolete' ignored
                )
                # After: tags=['reviewed', 'production']

        """
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


class OssResourceFacade(ResourceFacade[T]):
    """Oss-scoped: namespace fixed to "oss"; caller does not pass namespace."""

    @override
    def _ns(self, namespace: str | None) -> str:
        return "oss"


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

        Fetches log entries from a completed scan using the ScanLogRequest API.
        Use this to inspect scan execution details, debug failures, or audit
        scan behavior.

        Args:
            scan_result_uuid: UUID of the scan result to retrieve logs for.
                Obtain this from ``client.scan_result.list()`` or
                ``client.scan_result.get()``.
            namespace: Target namespace in canonical form (e.g.,
                ``'tenant.team.project'``). Defaults to the client's configured
                tenant namespace.
            max_entries: Maximum number of log entries to return. Defaults to
                100. Increase for more comprehensive logs or decrease for
                faster responses.
            log_levels: Filter to specific log levels. When None, returns all
                levels. Use ``ScanLogLevel`` enum values (e.g.,
                ``[ScanLogLevel.ERROR, ScanLogLevel.WARNING]``).
            start_time: Filter to logs after this timestamp (ISO 8601 format,
                e.g., ``'2024-01-01T00:00:00Z'``). Useful for narrowing to a
                specific time window.
            end_time: Filter to logs before this timestamp (ISO 8601 format).
                Combine with ``start_time`` to define a time range.
            newest_first: When True, return logs in reverse chronological order
                (newest first). When False or None, logs are returned in
                chronological order.

        Returns:
            List of log message objects containing timestamp, level, message,
            and other metadata. Empty list if no logs match the criteria.

        Raises:
            ValueError: When namespace is required but not provided.

        Example:
            Get all logs for a scan result::

                logs = client.scan_logs.get_logs(
                    scan_result_uuid='550e8400-e29b-41d4-a716-446655440000',
                    namespace='tenant.team'
                )
                for log in logs:
                    print(f'{log.timestamp}: [{log.level}] {log.message}')

            Get only error logs, newest first::

                from endorlabs.resources.scan_log_request import ScanLogLevel

                errors = client.scan_logs.get_logs(
                    scan_result_uuid='...',
                    log_levels=[ScanLogLevel.ERROR],
                    newest_first=True,
                    max_entries=50
                )

        See Also:
            - ``docs/reference/resources.md`` (scan_log_request section)
            - ``docs/guides/retrieving-scan-results.md``

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
