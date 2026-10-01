"""Phase 2 — resolve SPDX via PackageLicenseQuery at the export namespace.

Customer-plane only: POST ``PackageLicenseQuery`` (and batched
``BatchPackageLicenseQuery``) under the tenant/child namespace being exported.
Do not list ``PackageLicense`` under a hardcoded catalog namespace — Query is the
product merge of catalog license data + ``PackageLicenseOverride`` for that
namespace chain.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import httpx

from endorlabs.core.exceptions import NotFoundError
from endorlabs.tools.list_bounds import resolve_collect_max_workers
from endorlabs.tools.parallel_scopes import parallel_over
from endorlabs.utils.jsonl_store import JsonlKeyedStore, load_jsonl_rows
from endorlabs.utils.logging_config import get_resource_logger
from endorlabs.workflows.common import WorkflowResult
from endorlabs.workflows.license_export.spdx import (
    empty_license_resolution,
    license_resolution_from_query,
)

if TYPE_CHECKING:
    from endorlabs.api_client import APIClient
    from endorlabs.client_surface import Client

LOGGER = get_resource_logger(__name__)

LICENSE_CACHE_FILENAME = "license_cache.jsonl"
LICENSE_OBJECTS_FILENAME = "license_objects.jsonl"
LICENSE_CACHE_KEY_FIELDS: tuple[str, ...] = ("package_version_uuid",)
LICENSE_OBJECTS_KEY_FIELDS: tuple[str, ...] = ("package_version_uuid",)
DEFAULT_BATCH_SIZE = 100


@dataclass
class ResolveResult(WorkflowResult):
    """Outcome of license resolution for a set of package_version UUIDs."""

    cache_path: str = ""
    objects_path: str = ""
    resolved_count: int = 0
    query_count: int = 0
    consensus_count: int = 0  # retained for API compat; always 0 (no catalog fast-path)
    missing_count: int = 0


def _api_transport(client: Client) -> APIClient:
    api = client._client  # noqa: SLF001 — PackageLicenseQuery has no facade
    if api is None:
        raise RuntimeError("Client has no API transport (closed?)")
    return api


def _is_http_404(exc: BaseException) -> bool:
    if isinstance(exc, NotFoundError):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code == 404
    return False


def create_package_license_query(
    client: Client,
    *,
    namespace: str,
    package_version_uuid: str,
) -> dict[str, Any] | None:
    """POST PackageLicenseQuery at *namespace* (catalog + overrides for that chain).

    Returns ``None`` when the API responds 404 (no license data for the PV).
    ``APIClient.post`` raises on 404 — catch that rather than inspecting status.
    """
    api = _api_transport(client)
    path = f"v1/namespaces/{namespace}/queries/package-license-queries"
    payload: dict[str, Any] = {
        "meta": {"name": f"license-export-{package_version_uuid[:12]}"},
        "spec": {"package_version_uuid": package_version_uuid},
    }
    try:
        response = api.post(path, json=payload)
    except Exception as exc:
        if _is_http_404(exc):
            return None
        raise
    if response.status_code == 404:
        return None
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, dict):
        raise TypeError("PackageLicenseQuery returned non-object JSON")
    return cast("dict[str, Any]", data)


def create_batch_package_license_query(
    client: Client,
    *,
    namespace: str,
    package_version_uuids: list[str],
) -> list[dict[str, Any]] | None:
    """POST BatchPackageLicenseQuery at *namespace*.

    Returns the evaluated ``spec.queries`` list, or ``None`` when the whole
    batch 404s (platform may 404 the batch if any PV has no license data —
    caller should fall back to per-PV Query).
    """
    if not package_version_uuids:
        return []
    api = _api_transport(client)
    path = f"v1/namespaces/{namespace}/queries/batch-package-license-queries"
    payload: dict[str, Any] = {
        "meta": {"name": f"license-export-batch-{len(package_version_uuids)}"},
        "spec": {
            "queries": [
                {
                    "meta": {"name": f"pv-{pv[:12]}"},
                    "spec": {"package_version_uuid": pv},
                }
                for pv in package_version_uuids
            ]
        },
    }
    try:
        response = api.post(path, json=payload)
    except Exception as exc:
        if _is_http_404(exc):
            return None
        raise
    if response.status_code == 404:
        return None
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, dict):
        raise TypeError("BatchPackageLicenseQuery returned non-object JSON")
    data_map = cast("dict[str, Any]", data)
    spec_obj = data_map.get("spec")
    spec = cast("dict[str, Any]", spec_obj) if isinstance(spec_obj, dict) else {}
    queries = spec.get("queries")
    if not isinstance(queries, list):
        raise TypeError("BatchPackageLicenseQuery missing spec.queries list")
    return [
        cast("dict[str, Any]", q)
        for q in cast("list[Any]", queries)
        if isinstance(q, dict)
    ]


def load_license_cache(path: Path) -> dict[str, dict[str, Any]]:
    """Load package_version_uuid → resolution dict from JSONL cache."""
    cache: dict[str, dict[str, Any]] = {}
    for data in load_jsonl_rows(path):
        pv = str(data.get("package_version_uuid") or "").strip()
        if pv:
            cache[pv] = data
    return cache


def load_license_objects(path: Path) -> dict[str, dict[str, Any]]:
    """Load package_version_uuid → full license object sidecar rows."""
    objects: dict[str, dict[str, Any]] = {}
    for data in load_jsonl_rows(path):
        pv = str(data.get("package_version_uuid") or "").strip()
        if pv:
            objects[pv] = data
    return objects


def _chunks(items: list[str], size: int) -> list[list[str]]:
    if size <= 0:
        raise ValueError("batch_size must be positive")
    return [items[i : i + size] for i in range(0, len(items), size)]


def _record_object(
    objects_store: JsonlKeyedStore | None,
    *,
    package_version_uuid: str,
    body: dict[str, Any],
) -> None:
    if objects_store is None:
        return
    objects_store.upsert(
        {
            "package_version_uuid": package_version_uuid,
            "source": "package_license_query",
            "license_object": body,
        }
    )


def _apply_query_body(
    *,
    package_version_uuid: str,
    body: dict[str, Any] | None,
    cache_store: JsonlKeyedStore,
    objects_store: JsonlKeyedStore | None,
) -> tuple[bool, bool]:
    """Upsert one resolution. Returns ``(has_primary_spdx, is_missing)``."""
    if body is None:
        cache_store.upsert(
            {"package_version_uuid": package_version_uuid, **empty_license_resolution()}
        )
        return False, True
    resolved = license_resolution_from_query(body)
    row: dict[str, Any] = {"package_version_uuid": package_version_uuid, **resolved}
    cache_store.upsert(row)
    _record_object(objects_store, package_version_uuid=package_version_uuid, body=body)
    if row.get("primary_spdx"):
        return True, False
    return False, True


def _query_one_pv(
    client: Client,
    *,
    namespace: str,
    package_version_uuid: str,
) -> tuple[str, dict[str, Any] | None, str | None]:
    try:
        body = create_package_license_query(
            client,
            namespace=namespace,
            package_version_uuid=package_version_uuid,
        )
        return package_version_uuid, body, None
    except Exception as exc:
        return package_version_uuid, None, f"{package_version_uuid}: {exc}"


def _resolve_chunk_individually(
    client: Client,
    *,
    namespace: str,
    package_version_uuids: list[str],
    cache_store: JsonlKeyedStore,
    objects_store: JsonlKeyedStore | None,
    max_workers: int,
) -> tuple[int, int, list[str]]:
    """Per-PV PackageLicenseQuery for a chunk; return hits, missing, errors."""
    errors: list[str] = []
    hits = 0
    missing = 0

    def _one(pv: str) -> tuple[str, dict[str, Any] | None, str | None]:
        return _query_one_pv(client, namespace=namespace, package_version_uuid=pv)

    for pv, body, err in parallel_over(
        package_version_uuids,
        _one,
        max_workers=max_workers,
    ):
        if err:
            errors.append(err)
            cache_store.upsert(
                {"package_version_uuid": pv, **empty_license_resolution()}
            )
            missing += 1
            continue
        has_spdx, is_missing = _apply_query_body(
            package_version_uuid=pv,
            body=body,
            cache_store=cache_store,
            objects_store=objects_store,
        )
        if has_spdx:
            hits += 1
        if is_missing:
            missing += 1
    return hits, missing, errors


def _resolve_via_queries(
    client: Client,
    *,
    namespace: str,
    pending: list[str],
    batch_size: int,
    cache_store: JsonlKeyedStore,
    objects_store: JsonlKeyedStore | None,
    max_workers: int,
) -> tuple[int, int, int, list[str]]:
    """Resolve *pending* PVs via batch Query with per-PV fallback on batch 404."""
    errors: list[str] = []
    hits = 0
    missing = 0
    queried = 0

    for batch in _chunks(pending, batch_size):
        queried += len(batch)
        try:
            queries = create_batch_package_license_query(
                client, namespace=namespace, package_version_uuids=batch
            )
        except Exception as exc:
            msg = f"BatchPackageLicenseQuery failed ({len(batch)} uuids): {exc}"
            errors.append(msg)
            LOGGER.warning("%s", msg)
            h, m, e = _resolve_chunk_individually(
                client,
                namespace=namespace,
                package_version_uuids=batch,
                cache_store=cache_store,
                objects_store=objects_store,
                max_workers=max_workers,
            )
            hits += h
            missing += m
            errors.extend(e)
            cache_store.flush()
            if objects_store is not None:
                objects_store.flush()
            continue

        if queries is None:
            # Whole-batch 404 (often when any PV lacks license data) → per-PV.
            h, m, e = _resolve_chunk_individually(
                client,
                namespace=namespace,
                package_version_uuids=batch,
                cache_store=cache_store,
                objects_store=objects_store,
                max_workers=max_workers,
            )
            hits += h
            missing += m
            errors.extend(e)
            cache_store.flush()
            if objects_store is not None:
                objects_store.flush()
            continue

        by_pv: dict[str, dict[str, Any]] = {}
        for item in queries:
            raw_spec = item.get("spec")
            spec: dict[str, Any] = (
                cast("dict[str, Any]", raw_spec) if isinstance(raw_spec, dict) else {}
            )
            pv = str(spec.get("package_version_uuid") or "").strip()
            if pv:
                by_pv[pv] = item

        for pv in batch:
            body = by_pv.get(pv)
            has_spdx, is_missing = _apply_query_body(
                package_version_uuid=pv,
                body=body,
                cache_store=cache_store,
                objects_store=objects_store,
            )
            if has_spdx:
                hits += 1
            if is_missing:
                missing += 1

        cache_store.flush()
        if objects_store is not None:
            objects_store.flush()

    return queried, hits, missing, errors


def resolve_licenses(
    client: Client,
    *,
    namespace: str,
    package_version_uuids: list[str],
    cache_path: str | Path,
    batch_size: int = DEFAULT_BATCH_SIZE,
    max_workers: int | None = None,
    overwrite: bool = False,
    include_license_object: bool = False,
    objects_path: str | Path | None = None,
) -> ResolveResult:
    """Resolve SPDX for PV UUIDs into a shared JSONL cache.

    Posts ``BatchPackageLicenseQuery`` / ``PackageLicenseQuery`` at *namespace*
    only (tenant plane). 404 means no license data for that PV → empty cache row.

    When *include_license_object* is true, also upsert full Query bodies into
    ``license_objects.jsonl`` (keyed by ``package_version_uuid``).
    """
    path = Path(cache_path)
    if overwrite and path.is_file():
        path.unlink()

    obj_path = (
        Path(objects_path)
        if objects_path is not None
        else path.parent / LICENSE_OBJECTS_FILENAME
    )
    if include_license_object and overwrite and obj_path.is_file():
        obj_path.unlink()

    cache_store = JsonlKeyedStore(path, LICENSE_CACHE_KEY_FIELDS)
    objects_store: JsonlKeyedStore | None = None
    if include_license_object:
        objects_store = JsonlKeyedStore(obj_path, LICENSE_OBJECTS_KEY_FIELDS)

    pending = [pv for pv in package_version_uuids if pv and cache_store.get(pv) is None]
    if not pending:
        return ResolveResult(
            status="success",
            message=f"License cache already covered {len(package_version_uuids)} PV(s)",
            cache_path=str(path),
            objects_path=str(obj_path) if include_license_object else "",
            resolved_count=len(package_version_uuids),
        )

    workers = resolve_collect_max_workers(max_workers)
    query_count, query_hits, missing, errors = _resolve_via_queries(
        client,
        namespace=namespace,
        pending=pending,
        batch_size=batch_size,
        cache_store=cache_store,
        objects_store=objects_store,
        max_workers=workers,
    )

    resolved_count = sum(
        1
        for pv in package_version_uuids
        if (cache_store.get(pv) or {}).get("primary_spdx")
    )
    if errors and resolved_count == 0:
        status = "error"
    elif errors:
        status = "partial"
    else:
        status = "success"

    return ResolveResult(
        status=status,
        message=(
            f"Resolved licenses: query_ok={query_hits}, "
            f"missing={missing}, errors={len(errors)}"
        ),
        errors=errors,
        cache_path=str(path),
        objects_path=str(obj_path) if include_license_object else "",
        resolved_count=resolved_count,
        query_count=query_count,
        consensus_count=0,
        missing_count=missing,
    )
