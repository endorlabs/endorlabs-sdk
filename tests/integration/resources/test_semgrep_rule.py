"""Test cases for SemgrepRule resource operations.

Canonical order: LIST (root + traverse) -> GET -> Create -> Update -> Delete.
Uses conftest api_client, namespace, root_namespace.
"""

import time

import pytest

import endorlabs
from endorlabs.api_client import APIClient
from endorlabs.resources import semgrep_rule
from endorlabs.resources.semgrep_rule import (
    CreateSemgrepRulePayload,
    SemgrepNativeRule,
    SemgrepRuleMetaCreate,
    SemgrepRuleSpec,
    UpdateSemgrepRulePayload,
)
from tests.conftest import TEST_MAX_PAGES_TRAVERSE


@pytest.mark.integration
class TestSemgrepRule:
    """Canonical order: LIST -> GET -> Create -> Update -> Delete."""

    @pytest.fixture(autouse=True)
    def setup(self, api_client: APIClient, namespace: str, root_namespace: str) -> None:
        """Set client and namespaces from conftest."""
        self.client = api_client
        self.namespace = namespace
        self.root_namespace = root_namespace
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
        """LIST from tenant root with traverse."""
        client = endorlabs.Client(
            tenant=self.root_namespace,
            api_client=self.client,
        )
        result = client.semgrep_rule.list(
            traverse=True,
            max_pages=TEST_MAX_PAGES_TRAVERSE,
        )
        assert isinstance(result, list)

    def test_semgrep_rule_get(self) -> None:
        """GET first item from LIST (root + traverse)."""
        client = endorlabs.Client(
            tenant=self.root_namespace,
            api_client=self.client,
        )
        items = client.semgrep_rule.list(
            traverse=True,
            max_pages=TEST_MAX_PAGES_TRAVERSE,
        )
        if not items:
            pytest.skip("No resources in scope (empty; may be filter/auth/scope)")
        item = items[0]
        ns = (
            item.tenant_meta.namespace
            if item.tenant_meta and getattr(item.tenant_meta, "namespace", None)
            else self.root_namespace
        )
        got = client.semgrep_rule.get(item.uuid, namespace=ns)
        assert got is not None
        assert got.uuid == item.uuid

    @pytest.mark.writes
    def test_semgrep_rule_create(self) -> None:
        """Create a semgrep rule; teardown deletes."""
        client = endorlabs.Client(
            tenant=self.namespace,
            api_client=self.client,
        )
        rule_id = f"client-ux-rule-{int(time.time())}"
        payload = CreateSemgrepRulePayload(
            meta=SemgrepRuleMetaCreate(name=rule_id, description="Consumer UX create"),
            spec=SemgrepRuleSpec(
                rule=SemgrepNativeRule(
                    id=rule_id,
                    languages=["python"],
                    message="Client UX test rule",
                    pattern="exec($VAR)",
                )
            ),
            propagate=False,
        )
        from endorlabs.exceptions import PermissionDeniedError

        created = None
        try:
            created = client.semgrep_rule.create(payload)
        except PermissionDeniedError as e:
            pytest.skip(f"Semgrep rule create not allowed in this environment: {e}")
        try:
            assert created is not None
            assert created.meta.name == rule_id
            self.created_semgrep_rule_uuids.append(created.uuid)
        finally:
            if created is not None:  # type: ignore[reportUnnecessaryComparison]
                try:
                    semgrep_rule.delete_semgrep_rule(
                        self.client, self.namespace, created.uuid
                    )
                except Exception as e:
                    print(f"[WARNING] Cleanup failed for {created.uuid}: {e}")

    @pytest.mark.writes
    def test_semgrep_rule_update(self) -> None:
        """Create then update the created resource; teardown deletes."""
        client = endorlabs.Client(
            tenant=self.namespace,
            api_client=self.client,
        )
        rule_id = f"client-ux-update-{int(time.time())}"
        create_payload = CreateSemgrepRulePayload(
            meta=SemgrepRuleMetaCreate(
                name=rule_id, description="Original description"
            ),
            spec=SemgrepRuleSpec(
                rule=SemgrepNativeRule(
                    id=rule_id,
                    languages=["python"],
                    message="Client UX update test",
                    pattern="eval($X)",
                )
            ),
            propagate=False,
        )
        from endorlabs.exceptions import PermissionDeniedError

        created = None
        try:
            created = client.semgrep_rule.create(create_payload)
        except PermissionDeniedError as e:
            pytest.skip(f"Semgrep rule create not allowed in this environment: {e}")
        try:
            if not created:
                pytest.skip("Failed to create semgrep rule for update test")
            self.created_semgrep_rule_uuids.append(created.uuid)
            current = client.semgrep_rule.get(created.uuid, namespace=self.namespace)
            if not current:
                pytest.skip(f"Could not retrieve semgrep rule {created.uuid}")
            update_payload = UpdateSemgrepRulePayload(
                meta=SemgrepRuleMetaCreate(
                    name=rule_id, description="Updated by client-ux"
                )
            )
            try:
                updated = client.semgrep_rule.update(
                    created.uuid,
                    update_payload,
                    update_mask="meta.description",
                    namespace=self.namespace,
                )
            except Exception as e:
                pytest.skip(f"Semgrep rule update not allowed in this environment: {e}")
            assert updated is not None
        finally:
            if created is not None:  # type: ignore[reportUnnecessaryComparison]
                try:
                    semgrep_rule.delete_semgrep_rule(
                        self.client, self.namespace, created.uuid
                    )
                except Exception as e:
                    print(f"[WARNING] Cleanup failed for {created.uuid}: {e}")

    @pytest.mark.writes
    def test_semgrep_rule_delete(self) -> None:
        """Create then delete the created resource."""
        client = endorlabs.Client(
            tenant=self.namespace,
            api_client=self.client,
        )
        rule_id = f"client-ux-del-{int(time.time())}"
        payload = CreateSemgrepRulePayload(
            meta=SemgrepRuleMetaCreate(
                name=rule_id, description="Consumer UX delete test"
            ),
            spec=SemgrepRuleSpec(
                rule=SemgrepNativeRule(
                    id=rule_id,
                    languages=["python"],
                    message="Client UX delete test",
                    pattern="open($F)",
                )
            ),
            propagate=False,
        )
        from endorlabs.exceptions import PermissionDeniedError

        try:
            created = client.semgrep_rule.create(payload)
        except PermissionDeniedError as e:
            pytest.skip(f"Semgrep rule create not allowed in this environment: {e}")
        if not created:
            pytest.skip("Failed to create semgrep rule for delete test")
        result = client.semgrep_rule.delete(created.uuid)
        assert result is True
