"""Resource facade for the resource-oriented Client API.

Provides ``ResourceFacade[T]`` — a single facade class that handles all
resource scopes (tenant, system, oss) via the ``scope`` parameter — and
``ScanLogsFacade`` for the request-based scan logs workflow.

``scope`` controls namespace resolution:

* ``None`` (default) — tenant-scoped; namespace from client default or arg.
* ``"system"`` — system-owned; ``get()`` restricted to ``namespace="oss"``.
* ``"oss"`` — OSS-scoped; namespace is always ``"oss"``.

Backward-compatible aliases ``SystemResourceFacade`` and ``OssResourceFacade``
are provided for external consumers.

See docs/reference/resources.md and docs/guides/retrieving-scan-results.md.
"""

from __future__ import annotations

from typing import (
    TYPE_CHECKING,
    Any,
    Generic,
    Literal,
    TypeGuard,
    TypeVar,
    cast,
    override,
)

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
    """Base facade: list, list_iter, lookup only. No get/create/update/delete.

    Shared parameter vocabulary (list, lookup, list_iter):
    traverse, concurrent, max_workers, namespace, list_params, max_pages, parent,
    filter, mask, page_size, page_token, page_id, sort_by, desc, count,
    from_date, to_date, archive, pr_uuid, **kwargs (identity → filter).
    See method docstrings for signatures; semantics: traverse=tenant-wide,
    concurrent=parallel namespaces when traverse=True, namespace=canonical path,
    list_params=ListParameters (kwargs override), max_pages=None=all,
    parent=scope by meta.parent_uuid, filter/mask=API expressions,
    page_*=pagination, sort_by/desc=ordering, count=return count only,
    from_date/to_date=ISO 8601, archive=from archive, pr_uuid=PR scan scope.
    """

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

    def _build_list_kwargs(
        self,
        *,
        parent: Any,
        filter: str | None,
        mask: str | None,
        page_size: int | None,
        page_token: str | None,
        page_id: str | None,
        sort_by: str | None,
        desc: bool | None,
        count: bool | None,
        from_date: str | None,
        to_date: str | None,
        archive: bool | None,
        pr_uuid: str | None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Build merged kwargs dict from explicit params, identity kwargs, and parent.

        Shared by ``list()`` and ``list_iter()`` to guarantee identical
        filter/mask/parent behaviour.
        """
        from .models.base import RESOURCE_NAME_TO_TYPE

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

        return remaining_kwargs

    def list(
        self,
        traverse: bool = False,
        concurrent: bool = False,
        max_workers: int = 10,
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
        """List resources with full pagination and optional concurrent mode.

        Uses full pagination (list_all=True). With traverse=True and
        concurrent=True, queries each namespace in parallel. Parameter details
        are in the class docstring (traverse, concurrent, max_workers,
        namespace, list_params, max_pages, parent, filter, mask, page_*, sort_by,
        desc, count, from_date, to_date, archive, pr_uuid, **kwargs).

        Args:
            traverse: See class docstring.
            concurrent: See class docstring.
            max_workers: See class docstring.
            namespace: See class docstring.
            list_params: See class docstring.
            max_pages: See class docstring.
            parent: See class docstring.
            filter: See class docstring.
            mask: See class docstring.
            page_size: See class docstring.
            page_token: See class docstring.
            page_id: See class docstring.
            sort_by: See class docstring.
            desc: See class docstring.
            count: See class docstring.
            from_date: See class docstring.
            to_date: See class docstring.
            archive: See class docstring.
            pr_uuid: See class docstring.
            **kwargs: See class docstring.

        Returns:
            List of resources; empty if no matches.

        Raises:
            ValueError: Missing namespace, unsupported parent, or concurrent
                without traverse.

        Example:
            List critical findings tenant-wide::

                findings = client.finding.list(
                    traverse=True,
                    filter='spec.level==FINDING_LEVEL_CRITICAL'
                )

        """
        # Validate concurrent usage
        if concurrent and not traverse:
            raise ValueError(
                "concurrent=True requires traverse=True. "
                "Concurrent mode queries each namespace in parallel."
            )

        if parent is not None:
            if self._parent_kind is None:
                raise ValueError(
                    "This resource does not support list(parent=)."
                ) from None
            namespace = self._ns(
                resolve_namespace_for_resource(parent, self._default_namespace)
            )
        ns = self._ns(namespace)

        # Handle concurrent mode: query namespaces in parallel
        if concurrent and traverse:
            return self._list_concurrent(
                namespace=ns,
                max_workers=max_workers,
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

        # Standard single-query mode
        remaining_kwargs = self._build_list_kwargs(
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
        lp = self._list_params(list_params, traverse=traverse, **remaining_kwargs)
        return self._list_fn(self._client, ns, lp, max_pages)

    def _list_concurrent(
        self,
        namespace: str,
        max_workers: int,
        list_params: ListParameters | None,
        max_pages: int | None,
        parent: Any,
        **kwargs: Any,
    ) -> list[T]:
        """Fetch namespaces with traverse, then query each in parallel; merge."""
        from .resources.namespace import list_namespaces
        from .utils.parallel import execute_across_namespaces

        # Phase 1: Get all namespaces
        all_namespaces = list_namespaces(
            self._client,
            namespace,
            ListParameters(traverse=True),  # pyright: ignore[reportCallIssue]
        )

        # Extract namespace names (spec.full_name is the canonical name)
        namespace_names: list[str] = []
        for ns_obj in all_namespaces:
            if ns_obj.spec and ns_obj.spec.full_name:
                namespace_names.append(ns_obj.spec.full_name)
            elif ns_obj.tenant_meta and ns_obj.tenant_meta.namespace:
                # Fallback to tenant_meta.namespace + meta.name
                parent_ns = ns_obj.tenant_meta.namespace
                if ns_obj.meta and ns_obj.meta.name:
                    namespace_names.append(f"{parent_ns}.{ns_obj.meta.name}")
                else:
                    namespace_names.append(parent_ns)

        # Also include the root namespace itself
        if namespace not in namespace_names:
            namespace_names.insert(0, namespace)

        # Phase 2: Build query function for each namespace
        def query_namespace(ns: str) -> list[T]:
            # Query without traverse - each namespace independently
            return self.list(
                traverse=False,
                concurrent=False,
                namespace=ns,
                list_params=list_params,
                max_pages=max_pages,
                parent=parent,
                **kwargs,
            )

        # Phase 3: Execute concurrently and merge
        return execute_across_namespaces(
            namespaces=namespace_names,
            query_fn=query_namespace,
            max_workers=max_workers,
        )

    def lookup(
        self,
        traverse: bool = False,
        concurrent: bool = False,
        max_workers: int = 10,
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
        """Return the single resource matching criteria; calls list() under the hood.

        Parameters match list(); see class docstring. max_pages defaults to 2
        to limit search scope.

        Args:
            traverse: See class docstring.
            concurrent: See class docstring.
            max_workers: See class docstring.
            namespace: See class docstring.
            list_params: See class docstring.
            max_pages: Max pages to search (default 2).
            parent: See class docstring.
            filter: See class docstring.
            mask: See class docstring.
            page_size: See class docstring.
            page_token: See class docstring.
            page_id: See class docstring.
            sort_by: See class docstring.
            desc: See class docstring.
            count: See class docstring.
            from_date: See class docstring.
            to_date: See class docstring.
            archive: See class docstring.
            pr_uuid: See class docstring.
            **kwargs: See class docstring.

        Returns:
            The single matching resource.

        Raises:
            NotFoundError: No resource matches.
            AmbiguousError: Multiple match; narrow criteria.
            ValueError: Missing namespace or concurrent without traverse.

        Example:
            project = client.project.lookup(namespace='tenant.team', name='my-project')

        """
        items = self.list(
            traverse=traverse,
            concurrent=concurrent,
            max_workers=max_workers,
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
        concurrent: bool = False,
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
        """Yield resources one at a time; no concurrent support; memory-efficient.

        Parameters match list() (see class docstring). concurrent is not
        supported; use list(concurrent=True) for parallel namespace queries.

        Args:
            traverse: See class docstring.
            concurrent: Not supported; use list() for concurrent.
            namespace: See class docstring.
            list_params: See class docstring.
            max_pages: See class docstring.
            parent: See class docstring.
            filter: See class docstring.
            mask: See class docstring.
            page_size: See class docstring.
            page_token: See class docstring.
            page_id: See class docstring.
            sort_by: See class docstring.
            desc: See class docstring.
            count: See class docstring.
            from_date: See class docstring.
            to_date: See class docstring.
            archive: See class docstring.
            pr_uuid: See class docstring.
            **kwargs: See class docstring.

        Yields:
            Resources one at a time.

        Raises:
            NotImplementedError: Resource has no list_iter or concurrent=True.
            ValueError: Missing namespace or unsupported parent.

        Example:
            for finding in client.finding.list_iter(traverse=True):
                process(finding)

        """
        if concurrent:
            raise NotImplementedError(
                "concurrent=True is not supported for list_iter. "
                "Use list(concurrent=True, traverse=True) instead."
            ) from None
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
        remaining_kwargs = self._build_list_kwargs(
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
        lp = self._list_params(list_params, traverse=traverse, **remaining_kwargs)
        return self._list_iter_fn(self._client, ns, lp, max_pages)


class ResourceFacade(_ListableFacade[T]):
    """Facade for resources with get/create/update/delete where supported.

    id_or_resource / name_or_resource: Methods accept either a UUID string or a
    resource object. When a resource object is passed, UUID is taken from it and
    namespace is derived from the resource's tenant_meta unless overridden by
    the namespace= argument.

    Namespace resolution: From client default or explicit namespace=; for
    list/get/create/update/delete, explicit namespace= overrides resource-derived
    namespace when both could apply.

    Scope (set at facade construction):
        * ``None`` — tenant-scoped; namespace from client default or argument.
        * ``"system"`` — system-owned; get() only when namespace="oss".
        * ``"oss"`` — OSS-scoped; namespace always "oss".
    """

    def __init__(
        self,
        client: APIClient,
        default_namespace: str | None,
        list_fn: Callable[..., list[T]],
        get_fn: Callable[..., T] | None = None,
        create_fn: Callable[..., T] | None = None,
        update_fn: Callable[..., T] | None = None,
        delete_fn: Callable[..., bool] | None = None,
        list_iter_fn: Callable[..., Iterator[T]] | None = None,
        tags_paths: list[str] | None = None,
        resource_name: str = "",
        parent_kind: str | None = None,
        build_create_payload_fn: Callable[..., Any] | None = None,
        scope: Literal["system", "oss"] | None = None,
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
        self._scope: Literal["system", "oss"] | None = scope

    @property
    def scope(self) -> Literal["system", "oss"] | None:
        """The resource scope: ``"system"``, ``"oss"``, or ``None`` (tenant)."""
        return self._scope

    @override
    def _ns(self, namespace: str | None) -> str:
        if self._scope == "oss":
            return "oss"
        return super()._ns(namespace)

    def _is_resource_like(self, value: Any) -> TypeGuard[T]:
        """Return True if value has uuid and tenant_meta (resource object)."""
        return (
            hasattr(value, "uuid")
            and hasattr(value, "tenant_meta")
            and value is not None
        )

    def get(self, id_or_resource: str | T, namespace: str | None = None) -> T:
        """Fetch a single resource by UUID or resource object.

        id_or_resource and namespace follow class docstring (resource object
        supplies namespace when namespace= omitted). System scope: get() only
        when resolved namespace is "oss".

        Args:
            id_or_resource: UUID or resource object. See class docstring.
            namespace: Target namespace. See class docstring.

        Returns:
            The resource.

        Raises:
            NotImplementedError: No get support, or system scope and ns != "oss".
            ValueError: Namespace required but not set.

        Example:
            project = client.project.get('uuid-here', namespace='tenant.team')
            updated = client.project.get(project)

        """
        if self._get_fn is None:
            raise NotImplementedError(
                "This resource does not support get; use list() for system/tenant."
            ) from None
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
        if self._scope == "system" and ns != "oss":
            raise NotImplementedError(
                "GET only supported for oss namespace; use list() for system/tenant."
            ) from None
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
        """Create a resource via payload= or kwargs (build_create_payload).

        Either pass a CreateXPayload in payload= or resource-specific kwargs;
        mutually exclusive. namespace follows class docstring.

        Args:
            payload: CreateXPayload; mutually exclusive with kwargs.
            name: Convenience; merged into kwargs.
            description: Convenience; merged into kwargs.
            namespace_uuid: Convenience; merged into kwargs.
            namespace: Where to create. See class docstring.
            **kwargs: Resource-specific; passed to build_create_payload.

        Returns:
            Created resource with server-assigned fields.

        Raises:
            NotImplementedError: Resource has no create.
            TypeError: Both payload and kwargs, or neither, or kwargs without builder.
            ValueError: Namespace required but not set.

        Example:
            ns = client.namespace.create(name='my-namespace', namespace='tenant')

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
        """Update a resource: update_mask + payload, or field kwargs (mask derived).

        id_or_resource and namespace follow class docstring. For kwargs-based
        updates, id_or_resource must be a resource instance; payload can be
        omitted (resource used as payload).

        Args:
            id_or_resource: UUID or resource object. See class docstring.
            payload: Updated fields; optional when id_or_resource is resource.
            update_mask: Comma-separated paths (e.g. 'meta.tags').
            meta_description: Convenience; updates meta.description.
            meta_tags: Convenience; updates meta.tags.
            namespace: See class docstring.
            **kwargs: Mutable field kwargs; mask derived if update_mask omitted.

        Returns:
            Updated resource.

        Raises:
            NotImplementedError: No update support.
            TypeError: No mask nor kwargs; or kwargs with UUID id_or_resource.
            ValueError: Missing namespace or immutable in update_mask.

        Example:
            updated = client.project.update(project, meta_tags=['reviewed'])

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
        """Remove a resource by UUID or resource object.

        name_or_resource and namespace follow class docstring.

        Args:
            name_or_resource: UUID or resource object. See class docstring.
            namespace: See class docstring.
            ignore_missing: If True, return False on 404 instead of raising.

        Returns:
            True if deleted; False if ignore_missing and not found.

        Raises:
            NotImplementedError: No delete support.
            NotFoundError: Not found and not ignore_missing.
            ValueError: Namespace required but not set.

        Example:
            client.project.delete(project)
            deleted = client.project.delete(
                'uuid', namespace='tenant.team', ignore_missing=True
            )

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
        """Set meta.tags (replaces existing); wraps update(update_mask='meta.tags').

        id_or_resource and namespace follow class docstring. Only for resources
        with meta.tags in mutable fields.

        Args:
            id_or_resource: UUID or resource object. See class docstring.
            tags: Tag list; replaces all. Use [] to clear.
            namespace: See class docstring.

        Returns:
            Updated resource.

        Raises:
            NotImplementedError: No tagging support.
            ValueError: Missing namespace or no meta.

        Example:
            updated = client.project.tag(project, tags=['reviewed', 'production'])

        """
        resource, uuid, ns, meta = self._resolve_for_tag(
            id_or_resource, namespace, operation="tag"
        )
        assert self._update_fn is not None  # guaranteed by _resolve_for_tag
        model_copy = getattr(resource, "model_copy")  # noqa: B009
        payload = model_copy(update={"meta": meta.model_copy(update={"tags": tags})})
        return self._update_fn(self._client, ns, uuid, payload, "meta.tags")

    def untag(
        self,
        id_or_resource: str | T,
        keys: list[str],
        namespace: str | None = None,
    ) -> T:
        """Remove listed tags from meta.tags; fetch, filter, then update(meta.tags).

        id_or_resource and namespace follow class docstring. Keys not present
        are ignored.

        Args:
            id_or_resource: UUID or resource object. See class docstring.
            keys: Tag values to remove; others preserved.
            namespace: See class docstring.

        Returns:
            Updated resource.

        Raises:
            NotImplementedError: No tagging support.
            ValueError: Missing namespace or no meta.

        Example:
            updated = client.project.untag(project, keys=['deprecated'])

        """
        resource, uuid, ns, meta = self._resolve_for_tag(
            id_or_resource, namespace, operation="untag"
        )
        assert self._update_fn is not None  # guaranteed by _resolve_for_tag
        current: list[str] = getattr(meta, "tags", None) or []
        new_tags: list[str] = [t for t in current if t not in keys]
        model_copy = getattr(resource, "model_copy")  # noqa: B009
        payload = model_copy(
            update={"meta": meta.model_copy(update={"tags": new_tags})}
        )
        return self._update_fn(self._client, ns, uuid, payload, "meta.tags")

    # -- Internal helpers for tag / untag ----------------------------------

    def _resolve_for_tag(
        self,
        id_or_resource: str | T,
        namespace: str | None,
        *,
        operation: str = "tag",
    ) -> tuple[T, str, str, Any]:
        """Resolve resource, uuid, namespace and meta for tag/untag.

        Returns:
            (resource, uuid, namespace, meta)

        Raises:
            NotImplementedError: When the resource does not support tagging.
            ValueError: When the resource has no ``meta``.
        """
        if (
            not self._tags_paths
            or "meta.tags" not in self._tags_paths
            or self._update_fn is None
        ):
            raise NotImplementedError(
                f"This resource does not support {operation}."
            ) from None
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
            raise ValueError(
                f"Resource has no meta; cannot {operation} meta.tags."
            ) from None
        return resource, uuid, ns, meta


SystemResourceFacade = ResourceFacade
"""Backward-compat alias. Use ``ResourceFacade(scope="system")`` instead."""

OssResourceFacade = ResourceFacade
"""Backward-compat alias. Use ``ResourceFacade(scope="oss")`` instead."""


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
        """Fetch log messages for a scan result (ScanLogRequest API).

        Args:
            scan_result_uuid: UUID from client.scan_result.list() or .get().
            namespace: Target namespace; defaults to client tenant.
            max_entries: Max log entries (default 100).
            log_levels: Filter by level (ScanLogLevel); None = all.
            start_time: Logs after (ISO 8601).
            end_time: Logs before (ISO 8601).
            newest_first: True = newest first; False/None = chronological.

        Returns:
            Log message list; empty if none match.

        Raises:
            ValueError: Namespace required but not set.

        Example:
            logs = client.scan_logs.get_logs(
                scan_result_uuid='...', namespace='tenant.team'
            )

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
