"""Parametrized list → get roundtrip integration harness.

Replaces per-resource boilerplate ``test_*_list`` / ``test_*_get`` functions
with a single registry-driven parametrized suite.  Resources that need unique
assertions (PATCH, CRUD, special namespaces, log-style pagination) retain
explicit tests in their own files.

Resources included here satisfy ALL of:
- Standard namespace scope via the ``endor_client`` fixture (tenant namespace).
- ``.list(max_pages=TEST_MAX_PAGES)`` returns a plain list (no log-style helpers).
- ``.get(item)`` performs a normal uuid roundtrip (no expected 403 / system scope).
- No in-list filter assertions beyond ``isinstance(result, list)``.

Excluded resources and why:
- AuditLog / FindingLog / AuthenticationLog — log-style bounded pagination.
- EndorLicense / PolicyTemplate              — get raises 403 (system-scoped).
- Installation                               — requires traverse=True root client.
- PackageLicense / Vulnerability / Malware   — OSS catalog namespace.
- ScanLogRequest / VectorStoreQuery          — create-only (no standard list/get).
"""

from __future__ import annotations

import pytest

from endorlabs.core.exceptions import NotFoundError, ServerError
from tests.conftest import TEST_MAX_PAGES

# ---------------------------------------------------------------------------
# Registry: resource kinds with standard list → get behaviour.
# Each entry is the PascalCase ``client.<Kind>`` attribute name.
# ---------------------------------------------------------------------------
_RESOURCE_KINDS: list[str] = [
    "APIKey",
    "AuthorizationPolicy",
    "CodeOwners",
    "Finding",
    "Invitation",
    "LinterResult",
    "Metric",
    "Namespace",
    "NotificationTarget",
    "PackageVersion",
    "Policy",
    "PRCommentConfig",
    "Project",
    "Repository",
    "RepositoryVersion",
    "ScanProfile",
    "ScanResult",
    "ScanWorkflow",
    "ScanWorkflowResult",
    "SemgrepRule",
    "VectorStore",
    "VersionUpgrade",
]


@pytest.mark.integration
@pytest.mark.parametrize("kind", _RESOURCE_KINDS)
def test_resource_list(kind: str, endor_client) -> None:
    """LIST returns a list for each registered resource kind."""
    facade = getattr(endor_client, kind)
    try:
        result = facade.list(max_pages=TEST_MAX_PAGES)
    except NotFoundError:
        pytest.skip("List returned 404 (namespace not accessible or resource absent)")
    except ServerError:
        pytest.skip("Backend returned ServerError (list); skip")
    assert isinstance(result, list)


@pytest.mark.integration
@pytest.mark.parametrize("kind", _RESOURCE_KINDS)
def test_resource_get(kind: str, endor_client) -> None:
    """GET first item from LIST and verify uuid roundtrip."""
    facade = getattr(endor_client, kind)
    try:
        items = facade.list(max_pages=TEST_MAX_PAGES)
    except NotFoundError:
        pytest.skip("List returned 404 (namespace not accessible or resource absent)")
    except ServerError:
        pytest.skip("Backend returned ServerError (list); skip")
    if not items:
        pytest.skip("No resources in scope (empty; may be filter/auth/scope)")
    item = items[0]
    try:
        got = facade.get(item)
    except NotFoundError:
        pytest.skip("Get returned 404 after list succeeded")
    except ServerError:
        pytest.skip("Backend returned ServerError (get); skip")
    assert got is not None
    assert got.uuid == item.uuid
