import os
import sys
import time

import pytest

# Ensure src/ is on sys.path for direct import
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
)
from endor_cockpit.api_client import APIClient
from endor_cockpit.resources.namespace import (
    CreateNamespacePayload,
    NamespaceMetaCreate,
    create_namespace,
    delete_namespace,
    list_namespaces,
)


@pytest.mark.integration
def test_namespaces_main_flow():
    # Check for required environment variables
    required_vars = [
        "ENDOR_API",
        "ENDOR_API_CREDENTIALS_KEY",
        "ENDOR_API_CREDENTIALS_SECRET",
    ]

    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        pytest.skip(f"Missing required environment variables: {missing_vars}")

    # Setup APIClient
    client = APIClient(max_retries=2, backoff_factor=0.1, auth_method="api-key")
    tenant_namespace = os.getenv("ENDOR_NAMESPACE", "endor-solutions-tgowan.tgowan-endor")
    if not tenant_namespace:
        pytest.skip("ENDOR_NAMESPACE environment variable must be set")
    # Create mock namespaces
    # Use timestamp and random ID to ensure unique names
    import random

    timestamp = int(time.time())
    random_id = random.randint(1000, 9999)
    mock_namespaces_to_create = [
        CreateNamespacePayload(
            meta=NamespaceMetaCreate(
                name=f"mock-namespace-{timestamp}-{random_id}-{i}",
                description=(
                    f"Description for mock-namespace-{timestamp}-{random_id}-{i}"
                ),
            )
        )
        for i in range(2)
    ]
    created_uuids = []
    for payload in mock_namespaces_to_create:
        try:
            ns = create_namespace(client, tenant_namespace, payload)
            if ns:
                created_uuids.append(ns.uuid)
        except Exception as e:
            print(f"Warning: Failed to create namespace {payload.meta.name}: {e}")
            # Continue with other namespaces
    # List and check created
    import conftest

    from endor_cockpit.types import ListParameters

    all_namespaces = list_namespaces(
        client,
        tenant_namespace,
        list_params=ListParameters(page_size=conftest.TEST_PAGE_SIZE),
        max_pages=conftest.TEST_MAX_PAGES,
    )
    mock_names = {p.meta.name for p in mock_namespaces_to_create}
    found = [ns for ns in all_namespaces if ns.meta.name in mock_names]
    # Assert that at least one namespace was created successfully
    expected_msg = (
        f"Expected at least 1 namespace, found {len(found)}. "
        f"Created UUIDs: {created_uuids}"
    )
    assert len(found) >= 1, expected_msg
    # Delete created
    for ns in found:
        assert delete_namespace(client, tenant_namespace, ns.uuid)
