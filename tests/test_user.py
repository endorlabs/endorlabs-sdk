"""
Test cases for User resource operations.

Tests GET operations for User resources.
Users are read-only resources managed by identity providers.
"""

import os
import sys

import pytest

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from endor_cockpit.api_client import APIClient
from endor_cockpit.resources import user
from endor_cockpit.types import ListParameters


@pytest.mark.integration
class TestUser:
    """Test cases for User resource operations."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test environment."""
        self.client = APIClient()
        self.namespace = os.getenv("ENDOR_NAMESPACE", "")

        # Validate namespace is set
        if not self.namespace:
            pytest.skip("ENDOR_NAMESPACE environment variable must be set")

        # Get test data - use parent namespace to access child resources
        parts = self.namespace.split(".")
        self.parent_namespace = parts[0] if len(parts) > 1 else self.namespace

        # List users from parent namespace to get available data
        import conftest

        self.users = user.list_users(
            self.client,
            self.parent_namespace,
            list_params=ListParameters(page_size=conftest.TEST_PAGE_SIZE),
        )
        if not self.users:
            pytest.skip("No users available for testing")

    def test_user_list(self):
        """Test LIST users operation."""
        print("\n=== TESTING LIST USERS ===")

        # Test list_users
        users_list = user.list_users(self.client, self.parent_namespace)
        assert isinstance(users_list, list), "Should return a list of users"
        assert len(users_list) > 0, "Should have at least one user"

        print(f"Found {len(users_list)} users")

        # Display first few users
        for _i, user_item in enumerate(users_list[:5]):
            print(
                f"User {user_item.uuid}: "
                f"{user_item.meta.name if user_item.meta else 'N/A'}"
            )
            if user_item.spec:
                if user_item.spec.user_name:
                    print(f"  Username: {user_item.spec.user_name}")
                if user_item.spec.email:
                    print(f"  Email: {user_item.spec.email}")
                if user_item.spec.first_name:
                    print(f"  First name: {user_item.spec.first_name}")
                if user_item.spec.last_name:
                    print(f"  Last name: {user_item.spec.last_name}")

    def test_user_get_by_uuid(self):
        """Test GET user by UUID operation."""
        print("\n=== TESTING GET USER BY UUID ===")

        user_item = self.users[0]
        retrieved_user = user.get_user(
            self.client, self.parent_namespace, user_item.uuid
        )

        assert retrieved_user is not None, (
            "Should successfully retrieve user by UUID"
        )
        assert retrieved_user.uuid == user_item.uuid, (
            "Retrieved user should match original"
        )
        if retrieved_user.meta and user_item.meta:
            assert retrieved_user.meta.name == user_item.meta.name, (
                "User name should match"
            )

        print(f"Successfully retrieved user: {retrieved_user.uuid}")
        if retrieved_user.meta:
            print(f"User name: {retrieved_user.meta.name}")
        if retrieved_user.spec:
            if retrieved_user.spec.user_name:
                print(f"Username: {retrieved_user.spec.user_name}")
            if retrieved_user.spec.email:
                print(f"Email: {retrieved_user.spec.email}")

    def test_user_with_traverse(self):
        """Test listing users with traverse (child namespaces)."""
        print("\n=== TESTING LIST USERS WITH TRAVERSE ===")

        # List with traverse enabled
        list_params = ListParameters(traverse=True)

        users_list = user.list_users(self.client, self.parent_namespace, list_params)

        assert isinstance(users_list, list), "Should return a list of users"
        print(f"Found {len(users_list)} users (with traverse)")

    def test_user_field_validation(self):
        """Test field validation and required fields."""
        user_item = self.users[0]

        # Verify required fields are present
        assert user_item.uuid is not None
        assert user_item.meta is not None
        assert user_item.meta.name is not None
        assert user_item.spec is not None

        # Note: spec fields may be None for some users
        # This is expected as user data comes from identity providers

    def test_user_pagination(self):
        """Test pagination capabilities."""
        # Test with page size
        paginated_results = user.list_users(
            self.client,
            self.parent_namespace,
            list_params=ListParameters(page_size=5, sort_order="asc"),
        )
        assert isinstance(paginated_results, list)
        assert len(paginated_results) > 0

    def test_user_error_handling(self):
        """Test error handling for invalid UUID."""
        # Test with invalid UUID
        invalid_user = user.get_user(
            self.client, self.parent_namespace, "invalid-uuid"
        )
        assert invalid_user is None

    def test_user_event_tracking(self):
        """Test user event tracking data structure."""
        users_list = user.list_users(self.client, self.parent_namespace)

        users_with_events = 0
        for u in users_list:
            if u.spec and u.spec.event_tracking:
                users_with_events += 1
                print(f"\nUser {u.uuid} has event tracking:")
                for event_type, event_data in u.spec.event_tracking.items():
                    print(f"  {event_type}: {event_data.count} occurrences")

        print(f"\nFound {users_with_events} users with event tracking data")
        assert len(users_list) > 0

