"""Shared fixtures for facade helper integration tests."""

from __future__ import annotations

import pytest

import endorlabs
from endorlabs.core.exceptions import ServerError
from tests.conftest import TEST_MAX_PAGES
from tests.integration.client.helper_assertions import nested_attr

# Registry scope is ``tenant`` (OpenAPI exposes both tenant and oss paths), but OSS
# catalog PackageLicense rows live under the literal ``oss`` namespace on the wire.
OSS_NAMESPACE = "oss"
OSS_PLANE_PROBE_KINDS = frozenset({"PackageLicense"})


@pytest.fixture
def facade_client(api_client, namespace):
    """Client scoped to the integration namespace."""
    return endorlabs.Client(tenant=namespace, api_client=api_client)


@pytest.fixture
def facade_root_client(api_client, root_namespace):
    """Client scoped to tenant root (traverse-friendly reads)."""
    return endorlabs.Client(tenant=root_namespace, api_client=api_client)


@pytest.fixture
def facade_oss_client(api_client):
    """Client targeting the literal ``oss`` namespace path (catalog plane)."""
    return endorlabs.Client(tenant=OSS_NAMESPACE, api_client=api_client)


def require_first_project(client, *, max_pages: int = TEST_MAX_PAGES):
    """Return first project in scope or skip."""
    try:
        projects = client.Project.list(max_pages=max_pages)
    except ServerError as err:
        pytest.skip(f"Project list unavailable: {err}")
    if not projects:
        pytest.skip("No projects in scope")
    return projects[0]


def _list_rows(client, list_method: str) -> list[object]:
    try:
        return getattr(client, list_method).list(max_pages=TEST_MAX_PAGES)
    except ServerError:
        return []


def _clients_for_list_probe(
    client,
    list_method: str,
    *,
    root_client=None,
    oss_client=None,
) -> list[object]:
    """Clients to probe for list rows (tenant leaf/root plus oss when applicable)."""
    clients: list[object] = [client]
    if root_client is not None and root_client is not client:
        clients.append(root_client)
    if (
        list_method in OSS_PLANE_PROBE_KINDS
        and oss_client is not None
        and oss_client not in clients
    ):
        clients.append(oss_client)
    return clients


def resource_has_rows_in_scope(
    client,
    list_method: str,
    *,
    root_client=None,
    oss_client=None,
) -> bool:
    """True when plain list finds rows in tenant and/or oss probe scope."""
    for cl in _clients_for_list_probe(
        client, list_method, root_client=root_client, oss_client=oss_client
    ):
        if _list_rows(cl, list_method):
            return True
    return False


def _scan_has_context(scan: object) -> bool:
    ctx = getattr(scan, "context", None)
    return ctx is not None and bool(getattr(ctx, "type", None))


def _context_matches(left: object, right: object) -> bool:
    if getattr(left, "type", None) != getattr(right, "type", None):
        return False
    left_id = getattr(left, "id", None)
    if left_id:
        return getattr(right, "id", None) == left_id
    return True


def _project_scans(client, project: object, *, limit: int = 10) -> list[object]:
    """Bounded scan list for a project (single page — avoids sort/page_id conflict)."""
    try:
        route = client.ScanResult.list_by_project(project, limit=limit, max_pages=1)
    except ServerError:
        return []
    return list(route.values or [])


def _sample_from_row_context(
    client,
    list_method: str,
    edge_id: str,
    *,
    root_client=None,
    oss_client=None,
) -> tuple[object, object, object] | None:
    """Locate scan plane via an existing row's context + project linkage."""
    for cl in _clients_for_list_probe(
        client, list_method, root_client=root_client, oss_client=oss_client
    ):
        facade = getattr(cl, list_method)
        rows = _list_rows(cl, list_method)
        if not rows:
            continue
        row = rows[0]
        row_ctx = getattr(row, "context", None)
        if not _scan_has_context(row_ctx):
            continue
        project_uuid = nested_attr(row, "spec.project_uuid") or nested_attr(
            row, "meta.parent_uuid"
        )
        if not project_uuid:
            continue
        ns = nested_attr(row, "tenant_meta.namespace") or getattr(
            cl, "_default_namespace", None
        )
        try:
            project = cl.Project.get(str(project_uuid), namespace=ns)
        except Exception:
            continue
        for scan in _project_scans(cl, project):
            if not _scan_has_context(scan):
                continue
            if not _context_matches(row_ctx, scan.context):
                continue
            try:
                result = facade.list_for_context(scan, max_pages=TEST_MAX_PAGES)
            except ServerError:
                continue
            if result.edge_used == edge_id and result.values:
                return project, scan, result
    return None


def _sample_from_scan_probe(
    client,
    list_method: str,
    edge_id: str,
    *,
    root_client=None,
    oss_client=None,
    max_projects: int = 5,
    scans_per_project: int = 10,
) -> tuple[object, object, object] | None:
    """Probe projects/scans until list_for_context returns rows."""
    for cl in _clients_for_list_probe(
        client, list_method, root_client=root_client, oss_client=oss_client
    ):
        facade = getattr(cl, list_method)
        try:
            projects = cl.Project.list(max_pages=max_projects)
        except ServerError:
            continue
        for project in projects:
            for scan in _project_scans(cl, project, limit=scans_per_project):
                if not _scan_has_context(scan):
                    continue
                try:
                    result = facade.list_for_context(scan, max_pages=TEST_MAX_PAGES)
                except ServerError:
                    continue
                if result.edge_used == edge_id and result.values:
                    return project, scan, result
    return None


def require_list_for_context_sample(
    client,
    list_method: str,
    edge_id: str,
    *,
    root_client=None,
    oss_client=None,
) -> tuple[object, object, object]:
    """Return (project, scan, route_result) with non-empty list_for_context values.

    Skip only when plain LIST is empty across tenant and oss probe clients.
    Fail when rows exist but no scan plane could be resolved.
    """
    sample = _sample_from_row_context(
        client,
        list_method,
        edge_id,
        root_client=root_client,
        oss_client=oss_client,
    )
    if sample is None:
        sample = _sample_from_scan_probe(
            client,
            list_method,
            edge_id,
            root_client=root_client,
            oss_client=oss_client,
        )
    if sample is not None:
        return sample
    if not resource_has_rows_in_scope(
        client, list_method, root_client=root_client, oss_client=oss_client
    ):
        scope_note = (
            " (including oss namespace probe)"
            if list_method in OSS_PLANE_PROBE_KINDS
            else ""
        )
        pytest.skip(
            f"No {list_method} rows in integration scope{scope_note}; "
            f"list_for_context({edge_id}) not applicable"
        )
    pytest.fail(
        f"{list_method} rows exist but list_for_context({edge_id!r}) "
        f"returned no rows for any probed scan plane — check route wiring or probes"
    )


def require_scan_with_context(client, project):
    """Return (project, scan) preferring a scan whose plane has listable context."""
    for scan in _project_scans(client, project):
        if _scan_has_context(scan):
            return project, scan
    pytest.skip("No scan with usable context partition for project")
