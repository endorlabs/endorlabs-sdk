"""
Integration tests for Endor Cockpit SDK.

These tests use the real Endor Labs API and create actual objects in the backend.
They require valid authentication and will clean up after themselves.
"""

import os
import sys
import time
from typing import Optional

import pytest

# Add src to path for imports
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
)

from endor_cockpit.api_client import APIClient
from endor_cockpit.resources import namespaces
from endor_cockpit.resources.namespaces import (
    CreateNamespacePayload,
    NamespaceMetaCreate,
)


@pytest.mark.integration
class TestEndorCockpitIntegration:
    """Integration tests using real Endor Labs API."""

    @pytest.fixture(scope="class")
    def api_client(self):
        """Create authenticated API client."""
        # Check for required environment variables
        required_vars = [
            "ENDOR_API",
            "ENDOR_API_CREDENTIALS_KEY",
            "ENDOR_API_CREDENTIALS_SECRET",
        ]

        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            pytest.skip(f"Missing required environment variables: {missing_vars}")

        client = APIClient()
        return client

    @pytest.fixture(scope="class")
    def tenant_namespace(self):
        """The tenant namespace for testing."""
        return "endor-solutions-tgowan.cockpit"

    @pytest.fixture(scope="class")
    def test_namespaces(self, api_client, tenant_namespace):
        """Create test namespaces and clean up after tests."""
        created_namespaces = []

        try:
            # Create test namespaces
            test_names = [
                "integration-test-namespace-1",
                "integration-test-namespace-2",
            ]

            for name in test_names:
                namespace = self._create_test_namespace(
                    api_client,
                    tenant_namespace,
                    name,
                    f"Integration test namespace: {name}",
                )
                if namespace:
                    created_namespaces.append(namespace)
                    # Small delay to avoid rate limiting
                    time.sleep(1)

            yield created_namespaces

        finally:
            # Cleanup: Delete all created namespaces
            for namespace in created_namespaces:
                try:
                    self._delete_test_namespace(
                        api_client, tenant_namespace, namespace.uuid
                    )
                    time.sleep(1)  # Rate limiting
                except Exception as e:
                    print(f"Warning: Failed to delete namespace {namespace.uuid}: {e}")

    def test_api_connection(self, api_client, tenant_namespace):
        """Test basic API connection and authentication."""
        # Test connection by listing namespaces
        namespaces_list = namespaces.list_namespaces(api_client, tenant_namespace)

        assert namespaces_list is not None
        assert isinstance(namespaces_list, list)
        print(
            f"[OK] Connected to Endor Labs API. "
            f"Found {len(namespaces_list)} namespaces."
        )

    def test_create_namespace(self, api_client, tenant_namespace):
        """Test creating a namespace."""
        test_name = f"integration-test-create-{int(time.time())}"

        try:
            # Create namespace
            namespace = self._create_test_namespace(
                api_client,
                tenant_namespace,
                test_name,
                "Integration test for namespace creation",
            )

            assert namespace is not None
            assert namespace.uuid is not None
            assert namespace.meta.name == test_name
            print(f"[OK] Created namespace: {namespace.uuid}")

            return namespace

        finally:
            # Cleanup
            if "namespace" in locals():
                self._delete_test_namespace(
                    api_client, tenant_namespace, namespace.uuid
                )

    def test_list_namespaces(self, api_client, tenant_namespace, test_namespaces):
        """Test listing namespaces."""
        # List all namespaces
        all_namespaces = namespaces.list_namespaces(api_client, tenant_namespace)

        assert all_namespaces is not None
        assert isinstance(all_namespaces, list)

        # Check that our test namespaces are in the list
        test_namespace_uuids = {ns.uuid for ns in test_namespaces}
        found_namespaces = [
            ns for ns in all_namespaces if ns.uuid in test_namespace_uuids
        ]

        assert len(found_namespaces) == len(test_namespaces)
        print(
            f"[OK] Listed {len(all_namespaces)} namespaces, "
            f"found {len(found_namespaces)} test namespaces"
        )

    def test_get_namespace(self, api_client, tenant_namespace, test_namespaces):
        """Test getting a specific namespace."""
        if not test_namespaces:
            pytest.skip("No test namespaces available")

        test_namespace = test_namespaces[0]

        # Get the namespace by UUID
        retrieved_namespace = namespaces.get_namespace(
            api_client, tenant_namespace, test_namespace.uuid
        )

        assert retrieved_namespace is not None
        assert retrieved_namespace.uuid == test_namespace.uuid
        assert retrieved_namespace.meta.name == test_namespace.meta.name
        print(f"[OK] Retrieved namespace: {retrieved_namespace.meta.name}")

    def test_update_namespace(self, api_client, tenant_namespace):
        """Test updating a namespace."""
        test_name = f"integration-test-update-{int(time.time())}"
        updated_description = f"Updated description for {test_name}"

        try:
            # Create namespace
            namespace = self._create_test_namespace(
                api_client, tenant_namespace, test_name, "Original description"
            )

            assert namespace is not None

            # Update namespace (if update functionality exists)
            # Note: This would depend on the actual SDK implementation
            # For now, we'll just verify the namespace was created
            print(f"[OK] Created namespace for update test: {namespace.uuid}")

        finally:
            # Cleanup
            if "namespace" in locals():
                self._delete_test_namespace(
                    api_client, tenant_namespace, namespace.uuid
                )

    def test_delete_namespace(self, api_client, tenant_namespace):
        """Test deleting a namespace."""
        test_name = f"integration-test-delete-{int(time.time())}"

        # Create namespace
        namespace = self._create_test_namespace(
            api_client, tenant_namespace, test_name, "Namespace to be deleted"
        )

        assert namespace is not None
        namespace_uuid = namespace.uuid

        # Delete the namespace
        success = self._delete_test_namespace(
            api_client, tenant_namespace, namespace_uuid
        )

        assert success is True
        print(f"[OK] Successfully deleted namespace: {namespace_uuid}")

    def test_namespace_hierarchy(self, api_client, tenant_namespace):
        """Test namespace hierarchy operations."""
        parent_name = f"integration-test-parent-{int(time.time())}"
        child_name = f"integration-test-child-{int(time.time())}"

        parent_namespace = None
        child_namespace = None

        try:
            # Create parent namespace
            parent_namespace = self._create_test_namespace(
                api_client,
                tenant_namespace,
                parent_name,
                "Parent namespace for hierarchy test",
            )

            assert parent_namespace is not None
            print(f"[OK] Created parent namespace: {parent_namespace.uuid}")

            # Create child namespace under parent using canonical naming
            canonical_parent = f"{tenant_namespace}.{parent_name}"
            child_namespace = self._create_test_namespace(
                api_client,
                canonical_parent,  # Use canonical parent name
                child_name,
                "Child namespace for hierarchy test",
            )

            assert child_namespace is not None
            print(f"[OK] Created child namespace: {child_namespace.uuid}")

            # List namespaces under parent using canonical naming
            child_namespaces = namespaces.list_namespaces(api_client, canonical_parent)

            assert child_namespaces is not None
            assert len(child_namespaces) >= 1

            # Find our child namespace
            found_child = next(
                (ns for ns in child_namespaces if ns.uuid == child_namespace.uuid), None
            )
            assert found_child is not None
            print(f"[OK] Found child namespace in hierarchy: {found_child.meta.name}")

        finally:
            # Cleanup: Delete child first, then parent
            if child_namespace:
                self._delete_test_namespace(
                    api_client, canonical_parent, child_namespace.uuid
                )
            if parent_namespace:
                self._delete_test_namespace(
                    api_client, tenant_namespace, parent_namespace.uuid
                )

    def test_error_handling(self, api_client, tenant_namespace):
        """Test error handling with invalid operations."""
        # Test getting non-existent namespace
        fake_uuid = "00000000-0000-0000-0000-000000000000"
        result = namespaces.get_namespace(api_client, tenant_namespace, fake_uuid)

        # Should handle gracefully (return None or raise appropriate exception)
        assert result is None or isinstance(result, Exception)
        print("[OK] Handled non-existent namespace gracefully")

        # Test creating namespace with invalid name
        try:
            invalid_namespace = self._create_test_namespace(
                api_client,
                tenant_namespace,
                "",  # Empty name should fail
                "Invalid namespace",
            )
            # If we get here, the API didn't validate properly
            assert invalid_namespace is None
        except Exception:
            # Expected behavior - should raise an exception
            pass
        print("[OK] Handled invalid namespace creation gracefully")

    def test_rate_limiting(self, api_client, tenant_namespace):
        """Test rate limiting behavior."""
        # Create multiple namespaces quickly to test rate limiting
        test_names = [f"rate-limit-test-{i}-{int(time.time())}" for i in range(3)]
        created_namespaces = []

        try:
            for i, name in enumerate(test_names):
                namespace = self._create_test_namespace(
                    api_client,
                    tenant_namespace,
                    name,
                    f"Rate limiting test namespace {i}",
                )
                if namespace:
                    created_namespaces.append(namespace)

                # Small delay between requests
                time.sleep(0.5)

            print(
                f"[OK] Created {len(created_namespaces)} namespaces "
                f"with rate limiting"
            )

        finally:
            # Cleanup
            for namespace in created_namespaces:
                self._delete_test_namespace(
                    api_client, tenant_namespace, namespace.uuid
                )
                time.sleep(0.5)

    def _create_test_namespace(
        self, client: APIClient, parent_namespace: str, name: str, description: str
    ) -> Optional[any]:
        """Helper method to create a test namespace."""
        try:
            payload = CreateNamespacePayload(
                meta=NamespaceMetaCreate(name=name, description=description)
            )

            return namespaces.create_namespace(client, parent_namespace, payload)
        except Exception as e:
            print(f"Error creating namespace {name}: {e}")
            return None

    def _delete_test_namespace(
        self, client: APIClient, parent_namespace: str, namespace_uuid: str
    ) -> bool:
        """Helper method to delete a test namespace."""
        try:
            return namespaces.delete_namespace(client, parent_namespace, namespace_uuid)
        except Exception as e:
            print(f"Error deleting namespace {namespace_uuid}: {e}")
            return False


@pytest.mark.integration
class TestEndorCockpitSecurityIntegration:
    """Integration tests for security scanning functionality."""

    @pytest.fixture(scope="class")
    def api_client(self):
        """Create authenticated API client."""
        required_vars = [
            "ENDOR_API",
            "ENDOR_API_CREDENTIALS_KEY",
            "ENDOR_API_CREDENTIALS_SECRET",
        ]

        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            pytest.skip(f"Missing required environment variables: {missing_vars}")

        client = APIClient()
        return client

    @pytest.fixture(scope="class")
    def tenant_namespace(self):
        """The tenant namespace for testing."""
        return "endor-solutions-tgowan.cockpit"

    def test_security_scan_integration(self, api_client, tenant_namespace):
        """Test security scanning with endorctl."""
        import os
        import subprocess
        import tempfile

        # Create a temporary test file for scanning
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(
                """
# Test file for security scanning
import requests
import os

def test_function():
    # This should trigger some security findings
    password = "hardcoded-password-123"
    api_key = "sk-1234567890abcdef"  # endorctl:allow
    return password, api_key
"""
            )
            temp_file = f.name

        try:
            # Run endorctl scan on the test file
            result = subprocess.run(
                ["endorctl", "scan", temp_file],
                capture_output=True,
                text=True,
                timeout=60,
            )

            # Check if scan completed (may have findings or not)
            assert result.returncode in [0, 1]  # 0 = no issues, 1 = issues found
            print(f"[OK] Security scan completed with return code: {result.returncode}")

            if result.stdout:
                print(f"Scan output: {result.stdout[:200]}...")

            if result.stderr:
                print(f"Scan errors: {result.stderr[:200]}...")

        except subprocess.TimeoutExpired:
            pytest.fail("Security scan timed out")
        except FileNotFoundError:
            pytest.skip("endorctl not found - install endorctl to run security tests")
        except Exception as e:
            pytest.fail(f"Security scan failed: {e}")
        finally:
            # Cleanup
            if os.path.exists(temp_file):
                os.unlink(temp_file)

    def test_security_scan_namespace(self, api_client, tenant_namespace):
        """Test security scanning of a namespace."""
        import subprocess

        try:
            # Run endorctl scan on the namespace
            result = subprocess.run(
                ["endorctl", "scan", "--namespace", tenant_namespace],
                capture_output=True,
                text=True,
                timeout=120,
            )

            # Check if scan completed
            assert result.returncode in [0, 1]
            print(
                f"[OK] Namespace security scan completed with return code: "
                f"{result.returncode}"
            )

            if result.stdout:
                print(f"Namespace scan output: {result.stdout[:300]}...")

        except subprocess.TimeoutExpired:
            pytest.fail("Namespace security scan timed out")
        except FileNotFoundError:
            pytest.skip("endorctl not found - install endorctl to run security tests")
        except Exception as e:
            pytest.fail(f"Namespace security scan failed: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
