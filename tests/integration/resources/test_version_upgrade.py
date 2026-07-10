"""Tests for VersionUpgrade resource operations."""

import pytest


@pytest.mark.integration
class TestVersionUpgrade:
    """Test cases for VersionUpgrade resource operations."""

    @pytest.fixture(autouse=True)
    def setup(self, api_client, namespace, root_namespace) -> None:
        """Set up test environment."""
        self.client = api_client
        self.namespace = namespace
        self.root_namespace = root_namespace
        import endorlabs

        self.endor_client = endorlabs.Client(tenant=namespace, api_client=api_client)

    def test_version_upgrade_create_raises_not_implemented(self) -> None:
        """Create is not supported; raises NotImplementedError."""
        with pytest.raises(NotImplementedError, match="does not support create"):
            self.endor_client.VersionUpgrade.create({})
