# pyright: reportImportCycles=false
"""Resource facade for the resource-oriented Client API.

Provides ``ResourceRuntimeFacade[T]`` — a single facade class that handles all
resource scopes (tenant, oss, system) via the ``scope`` parameter — and
``ScanLogsFacade`` for the request-based scan logs workflow.

``scope`` controls namespace resolution:

* ``None`` (default) — tenant-scoped; namespace from client default or arg.
* ``"oss"`` — OSS-scoped; namespace is always ``"oss"``.
* ``"system"`` — system-scoped; namespace is always ``"system"``.

See docs/reference/resources.md and docs/guides/retrieving-scan-results.md.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import (
    TYPE_CHECKING,
    Any,
    Literal,
    TypeGuard,
    cast,
    override,
)

from pydantic import BaseModel

from .core.exceptions import AmbiguousError, NotFoundError
from .core.filter import F, FilterExpression
from .core.types import ListParameters, list_parameters_has_nonempty_field_mask
from .operations import BaseResourceOperations
from .utils.namespace import resolve_namespace_for_resource

if TYPE_CHECKING:
    from collections.abc import Callable

    from .api_client import APIClient
    from .registry import ResourceEntry
    from .resources.scan_log_request import ScanLogLevel, ScanLogRequestLogMessage


class ListableFacade[T: BaseModel]:
    """Base facade: list, list_iter, lookup only. No get/create/update/delete.

    Shared parameter vocabulary (list, lookup, list_iter):
    traverse, concurrent, max_workers, namespace, list_params, max_pages, parent,
    filter, mask, page_size, page_token, page_id, sort_by, desc, count,
    from_date, to_date, archive, pr_uuid, ci_run_uuid, **kwargs (identity → filter).
    See method docstrings for signatures; semantics: traverse=tenant-wide,
    concurrent=parallel namespaces when traverse=True, namespace=canonical path,
    list_params=ListParameters (kwargs override), max_pages=None=all,
    parent=scope by meta.parent_uuid, filter/mask=API expressions,
    page_*=pagination, sort_by/desc=ordering, count=return count only,
    from_date/to_date=ISO 8601, archive=from archive,
    ci_run_uuid=PR scan context id (OpenAPI list_parameters.ci_run_uuid);
    pr_uuid=deprecated alias for the same wire param.
    """

    def __init__(
        self,
        client: APIClient,
        default_namespace: str | None,
        entry: ResourceEntry,
        *,
        tags_paths: list[str] | None = None,
    ) -> None:
        super().__init__()
        self._client = client
        self._default_namespace = default_namespace
        self._resource_name = entry.resource_name
        self._parent_kind = entry.parent_kind
        self._tags_paths = tags_paths or []
        self._supported_ops = entry.supported_ops
        self._filter_kwarg_map: dict[str, str] = dict(entry.filter_kwarg_map)
        self._entry = entry
        self._ops: BaseResourceOperations[T] = BaseResourceOperations(
            client, entry.resource_name, entry.model_class
        )

    def _validate_list_remaining_kwargs(self, remaining_kwargs: dict[str, Any]) -> None:
        """Reject unknown flat kwargs before building ``ListParameters``."""
        allowed = set(ListParameters.model_fields) | set(self._filter_kwarg_map)
        unknown = sorted(key for key in remaining_kwargs if key not in allowed)
        if unknown:
            raise TypeError(
                f"Invalid list kwargs for {self._entry.attr_name}: {unknown}. "
                f"Allowed: {sorted(allowed)}. Use list_params=ListParameters(...) "
                "for advanced parameters."
            )

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
        filter: str | FilterExpression | None,
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
        ci_run_uuid: str | None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Build merged kwargs dict from explicit params, identity kwargs, and parent.

        Shared by ``list()`` and ``list_iter()`` to guarantee identical
        filter/mask/parent behaviour.
        """
        from .utils.model_validation import build_filter_from_identity_kwargs

        # Normalize FilterExpression to str early
        if isinstance(filter, FilterExpression):
            filter = str(filter)

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
                ("ci_run_uuid", ci_run_uuid),
            )
            if v is not None
        }
        list_kwargs = {**kwargs, **explicit}

        merged_filter, remaining_kwargs = build_filter_from_identity_kwargs(
            self._filter_kwarg_map, list_kwargs
        )
        if merged_filter is not None:
            remaining_kwargs["filter"] = merged_filter

        if parent is not None:
            parent_uuid = getattr(parent, "uuid", "")
            parent_clause = str(F("meta.parent_uuid") == parent_uuid)
            existing = remaining_kwargs.get("filter")
            remaining_kwargs["filter"] = (
                f"{existing} AND {parent_clause}" if existing else parent_clause
            )

        return remaining_kwargs

    def _effective_list_parameters(
        self,
        *,
        traverse: bool,
        list_params: ListParameters | None,
        parent: Any,
        filter: str | FilterExpression | None,
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
        ci_run_uuid: str | None,
        **kwargs: Any,
    ) -> ListParameters | None:
        """Merge list kwargs and list_params like ``list`` / ``list_iter``."""
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
            ci_run_uuid=ci_run_uuid,
            **kwargs,
        )
        self._validate_list_remaining_kwargs(remaining_kwargs)
        return self._list_params(list_params, traverse=traverse, **remaining_kwargs)

    def list(
        self,
        traverse: bool = False,
        concurrent: bool = False,
        max_workers: int = 10,
        namespace: str | None = None,
        list_params: ListParameters | None = None,
        max_pages: int | None = None,
        parent: Any = None,
        filter: str | FilterExpression | None = None,
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
        ci_run_uuid: str | None = None,
        **kwargs: Any,
    ) -> list[T] | list[dict[str, Any]]:
        """List resources with full pagination and optional concurrent mode.

        Uses full pagination (list_all=True). With ``traverse=True`` and
        ``concurrent=True``, queries each namespace in parallel.
        If any namespace query fails, raises after all queries complete.

        Args:
            traverse: Search child namespaces recursively (tenant-wide query).
            concurrent: Query each namespace in parallel (requires
                ``traverse=True``).
            max_workers: Thread pool size for concurrent mode (default 10).
            namespace: Canonical namespace path (e.g. ``"tenant.child"``);
                defaults to the client tenant.
            list_params: ``ListParameters`` object; flat kwargs override its
                values when both are provided.
            max_pages: Maximum pages to fetch; ``None`` fetches all.
            parent: Scope results to a parent resource's namespace and
                ``meta.parent_uuid``.
            filter: API filter expression (``str`` or ``FilterExpression``
                via ``F()``).
            mask: Comma-separated field mask limiting returned fields.
            page_size: Results per page; ``None`` uses the API default.
            page_token: Pagination cursor from a previous response.
            page_id: Pagination cursor (alternative to ``page_token``).
            sort_by: Field path to sort results by.
            desc: Reverse sort order when ``True``.
            count: Return count only (no resource bodies).
            from_date: ISO 8601 lower-bound date filter.
            to_date: ISO 8601 upper-bound date filter.
            archive: Query archived resources when ``True``.
            pr_uuid: Deprecated; use ``ci_run_uuid``. Sent as
                ``list_parameters.ci_run_uuid``.
            ci_run_uuid: PR scan context id (OpenAPI ``list_parameters.ci_run_uuid``).
            **kwargs: Identity kwargs mapped to filter clauses via
                ``filter_kwarg_map`` (e.g. ``name="foo"`` becomes
                ``meta.name=="foo"``).

        Returns:
            List of resources, or shallow-copied wire JSON dicts per row when a
            non-empty field ``mask`` is in effect (``mask=`` or
            ``ListParameters.mask``). Use unmasked ``list()`` when you need full
            Pydantic models.

        Raises:
            ValueError: Missing namespace, unsupported parent, or concurrent
                without traverse.
            ConcurrentNamespaceQueryError: Any namespace query failed during
                concurrent traversal.

        Example:
            List critical findings tenant-wide::

                findings = client.Finding.list(
                    traverse=True,
                    filter='spec.level==FINDING_LEVEL_CRITICAL'
                )

        """
        if "list" not in self._supported_ops:
            raise NotImplementedError("This resource does not support list.") from None
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
                ci_run_uuid=ci_run_uuid,
                **kwargs,
            )

        # Standard single-query mode
        lp = self._effective_list_parameters(
            traverse=traverse,
            list_params=list_params,
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
            ci_run_uuid=ci_run_uuid,
            **kwargs,
        )
        return self._ops.list(ns, lp, max_pages)

    def _list_concurrent(
        self,
        namespace: str,
        max_workers: int,
        list_params: ListParameters | None,
        max_pages: int | None,
        parent: Any,
        **kwargs: Any,
    ) -> list[T] | list[dict[str, Any]]:
        """Fetch namespaces with traverse, then query each in parallel; merge.

        Raises:
            ConcurrentNamespaceQueryError: One or more namespace queries failed.
        """
        from .resources.namespace import Namespace as NamespaceModel
        from .utils.parallel import execute_across_namespaces

        # Phase 1: Get all namespaces via ops (no module-level function needed)
        ns_ops: BaseResourceOperations[Any] = BaseResourceOperations(
            self._client, "namespaces", NamespaceModel
        )
        all_namespaces_list = ns_ops.list(
            namespace,
            ListParameters(traverse=True),  # pyright: ignore[reportCallIssue]
        )
        all_namespaces = cast("list[NamespaceModel]", all_namespaces_list)

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
        def query_namespace(ns: str) -> list[T] | list[dict[str, Any]]:
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
        merged = execute_across_namespaces(
            namespaces=namespace_names,
            query_fn=query_namespace,
            max_workers=max_workers,
        )
        return cast("list[T] | list[dict[str, Any]]", merged)

    def lookup(
        self,
        traverse: bool = False,
        concurrent: bool = False,
        max_workers: int = 10,
        namespace: str | None = None,
        list_params: ListParameters | None = None,
        max_pages: int = 2,
        parent: Any = None,
        filter: str | FilterExpression | None = None,
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
        ci_run_uuid: str | None = None,
        **kwargs: Any,
    ) -> T:
        """Return the single resource matching criteria.

        Calls ``list()`` under the hood.

        Convenience wrapper that fetches up to ``max_pages`` (default 2) pages
        and expects exactly one result.

        Args:
            traverse: Search child namespaces recursively (tenant-wide query).
            concurrent: Query each namespace in parallel (requires
                ``traverse=True``).
            max_workers: Thread pool size for concurrent mode (default 10).
            namespace: Canonical namespace path (e.g. ``"tenant.child"``);
                defaults to the client tenant.
            list_params: ``ListParameters`` object; flat kwargs override its
                values when both are provided.
            max_pages: Maximum pages to search (default 2).
            parent: Scope results to a parent resource's namespace and
                ``meta.parent_uuid``.
            filter: API filter expression (``str`` or ``FilterExpression``
                via ``F()``).
            mask: Comma-separated field mask limiting returned fields.
            page_size: Results per page; ``None`` uses the API default.
            page_token: Pagination cursor from a previous response.
            page_id: Pagination cursor (alternative to ``page_token``).
            sort_by: Field path to sort results by.
            desc: Reverse sort order when ``True``.
            count: Return count only (no resource bodies).
            from_date: ISO 8601 lower-bound date filter.
            to_date: ISO 8601 upper-bound date filter.
            archive: Query archived resources when ``True``.
            pr_uuid: Deprecated; use ``ci_run_uuid``.
            ci_run_uuid: PR scan context id for list scoping.
            **kwargs: Identity kwargs mapped to filter clauses via
                ``filter_kwarg_map`` (e.g. ``name="foo"`` becomes
                ``meta.name=="foo"``).

        Returns:
            The single matching resource.

        Raises:
            NotFoundError: No resource matches.
            AmbiguousError: Multiple match; narrow criteria.
            ValueError: Missing namespace, concurrent without traverse, or a
                non-empty list field mask (``mask=`` / ``ListParameters.mask``);
                ``lookup`` always returns a full typed resource—use ``list()`` or
                ``list_iter()`` for masked wire-shaped rows.

        Example:
            project = client.Project.lookup(namespace='tenant.team', name='my-project')

        """
        if "list" not in self._supported_ops:
            raise NotImplementedError(
                "This resource does not support lookup."
            ) from None
        lp = self._effective_list_parameters(
            traverse=traverse,
            list_params=list_params,
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
            ci_run_uuid=ci_run_uuid,
            **kwargs,
        )
        if list_parameters_has_nonempty_field_mask(lp):
            raise ValueError(
                "lookup returns a typed resource; omit mask= (or ListParameters.mask) "
                "or use list() / list_iter() for masked wire-shaped rows."
            )
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
            ci_run_uuid=ci_run_uuid,
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
        return cast("T", items[0])

    def list_iter(
        self,
        traverse: bool = False,
        concurrent: bool = False,
        namespace: str | None = None,
        list_params: ListParameters | None = None,
        max_pages: int | None = None,
        parent: Any = None,
        filter: str | FilterExpression | None = None,
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
        ci_run_uuid: str | None = None,
        **kwargs: Any,
    ) -> Iterator[T | dict[str, Any]]:
        """Yield resources one at a time; memory-efficient lazy pagination.

        Same parameters as ``list()`` except ``concurrent`` is not supported;
        use ``list(concurrent=True)`` for parallel namespace queries.

        Args:
            traverse: Search child namespaces recursively (tenant-wide query).
            concurrent: Not supported; raises ``NotImplementedError``. Use
                ``list(concurrent=True)`` instead.
            namespace: Canonical namespace path (e.g. ``"tenant.child"``);
                defaults to the client tenant.
            list_params: ``ListParameters`` object; flat kwargs override its
                values when both are provided.
            max_pages: Maximum pages to fetch; ``None`` fetches all.
            parent: Scope results to a parent resource's namespace and
                ``meta.parent_uuid``.
            filter: API filter expression (``str`` or ``FilterExpression``
                via ``F()``).
            mask: Comma-separated field mask limiting returned fields.
            page_size: Results per page; ``None`` uses the API default.
            page_token: Pagination cursor from a previous response.
            page_id: Pagination cursor (alternative to ``page_token``).
            sort_by: Field path to sort results by.
            desc: Reverse sort order when ``True``.
            count: Return count only (no resource bodies).
            from_date: ISO 8601 lower-bound date filter.
            to_date: ISO 8601 upper-bound date filter.
            archive: Query archived resources when ``True``.
            pr_uuid: Deprecated; use ``ci_run_uuid``.
            ci_run_uuid: PR scan context id for list scoping.
            **kwargs: Identity kwargs mapped to filter clauses via
                ``filter_kwarg_map`` (e.g. ``name="foo"`` becomes
                ``meta.name=="foo"``).

        Yields:
            Full resource models, or shallow-copied wire JSON dicts when a
            non-empty field mask is in effect (same rule as ``list()``).

        Raises:
            NotImplementedError: concurrent=True requested.
            ValueError: Missing namespace or unsupported parent.

        Example:
            for finding in client.Finding.list_iter(traverse=True):
                process(finding)

        """
        if "list" not in self._supported_ops:
            raise NotImplementedError(
                "This resource does not support list_iter."
            ) from None
        if concurrent:
            raise NotImplementedError(
                "concurrent=True is not supported for list_iter. "
                "Use list(concurrent=True, traverse=True) instead."
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
        lp = self._effective_list_parameters(
            traverse=traverse,
            list_params=list_params,
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
            ci_run_uuid=ci_run_uuid,
            **kwargs,
        )
        return self._ops.list_iter(ns, lp, max_pages)


class ResourceRuntimeFacade[T: BaseModel](ListableFacade[T]):
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
        * ``"oss"`` — OSS-scoped; namespace always ``"oss"``.
        * ``"system"`` — system-scoped; namespace always ``"system"``.
    """

    def __init__(
        self,
        client: APIClient,
        default_namespace: str | None,
        entry: ResourceEntry,
        *,
        tags_paths: list[str] | None = None,
    ) -> None:
        super().__init__(client, default_namespace, entry, tags_paths=tags_paths)
        self._supported_ops = entry.supported_ops
        self._build_create_payload_fn: Callable[..., Any] | None = (
            entry.build_create_payload_fn
        )
        self._scope: Literal["system"] | Literal["oss"] | None = entry.scope
        self._create_mode = entry.create_mode
        self._update_requires_mask = entry.update_requires_mask
        self._workflow_flags = entry.workflow_flags

    @property
    def scope(self) -> Literal["system"] | Literal["oss"] | None:
        """The resource scope: ``"oss"``, ``"system"``, or ``None`` (tenant)."""
        return self._scope

    @override
    def _ns(self, namespace: str | None) -> str:
        if self._scope == "oss":
            return "oss"
        if self._scope == "system":
            return "system"
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

        When ``id_or_resource`` is a resource object, the UUID is extracted
        from it and the namespace is derived from the resource's
        ``tenant_meta`` unless overridden by ``namespace=``.

        Args:
            id_or_resource: UUID string, or a resource object whose
                ``uuid`` and ``tenant_meta`` are used for resolution.
            namespace: Canonical namespace path (e.g. ``"tenant.child"``);
                defaults to the client tenant or the resource's namespace.

        Returns:
            The resource.

        Raises:
            NotImplementedError: No get support.
            ValueError: Namespace required but not set.

        Example:
            project = client.Project.get('uuid-here', namespace='tenant.team')
            updated = client.Project.get(project)

        """
        if "get" not in self._supported_ops:
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
        return self._ops.get(ns, cast("str", uuid))

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
        """Create a resource via ``payload=`` or kwargs (``build_create_payload``).

        Either pass a ``CreateXPayload`` in ``payload=`` or resource-specific
        kwargs; the two forms are mutually exclusive.

        Args:
            payload: A ``CreateXPayload`` model instance; mutually exclusive
                with keyword arguments.
            name: Convenience kwarg; merged into builder kwargs.
            description: Convenience kwarg; merged into builder kwargs.
            namespace_uuid: Convenience kwarg; merged into builder kwargs.
            namespace: Canonical namespace path (e.g. ``"tenant.child"``)
                where the resource will be created; defaults to the client
                tenant.
            **kwargs: Resource-specific keyword arguments passed to the
                resource's ``build_create_payload`` function.

        Returns:
            Created resource with server-assigned fields.

        Raises:
            NotImplementedError: Resource has no create.
            TypeError: Both payload and kwargs, or neither, or kwargs without builder.
            ValueError: Namespace required but not set.

        Example:
            ns = client.Namespace.create(name='my-namespace', namespace='tenant')

        """
        if "create" not in self._supported_ops:
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
        if payload is None and merged and self._create_mode == "both":
            # namespace is consumed by _ns(); do not pass to builder
            create_kwargs = {k: v for k, v in merged.items() if k != "namespace"}
            if self._build_create_payload_fn is None:
                raise TypeError(
                    "create() contract is inconsistent: "
                    "create_mode=both without builder."
                )
            payload = self._build_create_payload_fn(**create_kwargs)
        elif payload is None and merged and self._create_mode != "both":
            raise TypeError(
                "create() for this resource requires payload=; kwargs not supported."
            )
        ns = self._ns(namespace)
        return self._ops.create(ns, payload)

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
        """Update a resource: ``update_mask`` + payload, or field kwargs (mask derived).

        When using field kwargs (e.g. ``meta_tags=[...]``), ``id_or_resource``
        must be a resource instance; the resource is used as the payload and
        the mask is derived automatically.

        Args:
            id_or_resource: UUID string, or a resource object whose
                ``uuid`` and ``tenant_meta`` are used for resolution.
            payload: Updated fields; optional when ``id_or_resource`` is a
                resource instance (the resource itself is used as payload).
            update_mask: Comma-separated field paths to update
                (e.g. ``"meta.tags"``).
            meta_description: Convenience kwarg; updates ``meta.description``.
            meta_tags: Convenience kwarg; updates ``meta.tags``.
            namespace: Canonical namespace path (e.g. ``"tenant.child"``);
                defaults to the client tenant or the resource's namespace.
            **kwargs: Mutable field kwargs; ``update_mask`` is derived
                automatically if omitted.

        Returns:
            Updated resource.

        Raises:
            NotImplementedError: No update support.
            TypeError: No mask nor kwargs; or kwargs with UUID id_or_resource.
            ValueError: Missing namespace or immutable in update_mask.

        Example:
            updated = client.Project.update(project, meta_tags=['reviewed'])

        """
        if "update" not in self._supported_ops:
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
        # Convert comma-separated mask string to list (strip empty segments)
        mask_list: list[str] = (
            [p.strip() for p in update_mask.split(",") if p.strip()]
            if isinstance(update_mask, str)
            else (update_mask or [])
        )
        assert payload is not None  # guaranteed by TypeError guard above
        return self._ops.update(ns, cast("str", uuid), payload, mask_list)

    def delete(
        self,
        name_or_resource: str | T,
        namespace: str | None = None,
        *,
        ignore_missing: bool = False,
    ) -> bool:
        """Remove a resource by UUID or resource object.

        When ``name_or_resource`` is a resource object, the UUID is extracted
        from it and the namespace is derived from the resource's
        ``tenant_meta`` unless overridden by ``namespace=``.

        Args:
            name_or_resource: UUID string, or a resource object whose
                ``uuid`` and ``tenant_meta`` are used for resolution.
            namespace: Canonical namespace path (e.g. ``"tenant.child"``);
                defaults to the client tenant or the resource's namespace.
            ignore_missing: If ``True``, return ``False`` on 404 instead of
                raising ``NotFoundError``.

        Returns:
            ``True`` if deleted; ``False`` if ``ignore_missing`` and not found.

        Raises:
            NotImplementedError: No delete support.
            NotFoundError: Not found and not ``ignore_missing``.
            ValueError: Namespace required but not set.

        Example:
            client.Project.delete(project)
            deleted = client.Project.delete(
                'uuid', namespace='tenant.team', ignore_missing=True
            )

        """
        if "delete" not in self._supported_ops:
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
            return self._ops.delete(ns, cast("str", uuid))
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
        """Set ``meta.tags`` (replaces existing tags).

        Wraps ``update(update_mask='meta.tags')``.

        Only available for resources whose ``meta.tags`` is a mutable field.

        Args:
            id_or_resource: UUID string, or a resource object whose
                ``uuid`` and ``tenant_meta`` are used for resolution.
            tags: Tag list that replaces all existing tags. Use ``[]`` to
                clear.
            namespace: Canonical namespace path (e.g. ``"tenant.child"``);
                defaults to the client tenant or the resource's namespace.

        Returns:
            Updated resource.

        Raises:
            NotImplementedError: No tagging support.
            ValueError: Missing namespace or no meta.

        Example:
            updated = client.Project.tag(project, tags=['reviewed', 'production'])

        """
        resource, uuid, ns, meta = self._resolve_for_tag(
            id_or_resource, namespace, operation="tag"
        )
        model_copy = getattr(resource, "model_copy")  # noqa: B009
        payload = model_copy(update={"meta": meta.model_copy(update={"tags": tags})})
        return self._ops.update(ns, uuid, payload, ["meta.tags"])

    def untag(
        self,
        id_or_resource: str | T,
        keys: list[str],
        namespace: str | None = None,
    ) -> T:
        """Remove listed tags from ``meta.tags``; fetch, filter, then update.

        Tags in ``keys`` that are not present on the resource are silently
        ignored.

        Args:
            id_or_resource: UUID string, or a resource object whose
                ``uuid`` and ``tenant_meta`` are used for resolution.
            keys: Tag values to remove; all other tags are preserved.
            namespace: Canonical namespace path (e.g. ``"tenant.child"``);
                defaults to the client tenant or the resource's namespace.

        Returns:
            Updated resource.

        Raises:
            NotImplementedError: No tagging support.
            ValueError: Missing namespace or no meta.

        Example:
            updated = client.Project.untag(project, keys=['deprecated'])

        """
        resource, uuid, ns, meta = self._resolve_for_tag(
            id_or_resource, namespace, operation="untag"
        )
        current: list[str] = getattr(meta, "tags", None) or []
        new_tags: list[str] = [t for t in current if t not in keys]
        model_copy = getattr(resource, "model_copy")  # noqa: B009
        payload = model_copy(
            update={"meta": meta.model_copy(update={"tags": new_tags})}
        )
        return self._ops.update(ns, uuid, payload, ["meta.tags"])

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
            or "update" not in self._supported_ops
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


class ScanLogsFacade:
    """Facade for retrieving scan logs (request-based API; not in registry).

    Use client.ScanLogs.get_logs(scan_result_uuid) after obtaining a scan
    result UUID (e.g. from client.ScanResult.list() or .get()).
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
            scan_result_uuid: UUID from client.ScanResult.list() or .get().
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
            logs = client.ScanLogs.get_logs(
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


# Backward-compatible aliases while generated stubs and imports converge.
_ListableFacade = ListableFacade
ResourceFacade = ResourceRuntimeFacade
