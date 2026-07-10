"""Test cases for Finding resource operations.

Tests GET and PATCH operations for Finding resources, including tag management.

Greenfield alias unit tests live in
tests/unit/resources/test_greenfield_aliases.py.
"""

import pytest

import endorlabs
from endorlabs.resources.finding import (
    FindingMetaUpdate,
    FindingSpec,
    UpdateFindingPayload,
)
from tests.conftest import (
    TEST_MAX_PAGES,
    TEST_MAX_PAGES_TRAVERSE,
    TEST_PAGE_SIZE,
)


@pytest.mark.integration
class TestFinding:
    """Test cases for Finding resource operations."""

    @pytest.fixture(autouse=True)
    def setup_fast(self, api_client, namespace, root_namespace) -> None:
        """Fast setup: client and namespace from conftest."""
        self.client = api_client
        self.namespace = namespace
        self.root_namespace = root_namespace
        self.tenant_root = root_namespace
        self.endor_client = endorlabs.Client(tenant=namespace, api_client=api_client)
        self.endor_root_client = endorlabs.Client(
            tenant=root_namespace, api_client=api_client
        )
        self.created_finding_uuids = []

    def teardown_method(self) -> None:
        """Clean up any resources created during tests."""
        # Findings are read-only; cleanup is a no-op for consistent structure.
        if hasattr(self, "created_finding_uuids"):
            self.created_finding_uuids.clear()

    @pytest.fixture
    def updatable_finding(self):
        """Return a finding suitable for PATCH tag tests (``spec.dismiss`` is false).

        ``meta.tags`` and ``spec.finding_tags`` are different fields on the wire:

        - ``meta.tags`` — generic resource labels (e.g. ``defectdojo/defectdojo-django:latest``).
        - ``spec.finding_tags`` — triage/classification enums (``FINDING_TAGS_DIRECT``, …).

        Both are listed as mutable in the registry contract, but the API may ignore
        tag mutations when ``spec.dismiss`` is true (dismissed/suppressed findings).
        That behavior is server policy, not something the SDK should paper over in
        ``deserialize_list_row`` or list/update wiring — the client should surface
        the response as returned.

        Uses ``spec.dismiss==false`` with ``traverse=True`` so a single-page sample
        is not a dismissed outlier at the tenant root.
        """
        from endorlabs.core.exceptions import NotFoundError, ServerError
        from endorlabs.core.types import ListParameters

        try:
            results = self.endor_client.Finding.list(
                list_params=ListParameters(
                    filter="spec.dismiss==false",
                    page_size=TEST_PAGE_SIZE,
                ),
                max_pages=TEST_MAX_PAGES_TRAVERSE,
                traverse=True,
            )
        except NotFoundError:
            pytest.skip(
                "List returned 404 (resource does not exist to user: "
                "namespace not accessible to credential or resource no longer exists)"
            )
        except ServerError:
            pytest.skip("Backend returned ServerError (list); skip")
        if not results:
            pytest.skip("No resources in scope (empty; may be filter/auth/scope)")
        for item in results:
            dismissed = item.spec.dismiss if item.spec else False
            if dismissed is not True:
                return item
        pytest.skip(
            "No non-dismissed finding in scope; tag PATCH is not exercised when "
            "spec.dismiss is true (API returns success but leaves meta.tags and "
            "spec.finding_tags unchanged)"
        )

    @pytest.fixture
    def sample_finding(self):
        """Fetch minimal sample data (1 item) for UUID operations.

        Function-scoped but only fetches when explicitly requested by tests.
        Only fetches 1 item without traverse for fast setup. Tests that need
        sample data should request this fixture explicitly.
        """
        from endorlabs.core.exceptions import NotFoundError, ServerError
        from endorlabs.core.types import ListParameters

        try:
            results = self.endor_client.Finding.list(
                list_params=ListParameters(page_size=TEST_PAGE_SIZE),
                max_pages=TEST_MAX_PAGES,
            )
        except NotFoundError:
            pytest.skip(
                "List returned 404 (resource does not exist to user: "
                "namespace not accessible to credential or resource no longer exists)"
            )
        except ServerError:
            pytest.skip("Backend returned ServerError (list); skip")
        if not results:
            pytest.skip("No resources in scope (empty; may be filter/auth/scope)")
        return results[0]  # Return single item, not list

    @pytest.mark.parametrize(
        "category",
        [
            "FINDING_CATEGORY_SCA",
            "FINDING_CATEGORY_SAST",
            "FINDING_CATEGORY_SECRETS",
            "FINDING_CATEGORY_CONTAINER",
            "FINDING_CATEGORY_AI_MODELS",
            "FINDING_CATEGORY_LICENSE_RISK",
            "FINDING_CATEGORY_SCPM",
        ],
    )
    def test_finding_list_by_category(self, category: str) -> None:
        """Test filtering findings by category."""
        from endorlabs.core.types import ListParameters

        # Extract short label from enum name for assertions (e.g. "SCA", "SAST")
        short_label = category.replace("FINDING_CATEGORY_", "")

        list_params = ListParameters(
            filter=f"spec.finding_categories contains [{category}]",
            page_size=TEST_PAGE_SIZE,
        )

        findings = self.endor_client.Finding.list(
            list_params=list_params,
            max_pages=TEST_MAX_PAGES,
        )

        assert isinstance(findings, list), "Should return a list of findings"

        # Validate all returned findings have the expected category
        for f in findings:
            if f.spec.finding_categories:
                assert category in f.spec.finding_categories or any(
                    short_label in str(cat) for cat in f.spec.finding_categories
                ), (
                    f"Finding {f.uuid} should have {category} category, "
                    f"got {f.spec.finding_categories}"
                )

    @pytest.mark.writes
    def test_finding_update_with_mask(self, updatable_finding) -> None:
        """PATCH ``meta.tags`` and ``spec.finding_tags`` with separate semantics.

        Registry marks both paths mutable, but they mean different things on the wire:

        - ``meta.tags`` — free-form resource labels (image refs, project labels, …).
        - ``spec.finding_tags`` — ``FINDING_TAGS_*`` enums used for triage/filtering.

        Example row shape::

            "finding_tags": ["FINDING_TAGS_DIRECT", "FINDING_TAGS_UNFIXABLE", …]
            "tags": ["defectdojo/defectdojo-django:latest"]

        We assert each field with values appropriate to that field. Dismissed findings
        (``spec.dismiss=true``) are excluded via ``updatable_finding`` — not handled
        in SDK wiring, because empty/stale tags after PATCH reflect API policy.
        """
        print("\n=== TESTING FINDING UPDATE WITH MASK ===")

        finding_uuid = updatable_finding.uuid
        ns = updatable_finding.namespace or self.namespace

        current_finding = self.endor_client.Finding.get(finding_uuid, namespace=ns)
        if not current_finding:
            pytest.skip(f"Could not retrieve finding {finding_uuid}")

        original_meta_tags = list(current_finding.meta.tags or [])
        original_finding_tags = list(current_finding.spec.finding_tags or [])

        from endorlabs.resources.finding import FindingTags

        # meta.tags: label-style strings (not FINDING_TAGS_* enums)
        new_meta_tags = list({*original_meta_tags, "integration-test-label"})
        # spec.finding_tags: triage enums only
        new_finding_tags = list(
            {
                *original_finding_tags,
                FindingTags.UNDER_REVIEW.value,
                FindingTags.TEST.value,
            }
        )

        update_payload = UpdateFindingPayload(
            meta=FindingMetaUpdate(tags=new_meta_tags),
            spec=FindingSpec(finding_tags=new_finding_tags),
        )

        print(f"Updating finding: {finding_uuid}")
        print(f"New meta.tags: {new_meta_tags}")
        print(f"New spec.finding_tags: {new_finding_tags}")

        updated_finding = self.endor_client.Finding.update(
            finding_uuid,
            update_payload,
            update_mask="meta.tags,spec.finding_tags",
            namespace=ns,
        )

        assert updated_finding is not None, "Finding update should succeed"

        # PATCH responses may omit masked fields; re-get for authoritative state.
        verified_finding = self.endor_client.Finding.get(finding_uuid, namespace=ns)
        assert verified_finding is not None

        finding_tags_values = verified_finding.spec.finding_tags or []
        assert (
            FindingTags.UNDER_REVIEW.value in finding_tags_values
            or FindingTags.UNDER_REVIEW.value.replace("FINDING_TAGS_", "")
            in [tag.replace("FINDING_TAGS_", "") for tag in finding_tags_values]
        ), "spec.finding_tags should reflect triage enum PATCH"
        assert (
            FindingTags.TEST.value in finding_tags_values
            or FindingTags.TEST.value.replace("FINDING_TAGS_", "")
            in [tag.replace("FINDING_TAGS_", "") for tag in finding_tags_values]
        ), "spec.finding_tags should reflect triage enum PATCH"

        assert "integration-test-label" in (verified_finding.meta.tags or []), (
            "meta.tags should reflect free-form label PATCH (distinct from spec.finding_tags)"
        )

        print(f"[SUCCESS] Finding updated: {verified_finding.uuid}")
        print(f"Updated meta.tags: {verified_finding.meta.tags}")
        print(f"Updated spec.finding_tags: {verified_finding.spec.finding_tags}")

        restore_payload = UpdateFindingPayload(
            meta=FindingMetaUpdate(tags=original_meta_tags),
            spec=FindingSpec(finding_tags=original_finding_tags),
        )
        try:
            self.endor_client.Finding.update(
                finding_uuid,
                restore_payload,
                update_mask="meta.tags,spec.finding_tags",
                namespace=ns,
            )
            print("[CLEANUP] Restored original finding values")
        except Exception as e:
            print(f"[WARNING] Failed to restore original values: {e}")

    @pytest.mark.writes
    def test_client_ux_update_finding(self) -> None:
        """Consumer UX: client.Finding.get() then update then revert."""
        import endorlabs
        from endorlabs.resources.finding import FindingTags

        client = endorlabs.Client(
            tenant=self.namespace,
            api_client=self.client,
        )
        findings = client.Finding.list(max_pages=TEST_MAX_PAGES)
        if not findings:
            pytest.skip("No resources in scope (empty; may be filter/auth/scope)")
        item = findings[0]
        ns = (
            item.tenant_meta.namespace
            if item.tenant_meta and getattr(item.tenant_meta, "namespace", None)
            else self.namespace
        )
        current = client.Finding.get(item.uuid, namespace=ns)
        if not current:
            pytest.skip(f"Could not retrieve finding {item.uuid}")
        original_tags = current.meta.tags or []
        original_finding_tags = list(current.spec.finding_tags or [])
        new_tags = [*original_tags, "client-ux-update"]
        new_finding_tags = list(original_finding_tags)
        if FindingTags.UNDER_REVIEW.value not in new_finding_tags:
            new_finding_tags.append(FindingTags.UNDER_REVIEW.value)
        update_payload = UpdateFindingPayload(
            meta=FindingMetaUpdate(tags=new_tags),
            spec=FindingSpec(finding_tags=new_finding_tags),
        )
        try:
            updated = client.Finding.update(
                item.uuid,
                update_payload,
                update_mask="meta.tags,spec.finding_tags",
                namespace=ns,
            )
        except Exception as e:
            pytest.skip(f"Finding update not allowed in this environment: {e}")
        assert updated is not None
        restore_payload = UpdateFindingPayload(
            meta=FindingMetaUpdate(tags=original_tags),
            spec=FindingSpec(finding_tags=original_finding_tags),
        )
        try:
            client.Finding.update(
                item.uuid,
                restore_payload,
                update_mask="meta.tags,spec.finding_tags",
                namespace=ns,
            )
        except Exception as e:
            print(f"[WARNING] Failed to restore original finding values: {e}")
