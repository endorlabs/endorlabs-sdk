"""Execute Query.create with per-leaf-namespace grouping and list pagination."""

from __future__ import annotations

import warnings
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import TYPE_CHECKING, Any

from endorlabs.resources.query import CreateQueryPayload

from .parse import next_page_token
from .row_fields import project_namespace, project_uuid

if TYPE_CHECKING:
    from .scope import QueryScope
    from .spec import QuerySpec

UUID_BATCH_SIZE = 500


def group_projects_by_namespace(projects: list[Any]) -> dict[str, list[str]]:
    """Map wire namespace to project UUIDs for per-namespace Query POST."""
    from collections import defaultdict

    out: dict[str, list[str]] = defaultdict(list)
    for proj in projects:
        ns = project_namespace(proj)
        uid = project_uuid(proj)
        if not ns or not uid:
            continue
        out[ns].append(uid)
    return dict(out)


def _query_create_callable(query_resource: Any) -> Callable[..., Any]:
    """Resolve ``Query.create`` from a ``Client`` or ``QueryFacade``."""
    if hasattr(query_resource, "Query"):
        query_facade = query_resource.Query
        if hasattr(query_facade, "create"):
            return query_facade.create
    if hasattr(query_resource, "create"):
        return query_resource.create
    raise AttributeError(
        "Query executor requires endorlabs.Client or QueryFacade with create()"
    )


def query_create(
    query_resource: Any,
    *,
    namespace: str,
    name: str,
    query_spec: dict[str, Any],
) -> Any:
    """POST one ``Query.create`` payload to ``namespace``."""
    payload = CreateQueryPayload(
        meta={"name": name},
        spec={"query_spec": query_spec},
    )
    return _query_create_callable(query_resource)(payload=payload, namespace=namespace)


def query_create_pages(
    query_resource: Any,
    *,
    namespace: str,
    name: str,
    query_spec: dict[str, Any],
    max_pages: int | None = None,
) -> list[Any]:
    """POST Query.create repeatedly while ``next_page_token`` is set."""
    pages: list[Any] = []
    page_token: int | None = None
    page_index = 0
    while True:
        spec = dict(query_spec)
        lp = dict(spec.get("list_parameters") or {})
        if page_token is None:
            lp.pop("page_token", None)
        else:
            lp["page_token"] = page_token
        spec["list_parameters"] = lp
        suffix = f"-p{page_index}" if page_index else ""
        result = query_create(
            query_resource,
            namespace=namespace,
            name=f"{name}{suffix}",
            query_spec=spec,
        )
        pages.append(result)
        page_token = next_page_token(result)
        page_index += 1
        if page_token is None or (max_pages is not None and page_index >= max_pages):
            break
    return pages


def _uuid_batches(
    uuids: list[str],
    batch_size: int = UUID_BATCH_SIZE,
) -> list[list[str]]:
    if len(uuids) <= batch_size:
        return [uuids]
    return [uuids[i : i + batch_size] for i in range(0, len(uuids), batch_size)]


class QueryExecutor:
    """Run a ``QuerySpec`` per ``QueryScope`` and merge parsed results."""

    def __init__(
        self,
        query_resource: Any,
        *,
        name_prefix: str = "endor-query",
        max_workers: int = 1,
        uuid_batch_size: int = UUID_BATCH_SIZE,
        max_root_pages: int | None = None,
    ) -> None:
        super().__init__()
        self._query_resource = query_resource
        self._name_prefix = name_prefix
        self._max_workers = max(1, max_workers)
        self._uuid_batch_size = max(1, uuid_batch_size)
        self._max_root_pages = max_root_pages

    def _execute_scope[T](
        self,
        spec: QuerySpec,
        *,
        scope: QueryScope,
        parse_page: Callable[[Any], dict[str, T]],
    ) -> dict[str, T]:
        merged: dict[str, T] = {}
        namespace = scope.namespace
        slug = namespace.rsplit(".", maxsplit=1)[-1] if namespace else "root"
        keys = list(scope.keys)
        batches: list[list[str]] = (
            _uuid_batches(keys, self._uuid_batch_size) if keys else [[]]
        )
        for batch_index, batch in enumerate(batches):
            suffix = f"-{batch_index}" if len(keys) > self._uuid_batch_size else ""
            wire = spec.for_scope_batch(tuple(batch))
            for _page_index, result in enumerate(
                query_create_pages(
                    self._query_resource,
                    namespace=namespace,
                    name=f"{self._name_prefix}-{slug}{suffix}",
                    query_spec=wire,
                    max_pages=self._max_root_pages,
                )
            ):
                merged.update(parse_page(result))
        return merged

    def execute[T](
        self,
        spec: QuerySpec,
        *,
        scopes: list[QueryScope],
        parse_page: Callable[[Any], dict[str, T]],
    ) -> dict[str, T]:
        """Execute the spec per scope and merge ``parse_page`` maps."""
        if not scopes:
            return {}

        client_default = getattr(self._query_resource, "_default_namespace", None)
        if client_default is None:
            client_default = getattr(self._query_resource, "default_namespace", None)
        if client_default and len(scopes) > 1:
            root_depth = str(client_default).count(".")
            if all(s.namespace.count(".") > root_depth for s in scopes):
                warnings.warn(
                    "Query scopes span child namespaces; POST uses each "
                    "scope's wire namespace (not the client default). "
                    "Posting at tenant root alone can return zero counts.",
                    UserWarning,
                    stacklevel=2,
                )

        merged: dict[str, T] = {}
        ordered = sorted(scopes, key=lambda s: s.namespace)
        if self._max_workers <= 1 or len(ordered) <= 1:
            for scope in ordered:
                merged.update(
                    self._execute_scope(spec, scope=scope, parse_page=parse_page)
                )
            return merged

        workers = min(self._max_workers, len(ordered))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [
                pool.submit(
                    self._execute_scope,
                    spec,
                    scope=scope,
                    parse_page=parse_page,
                )
                for scope in ordered
            ]
            for future in as_completed(futures):
                merged.update(future.result())
        return merged

    def execute_pages[T](
        self,
        spec: QuerySpec,
        *,
        scopes: list[QueryScope],
        parse_page: Callable[[Any], T],
        merge_pages: Callable[[list[T]], T],
    ) -> T:
        """Execute per scope with root list pagination and merge page parses."""
        pages: list[T] = []
        for scope in scopes:
            wire = spec.for_scope_batch(scope.keys)
            scope_pages = query_create_pages(
                self._query_resource,
                namespace=scope.namespace,
                name=self._name_prefix,
                query_spec=wire,
                max_pages=self._max_root_pages,
            )
            pages.extend(parse_page(page) for page in scope_pages)
        return merge_pages(pages)

    def run_at_namespace[T](
        self,
        spec: QuerySpec,
        *,
        namespace: str,
        parse_page: Callable[[Any], T],
        merge_pages: Callable[[list[T]], T],
        max_pages: int | None = None,
    ) -> T:
        """Execute one spec at ``namespace`` with root list pagination."""
        pages = query_create_pages(
            self._query_resource,
            namespace=namespace,
            name=self._name_prefix,
            query_spec=spec.to_wire(),
            max_pages=max_pages if max_pages is not None else self._max_root_pages,
        )
        parsed = [parse_page(page) for page in pages]
        return merge_pages(parsed)
