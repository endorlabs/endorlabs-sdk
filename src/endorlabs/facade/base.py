# pyright: reportImportCycles=false
"""Listable facade base: list, list_iter."""

from __future__ import annotations

import warnings
from collections.abc import Callable, Iterator, Sequence
from typing import (
    TYPE_CHECKING,
    Any,
    cast,
)

from pydantic import BaseModel

from ..core.exceptions import ValidationError
from ..core.filter import F, FilterExpression
from ..core.types import ListParameters
from ..operations import BaseResourceOperations
from ..utils.namespace import resolve_namespace_for_resource

if TYPE_CHECKING:
    from ..api_client import APIClient
    from ..registry import ResourceEntry


class ListableFacade[T: BaseModel]:
    """Base facade: list and list_iter. No get/create/update/delete.

    Shared parameter vocabulary (list, list_iter):
    traverse, concurrent, max_workers, namespace, list_params, max_pages, parent,
    filter, mask, page_size, page_token, page_id, sort_by, desc, count,
    from_date, to_date, archive, pr_uuid, ci_run_uuid, **kwargs (identity → filter).
    See method docstrings for signatures; semantics: traverse=tenant-wide,
    concurrent=parallel namespaces when traverse=True (default on; opt out with
    concurrent=False), namespace=canonical path,
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
        self._workflow_flags = entry.workflow_flags

    def _maybe_warn_empty_project_namespace_list(
        self,
        rows: list[Any],
        *,
        traverse: bool,
        namespace_arg: str | None,
    ) -> None:
        """Warn when a project-scoped list at tenant root returns no rows."""
        if "project-namespace-list" not in self._workflow_flags:
            return
        if rows or traverse:
            return
        if namespace_arg is not None and namespace_arg != self._default_namespace:
            return
        warnings.warn(
            f"{self._entry.attr_name}.list() returned no rows at the client default "
            f"namespace ({self._default_namespace!r}) without traverse=True. "
            "Project-scoped resources usually live in child namespaces: resolve "
            "Project first, then pass namespace=project.namespace, or use "
            "Finding.list_by_project(project) / ScanResult.list_by_project(project) "
            "(see rule endor-namespace-scoping).",
            UserWarning,
            stacklevel=3,
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

    @staticmethod
    def _normalize_list_limit_kwarg(
        *,
        page_size: int | None,
        kwargs: dict[str, Any],
        attr_name: str,
    ) -> int | None:
        """Map ``limit`` to ``page_size`` for ``list()`` and ``list_iter()``."""
        limit = kwargs.pop("limit", None)
        if limit is None:
            return page_size
        if page_size is not None:
            raise TypeError(
                f"Cannot pass both limit and page_size to {attr_name}.list(); "
                "use one (limit is an alias for page_size)."
            )
        return limit

    def _ns(self, namespace: str | None) -> str:
        ns = namespace if namespace is not None else self._default_namespace
        if ns is None:
            raise ValidationError(
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
        from ..utils.model_validation import build_filter_from_identity_kwargs

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
        list_kwargs: dict[str, Any] = {**kwargs, **explicit}

        merged_filter, remaining_kwargs = build_filter_from_identity_kwargs(
            self._filter_kwarg_map, list_kwargs
        )
        if merged_filter is not None:
            remaining_kwargs["filter"] = merged_filter

        if parent is not None:
            parent_uuid = getattr(parent, "uuid", None) or parent
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
        concurrent: bool = True,
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

        Uses full pagination (list_all=True). With ``traverse=True``,
        ``concurrent`` defaults to ``True`` and queries each child namespace in
        parallel. Pass ``concurrent=False`` to use a single sequential traverse
        query. When ``traverse=False``, ``concurrent`` is ignored.
        If any namespace query fails, raises after all queries complete.

        Args:
            traverse: Search child namespaces recursively (tenant-wide query).
            concurrent: Query each namespace in parallel when ``traverse=True``
                (default ``True``; pass ``False`` to opt out).
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
            ValueError: Missing namespace or unsupported parent.
            ConcurrentNamespaceQueryError: Any namespace query failed during
                concurrent traversal.

        Example:
            List critical findings tenant-wide (concurrent by default)::

                findings = client.Finding.list(
                    traverse=True,
                    filter='spec.level==FINDING_LEVEL_CRITICAL'
                )

        """
        if "list" not in self._supported_ops:
            raise NotImplementedError("This resource does not support list.") from None

        page_size = self._normalize_list_limit_kwarg(
            page_size=page_size,
            kwargs=kwargs,
            attr_name=self._entry.attr_name,
        )

        if count is True:
            warnings.warn(
                f"{self._entry.attr_name}.list(count=True) is deprecated; "
                "use .count() instead.",
                DeprecationWarning,
                stacklevel=2,
            )
            return cast(
                "list[T] | list[dict[str, Any]]",
                self.count(
                    traverse=traverse,
                    namespace=namespace,
                    list_params=list_params,
                    parent=parent,
                    filter=filter,
                    from_date=from_date,
                    to_date=to_date,
                    archive=archive,
                    pr_uuid=pr_uuid,
                    ci_run_uuid=ci_run_uuid,
                    **kwargs,
                ),
            )

        if parent is not None:
            if self._parent_kind is None:
                raise ValidationError(
                    "This resource does not support list(parent=)."
                ) from None
            namespace = self._ns(
                resolve_namespace_for_resource(parent, self._default_namespace)
            )
        ns = self._ns(namespace)

        # Handle concurrent mode: query namespaces in parallel
        if concurrent and traverse:
            rows = self._list_concurrent(
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
            self._maybe_warn_empty_project_namespace_list(
                list(rows),
                traverse=True,
                namespace_arg=namespace,
            )
            return rows

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
        rows = self._ops.list(ns, lp, max_pages)
        self._maybe_warn_empty_project_namespace_list(
            list(rows),
            traverse=traverse,
            namespace_arg=namespace,
        )
        return rows

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
        from ..resources.namespace import Namespace as NamespaceModel
        from ..utils.parallel import execute_across_namespaces

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

        Same parameters as ``list()`` except ``concurrent`` defaults to
        ``False`` and is not supported when ``True``; use ``list(traverse=True)``
        for parallel namespace queries.

        Args:
            traverse: Search child namespaces recursively (tenant-wide query).
            concurrent: Not supported; raises ``NotImplementedError`` when
                ``True``. Defaults to ``False``.
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
                "Use list(traverse=True) instead."
            ) from None
        page_size = self._normalize_list_limit_kwarg(
            page_size=page_size,
            kwargs=kwargs,
            attr_name=self._entry.attr_name,
        )
        if parent is not None:
            if self._parent_kind is None:
                raise ValidationError(
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

    def count(
        self,
        traverse: bool = False,
        namespace: str | None = None,
        list_params: ListParameters | None = None,
        parent: Any = None,
        filter: str | FilterExpression | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
        archive: bool | None = None,
        pr_uuid: str | None = None,
        ci_run_uuid: str | None = None,
        **kwargs: Any,
    ) -> int:
        """Return the number of resources matching list filters."""
        if "list" not in self._supported_ops:
            raise NotImplementedError("This resource does not support count.") from None
        if parent is not None:
            if self._parent_kind is None:
                raise ValidationError(
                    "This resource does not support count(parent=)."
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
            mask=None,
            page_size=None,
            page_token=None,
            page_id=None,
            sort_by=None,
            desc=None,
            count=None,
            from_date=from_date,
            to_date=to_date,
            archive=archive,
            pr_uuid=pr_uuid,
            ci_run_uuid=ci_run_uuid,
            **kwargs,
        )
        return self._ops.count(ns, list_params=lp)

    def list_groups(
        self,
        *,
        paths: list[str] | None = None,
        traverse: bool = False,
        namespace: str | None = None,
        list_params: ListParameters | None = None,
        max_pages: int | None = None,
        parent: Any = None,
        filter: str | FilterExpression | None = None,
        page_size: int | None = None,
        **kwargs: Any,
    ) -> Iterator[Any]:
        """Yield grouped aggregation buckets from ``group_response`` pages."""
        from ..operations.list_response import iter_group_buckets_from_pages

        if "list" not in self._supported_ops:
            raise NotImplementedError(
                "This resource does not support list_groups."
            ) from None
        if parent is not None:
            if self._parent_kind is None:
                raise ValidationError(
                    "This resource does not support list_groups(parent=)."
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
            mask=None,
            page_size=page_size,
            page_token=None,
            page_id=None,
            sort_by=None,
            desc=None,
            count=None,
            from_date=None,
            to_date=None,
            archive=None,
            pr_uuid=None,
            ci_run_uuid=None,
            **kwargs,
        )
        if paths:
            if lp is None:
                lp = ListParameters.model_validate({"group_aggregation_paths": paths})
            else:
                lp = lp.model_copy(update={"group_aggregation_paths": paths})
        pages = self._ops.iter_group_pages(ns, lp, max_pages=max_pages)
        return iter_group_buckets_from_pages(pages)

    def latest(
        self,
        *,
        sort_by: str = "meta.create_time",
        desc: bool = True,
        parent: Any = None,
        namespace: str | None = None,
        list_params: ListParameters | None = None,
        filter: str | FilterExpression | None = None,
        **kwargs: Any,
    ) -> T | None:
        """Return the newest single row for ``sort_by`` (always ``max_pages=1``)."""
        if self._parent_kind and parent is None:
            warnings.warn(
                f"{self._entry.attr_name}.latest() without parent= may scan the "
                f"wrong scope; this resource has parent_kind={self._parent_kind!r}.",
                UserWarning,
                stacklevel=2,
            )
        items = self.list(
            parent=parent,
            namespace=namespace,
            list_params=list_params,
            filter=filter,
            sort_by=sort_by,
            desc=desc,
            max_pages=1,
            page_size=1,
            concurrent=False,
            **kwargs,
        )
        if not items:
            return None
        return cast("T", items[0])

    def latest_created(
        self,
        *,
        parent: Any = None,
        namespace: str | None = None,
        **kwargs: Any,
    ) -> T | None:
        """Newest row by ``meta.create_time`` (``max_pages=1``)."""
        return self.latest(
            sort_by="meta.create_time",
            desc=True,
            parent=parent,
            namespace=namespace,
            **kwargs,
        )

    def latest_updated(
        self,
        *,
        parent: Any = None,
        namespace: str | None = None,
        **kwargs: Any,
    ) -> T | None:
        """Newest row by ``meta.update_time`` (``max_pages=1``)."""
        return self.latest(
            sort_by="meta.update_time",
            desc=True,
            parent=parent,
            namespace=namespace,
            **kwargs,
        )

    def list_for_shards(
        self,
        shards: Sequence[Any],
        filter_fn: Callable[[Any], str],
        *,
        max_workers: int = 10,
        **list_kwargs: Any,
    ) -> list[Any]:
        """Parallel ``list()`` per shard via ``endorlabs.tools.list_sharding``."""
        from endorlabs.tools.list_sharding import list_for_shards

        return list_for_shards(
            self,
            shards,
            filter_fn,
            max_workers=max_workers,
            **list_kwargs,
        )
