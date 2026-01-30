"""Test cases for SemgrepRule resource operations.

Tests list, get, and Client-recommended UX for SemgrepRule resources.
Aligns with test-driven-development.mdc and resource-implementation.md.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import conftest

from endorlabs.api_client import APIClient
from endorlabs.resources import semgrep_rule
from endorlabs.types import ListParameters


@pytest.mark.integration
class TestSemgrepRule:
    """Test cases for SemgrepRule resource operations."""

    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        """Set up test environment."""
        self.client = APIClient(
            max_retries=2, backoff_factor=0.1, auth_method="api-key"
        )
        self.namespace = os.getenv("ENDOR_NAMESPACE", conftest.TEST_NAMESPACE_DEFAULT)

        if not self.namespace:
            pytest.skip("ENDOR_NAMESPACE environment variable must be set")

        self.created_semgrep_rule_uuids: list[str] = []

    def teardown_method(self) -> None:
        """Clean up any semgrep rules created during tests."""
        if hasattr(self, "created_semgrep_rule_uuids"):
            for rule_uuid in self.created_semgrep_rule_uuids:
                try:
                    semgrep_rule.delete_semgrep_rule(
                        self.client, self.namespace, rule_uuid
                    )
                except Exception as e:
                    print(f"[WARNING] Failed to delete semgrep rule {rule_uuid}: {e}")
            self.created_semgrep_rule_uuids.clear()

    def test_semgrep_rule_list(self) -> None:
        """Test GET semgrep rules (list) with pagination limits."""
        rules = semgrep_rule.list_semgrep_rules(
            self.client,
            self.namespace,
            list_params=ListParameters(page_size=conftest.TEST_PAGE_SIZE),
            max_pages=2,
        )
        assert isinstance(rules, list)

    def test_semgrep_rule_get_by_uuid(self) -> None:
        """Test GET semgrep rule by UUID when at least one rule exists."""
        rules = semgrep_rule.list_semgrep_rules(
            self.client,
            self.namespace,
            list_params=ListParameters(page_size=1),
            max_pages=1,
        )
        if not rules:
            pytest.skip("No resources in scope (empty; may be filter/auth/scope)")

        rule = semgrep_rule.get_semgrep_rule(self.client, self.namespace, rules[0].uuid)
        assert rule is not None
        assert rule.uuid == rules[0].uuid

    def test_client_recommended_ux_list_semgrep_rules(self) -> None:
        """Recommended UX: Client(tenant=...); client.semgrep_rules.list()."""
        import endorlabs

        client = endorlabs.Client(
            tenant=self.namespace,
            max_retries=2,
            backoff_factor=0.1,
            auth_method="api-key",
        )
        rules = client.semgrep_rules.list(max_pages=1)
        assert isinstance(rules, list)
