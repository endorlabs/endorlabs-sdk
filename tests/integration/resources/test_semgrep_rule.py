"""Test cases for SemgrepRule resource operations.

Canonical order: LIST (namespace) -> GET -> Create -> Update -> Delete.
Uses conftest api_client, namespace, root_namespace.
"""

import time

import pytest

import endorlabs
from endorlabs.api_client import APIClient
from endorlabs.resources.semgrep_rule import (
    CreateSemgrepRulePayload,
    SemgrepNativeRule,
    SemgrepRuleMetaCreate,
    SemgrepRuleSpec,
    UpdateSemgrepRulePayload,
)
from tests.conftest import TEST_MAX_PAGES


@pytest.mark.integration
class TestSemgrepRule:
    """Canonical order: LIST -> GET -> Create -> Update -> Delete."""

    @pytest.fixture(autouse=True)
    def setup(self, api_client: APIClient, namespace: str, root_namespace: str) -> None:
        """Set client and namespaces from conftest."""
        self.client = api_client
        self.namespace = namespace
        self.root_namespace = root_namespace
        self.endor_client = endorlabs.Client(tenant=namespace, api_client=api_client)
        self.endor_root_client = endorlabs.Client(
            tenant=root_namespace, api_client=api_client
        )
        self.created_semgrep_rule_uuids: list[str] = []

    def teardown_method(self) -> None:
        """Clean up any semgrep rules created during tests."""
        if hasattr(self, "created_semgrep_rule_uuids"):
            for rule_uuid in self.created_semgrep_rule_uuids:
                try:
                    self.endor_client.SemgrepRule.delete(rule_uuid)
                except Exception as e:
                    print(f"[WARNING] Failed to delete semgrep rule {rule_uuid}: {e}")
            self.created_semgrep_rule_uuids.clear()

    def test_semgrep_rule_list(self) -> None:
        """LIST in namespace."""
        result = self.endor_client.SemgrepRule.list(
            max_pages=TEST_MAX_PAGES,
        )
        assert isinstance(result, list)

    def test_semgrep_rule_get(self) -> None:
        """GET first item from LIST in namespace."""
        items = self.endor_client.SemgrepRule.list(
            max_pages=TEST_MAX_PAGES,
        )
        if not items:
            pytest.skip("No resources in scope (empty; may be filter/auth/scope)")
        item = items[0]
        ns = (
            item.tenant_meta.namespace
            if item.tenant_meta and getattr(item.tenant_meta, "namespace", None)
            else self.root_namespace
        )
        got = self.endor_client.SemgrepRule.get(item.uuid, namespace=ns)
        assert got is not None
        assert got.uuid == item.uuid

    @pytest.mark.writes
    def test_semgrep_rule_create(self) -> None:
        """Create a semgrep rule; teardown deletes."""
        rule_id = f"client-ux-rule-{int(time.time())}"
        payload = CreateSemgrepRulePayload(
            meta=SemgrepRuleMetaCreate(name=rule_id, description="Consumer UX create"),
            spec=SemgrepRuleSpec(
                rule=SemgrepNativeRule(
                    id=rule_id,
                    languages=["python"],
                    message="Client UX test rule",
                    severity="ERROR",
                    pattern="exec($VAR)",
                )
            ),
            propagate=False,
        )
        from endorlabs.core.exceptions import PermissionDeniedError

        created = None
        try:
            created = self.endor_client.SemgrepRule.create(payload)
        except PermissionDeniedError as e:
            pytest.skip(f"Semgrep rule create not allowed in this environment: {e}")
        try:
            assert created is not None
            assert created.meta.name == rule_id
            self.created_semgrep_rule_uuids.append(created.uuid)
        finally:
            if created is not None:  # type: ignore[reportUnnecessaryComparison]
                try:
                    self.endor_client.SemgrepRule.delete(created.uuid)
                except Exception as e:
                    print(f"[WARNING] Cleanup failed for {created.uuid}: {e}")

    @pytest.mark.writes
    def test_semgrep_rule_update(self) -> None:
        """Create then update the created resource; teardown deletes."""
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
                    severity="ERROR",
                    pattern="eval($X)",
                )
            ),
            propagate=False,
        )
        from endorlabs.core.exceptions import PermissionDeniedError

        created = None
        try:
            created = self.endor_client.SemgrepRule.create(create_payload)
        except PermissionDeniedError as e:
            pytest.skip(f"Semgrep rule create not allowed in this environment: {e}")
        try:
            if not created:
                pytest.skip("Failed to create semgrep rule for update test")
            self.created_semgrep_rule_uuids.append(created.uuid)
            current = self.endor_client.SemgrepRule.get(
                created.uuid, namespace=self.namespace
            )
            if not current:
                pytest.skip(f"Could not retrieve semgrep rule {created.uuid}")
            # The semgrep rule API always validates spec during update,
            # even when only meta fields are in the update_mask.  Include
            # the existing spec so the backend can validate it.
            update_payload = UpdateSemgrepRulePayload(
                meta=SemgrepRuleMetaCreate(
                    name=rule_id, description="Updated by client-ux"
                ),
                spec=current.spec,
            )
            try:
                updated = self.endor_client.SemgrepRule.update(
                    created.uuid,
                    update_payload,
                    update_mask="meta.description,spec",
                    namespace=self.namespace,
                )
            except PermissionDeniedError as e:
                pytest.skip(f"Semgrep rule update not allowed in this environment: {e}")
            assert updated is not None
        finally:
            if created is not None:  # type: ignore[reportUnnecessaryComparison]
                try:
                    self.endor_client.SemgrepRule.delete(created.uuid)
                except Exception as e:
                    print(f"[WARNING] Cleanup failed for {created.uuid}: {e}")

    @pytest.mark.writes
    def test_semgrep_rule_delete(self) -> None:
        """Create then delete the created resource."""
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
                    severity="ERROR",
                    pattern="open($F)",
                )
            ),
            propagate=False,
        )
        from endorlabs.core.exceptions import PermissionDeniedError

        try:
            created = self.endor_client.SemgrepRule.create(payload)
        except PermissionDeniedError as e:
            pytest.skip(f"Semgrep rule create not allowed in this environment: {e}")
        if not created:
            pytest.skip("Failed to create semgrep rule for delete test")
        result = self.endor_client.SemgrepRule.delete(created.uuid)
        assert result is True
