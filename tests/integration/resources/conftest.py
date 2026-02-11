"""Shared fixtures for resource integration tests.

Provides ResourceTestBase — a mixin that standardises the
api_client / namespace / root_namespace / created_uuids / teardown
pattern repeated across 25+ resource test files.
"""

import pytest


class ResourceTestBase:
    """Mixin for resource integration tests with standard setup/teardown.

    Subclasses inherit the autouse ``setup_resource`` fixture which wires
    ``self.client``, ``self.namespace``, ``self.root_namespace`` and a
    ``self.created_uuids`` list. Override ``_cleanup()`` to delete resources
    created during a test.
    """

    created_uuids: list[str]

    @pytest.fixture(autouse=True)
    def setup_resource(self, api_client, namespace, root_namespace):
        """Wire common integration-test state and call _cleanup on teardown."""
        self.client = api_client
        self.namespace = namespace
        self.root_namespace = root_namespace
        self.created_uuids = []
        yield
        self._cleanup()

    def _cleanup(self) -> None:
        """Override in subclasses to delete resources created during the test."""
