"""Execute Query.create with per-leaf-namespace grouping."""

from __future__ import annotations

import warnings
from collections import defaultdict
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import TYPE_CHECKING, Any, cast

from endorlabs.resources.query import CreateQueryPayload

if TYPE_CHECKING:
    from .spec import QuerySpec

UUID_BATCH_SIZE = 500


def project_uuid(project: Any) -> str:
    """Return project UUID from a model or dict row."""
    if isinstance(project, dict):
        project_dict = cast("dict[str, Any]", project)
        return str(project_dict.get("uuid") or "")
    return str(getattr(project, "uuid", None) or "")


def project_namespace(project: Any) -> str | None:
    """Return wire namespace from a model or dict row."""
    ns = getattr(project, "namespace", None)
    if ns:
        return str(ns)
    if isinstance(project, dict):
        project_dict = cast("dict[str, Any]", project)
        tm = project_dict.get("tenant_meta")
        if isinstance(tm, dict):
            tenant_meta = cast("dict[str, Any]", tm)
            raw = tenant_meta.get("namespace")
            return str(raw) if raw else None
        return None
    tenant_meta = getattr(project, "tenant_meta", None)
    if tenant_meta is None:
        return None
    if isinstance(tenant_meta, dict):
        tenant_meta_dict = cast("dict[str, Any]", tenant_meta)
        raw = tenant_meta_dict.get("namespace")
        return str(raw) if raw else None
    raw = getattr(tenant_meta, "namespace", None)
    return str(raw) if raw else None


def group_projects_by_namespace(projects: list[Any]) -> dict[str, list[str]]:
    """Map wire namespace to project UUIDs for per-namespace Query POST."""
    out: dict[str, list[str]] = defaultdict(list)
    for proj in projects:
        ns = project_namespace(proj)
        uid = project_uuid(proj)
        if not ns or not uid:
            continue
        out[ns].append(uid)
    return dict(out)


def query_create(
    client: Any,
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
    return client.Query.create(payload=payload, namespace=namespace)


def _uuid_batches(
    uuids: list[str],
    batch_size: int = UUID_BATCH_SIZE,
) -> list[list[str]]:
    if len(uuids) <= batch_size:
        return [uuids]
    return [uuids[i : i + batch_size] for i in range(0, len(uuids), batch_size)]


class QueryExecutor:
    """Run a ``QuerySpec`` once per leaf namespace and merge parsed results."""

    def __init__(
        self,
        client: Any,
        *,
        name_prefix: str = "endor-query",
        max_workers: int = 1,
        uuid_batch_size: int = UUID_BATCH_SIZE,
    ) -> None:
        super().__init__()
        self._client = client
        self._name_prefix = name_prefix
        self._max_workers = max(1, max_workers)
        self._uuid_batch_size = max(1, uuid_batch_size)

    def _execute_namespace[T](
        self,
        spec: QuerySpec,
        *,
        namespace: str,
        uuids: list[str],
        parse_result: Callable[[Any], dict[str, T]],
    ) -> dict[str, T]:
        merged: dict[str, T] = {}
        slug = namespace.rsplit(".", maxsplit=1)[-1] if namespace else "root"
        batches = _uuid_batches(uuids, self._uuid_batch_size)
        for batch_index, batch in enumerate(batches):
            suffix = f"-{batch_index}" if len(uuids) > self._uuid_batch_size else ""
            result = query_create(
                self._client,
                namespace=namespace,
                name=f"{self._name_prefix}-{slug}{suffix}",
                query_spec=spec.for_namespace_batch(batch),
            )
            merged.update(parse_result(result))
        return merged

    def run[T](
        self,
        spec: QuerySpec,
        *,
        projects: list[Any],
        parse_result: Callable[[Any], dict[str, T]],
    ) -> dict[str, T]:
        """Execute the spec per leaf namespace and merge ``parse_result`` maps."""
        grouped = group_projects_by_namespace(projects)
        if not grouped:
            return {}

        client_default = getattr(self._client, "_default_namespace", None)
        if client_default and len(grouped) > 1:
            root_depth = str(client_default).count(".")
            if all(ns.count(".") > root_depth for ns in grouped):
                warnings.warn(
                    "Query projects span child namespaces; POST uses each "
                    "project's wire namespace (not the client default). "
                    "Posting at tenant root alone can return zero counts.",
                    UserWarning,
                    stacklevel=2,
                )

        merged: dict[str, T] = {}
        items = sorted(grouped.items())
        if self._max_workers <= 1 or len(items) <= 1:
            for ns, uuids in items:
                merged.update(
                    self._execute_namespace(
                        spec,
                        namespace=ns,
                        uuids=uuids,
                        parse_result=parse_result,
                    )
                )
            return merged

        workers = min(self._max_workers, len(items))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [
                pool.submit(
                    self._execute_namespace,
                    spec,
                    namespace=ns,
                    uuids=uuids,
                    parse_result=parse_result,
                )
                for ns, uuids in items
            ]
            for future in as_completed(futures):
                merged.update(future.result())
        return merged
