"""Server-side grouped DependencyMetadata list (``group_response`` pagination)."""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import TYPE_CHECKING, Any

from endorlabs.core.types import ListParameters
from endorlabs.operations import validate_namespace
from endorlabs.utils.logging_config import get_resource_logger

from .columns import PACKAGE_NAME_PATH, PACKAGE_VERSION_PATH

if TYPE_CHECKING:
    from endorlabs import Client

logger = get_resource_logger(__name__)


def grouped_count_list_parameters(*, page_size: int) -> ListParameters:
    """Grouped DependencyMetadata list for one namespace (never traverse)."""
    return ListParameters(
        traverse=False,
        page_size=page_size,
        group_aggregation_paths=[PACKAGE_NAME_PATH, PACKAGE_VERSION_PATH],
    )


def grouped_count_list_parameters_for_project(
    *,
    page_size: int,
    project_uuid: str,
) -> ListParameters:
    """Grouped list scoped to one project importer (tenant namespace path)."""
    return grouped_count_list_parameters(page_size=page_size).model_copy(
        update={"filter": f'spec.importer_data.project_uuid=="{project_uuid}"'}
    )


def grouped_count_list_parameters_for_importer_package_version(
    *,
    page_size: int,
    package_version_uuid: str,
) -> ListParameters:
    """Grouped list scoped to one importer PackageVersion (tenant namespace path)."""
    return grouped_count_list_parameters(page_size=page_size).model_copy(
        update={
            "filter": (
                f'spec.importer_data.package_version_uuid=="{package_version_uuid}"'
            )
        }
    )


def grouped_count_list_parameters_for_package_name(
    *,
    page_size: int,
    package_name: str,
    main_context: bool = False,
) -> ListParameters:
    """Grouped list for one exact ``package_name``, optionally main-context only."""
    pkg_filter = f'spec.dependency_data.package_name=="{package_name}"'
    if main_context:
        from endorlabs.workflows.estate.filters.main_context import main_context_filter

        filt = main_context_filter(pkg_filter)
    else:
        filt = pkg_filter
    return grouped_count_list_parameters(page_size=page_size).model_copy(
        update={"filter": filt}
    )


def parse_group_key(group_key: str) -> dict[str, str]:
    """Parse a group index key into ``{field_path: value}``."""
    try:
        payload = json.loads(group_key)
    except json.JSONDecodeError:
        return {"_raw": group_key}
    if not isinstance(payload, list):
        return {"_raw": group_key}
    parsed: dict[str, str] = {}
    for entry in payload:
        if isinstance(entry, dict) and "key" in entry and "value" in entry:
            parsed[str(entry["key"])] = str(entry["value"])
    return parsed


def count_from_wire(block: Any) -> int:
    """Extract integer count from ``count_response``-shaped wire JSON."""
    if not isinstance(block, dict):
        return 0
    raw = block.get("count")
    if raw is None:
        return 0
    return int(raw)


def iter_group_pages(
    client: Client,
    namespace: str,
    list_params: ListParameters,
    *,
    max_pages: int | None = None,
) -> Iterator[dict[str, Any]]:
    """Yield raw API JSON pages that contain ``group_response``."""
    ops = client.DependencyMetadata._ops  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
    wire_ns = validate_namespace(namespace)
    url = f"v1/namespaces/{wire_ns}/dependency-metadata"
    params = ops._build_params(list_params)  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
    page_id: str | None = None
    pages = 0

    while True:
        if max_pages is not None and pages >= max_pages:
            break
        request_params = dict(params)
        if page_id:
            request_params["list_parameters.page_id"] = page_id
        response = ops.client.get(url, params=request_params)
        data = response.json()
        if not isinstance(data, dict):
            break
        yield data
        pages += 1

        next_page_id: str | None = None
        list_block = data.get("list")
        if isinstance(list_block, dict):
            response_meta = list_block.get("response")
            if isinstance(response_meta, dict):
                raw_next = response_meta.get("next_page_id")
                if raw_next:
                    next_page_id = str(raw_next)
        if not next_page_id:
            break
        page_id = next_page_id

    logger.info("Fetched %s grouped page(s) for %s", pages, namespace)


def iter_group_buckets(
    client: Client,
    namespace: str,
    list_params: ListParameters,
    *,
    max_pages: int | None = None,
) -> Iterator[tuple[str, dict[str, Any]]]:
    """Yield ``(group_key, group_data)`` from grouped list pages."""
    for page in iter_group_pages(client, namespace, list_params, max_pages=max_pages):
        group_response = page.get("group_response")
        if not isinstance(group_response, dict):
            continue
        groups = group_response.get("groups")
        if not isinstance(groups, dict):
            continue
        for key, value in groups.items():
            if isinstance(value, dict):
                yield str(key), value
