import os
import sys
import tempfile

import pytest

# Ensure src/ is on sys.path for direct import
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
)
from endor_cockpit.api_client import APIClient
from endor_cockpit.resources.namespaces import (
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
    client = APIClient(max_retries=2, backoff_factor=0.1)
    # Get OpenAPI spec and store in a temp file
    with tempfile.TemporaryDirectory() as tmpdir:
        spec_path = os.path.join(tmpdir, "openapiv2.swagger.json")
        try:
            client.get_openapi_spec(url=None, path=spec_path)
        except Exception as e:
            pytest.skip(f"Could not fetch OpenAPI spec: {e}")
        tenant_namespace = "endor-solutions-tgowan.cockpit"
        # Create mock namespaces
        mock_namespaces_to_create = [
            CreateNamespacePayload(
                meta=NamespaceMetaCreate(
                    name=f"mock-namespace-{i}",
                    description=f"Description for mock-namespace-{i}",
                )
            )
            for i in range(2)
        ]
        created_uuids = []
        for payload in mock_namespaces_to_create:
            ns = create_namespace(client, tenant_namespace, payload)
            if ns:
                created_uuids.append(ns.uuid)
        # List and check created
        all_namespaces = list_namespaces(client, tenant_namespace)
        mock_names = {p.meta.name for p in mock_namespaces_to_create}
        found = [ns for ns in all_namespaces if ns.meta.name in mock_names]
        assert len(found) == len(mock_namespaces_to_create)
        # Delete created
        for ns in found:
            assert delete_namespace(client, tenant_namespace, ns.uuid)
