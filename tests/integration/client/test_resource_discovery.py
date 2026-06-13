"""Live integration tests for search_by_* discovery helpers."""

from __future__ import annotations

import os

import pytest

from endorlabs.core.exceptions import ServerError
from tests.conftest import (
    CANONICAL_SDK_REPO_SLUG,
    CANONICAL_SDK_REPO_URL,
    TEST_MAX_PAGES_TRAVERSE,
)
from tests.integration.client.helper_assertions import assert_search_hit, nested_attr


@pytest.mark.integration
class TestResourceDiscovery:
    """Validate bounded discovery helpers return semantically matching resources."""

    @pytest.fixture(autouse=True)
    def setup_client(self, facade_client) -> None:
        self.client = facade_client
        self.repo_url = os.getenv("TEST_REPO_URL", CANONICAL_SDK_REPO_URL)

    def test_project_search_by_name_finds_canonical_repo(self) -> None:
        try:
            matches = self.client.Project.search_by_name(
                self.repo_url,
                traverse=True,
                max_pages=TEST_MAX_PAGES_TRAVERSE,
            )
        except ServerError as err:
            pytest.skip(f"Project list unavailable: {err}")
        assert matches, f"No project matched repo URL: {self.repo_url}"
        slug_needle = CANONICAL_SDK_REPO_SLUG.split("/")[-1].lower()
        assert any(
            slug_needle in str(nested_attr(row, "meta.name") or "").lower()
            or CANONICAL_SDK_REPO_SLUG.lower()
            in str(nested_attr(row, "meta.name") or "").lower()
            for row in matches
        ), "search_by_name should return a project whose name matches the repo query"

    def test_project_search_by_name_row_matches_query(self) -> None:
        try:
            matches = self.client.Project.search_by_name(
                self.repo_url,
                traverse=True,
                max_pages=TEST_MAX_PAGES_TRAVERSE,
            )
        except ServerError as err:
            pytest.skip(f"Project list unavailable: {err}")
        if not matches:
            pytest.skip(f"No project matched repo URL: {self.repo_url}")
        assert_search_hit(
            matches[0],
            self.repo_url,
            ("meta.name",),
            uuid_also=True,
        )

    def test_authorization_policy_search_by_claims_matches_known_policy(self) -> None:
        try:
            policies = self.client.AuthorizationPolicy.list(
                max_pages=TEST_MAX_PAGES_TRAVERSE,
            )
        except ServerError as err:
            pytest.skip(f"AuthorizationPolicy list unavailable: {err}")
        if not policies:
            pytest.skip("No authorization policies in scope")
        sample = policies[0]
        name = nested_attr(sample, "meta.name")
        if not name or len(str(name)) < 3:
            pytest.skip("Sample authorization policy has no searchable name")
        fragment = str(name)[: max(3, len(str(name)) // 2)]
        try:
            matches = self.client.AuthorizationPolicy.search_by_claims(
                fragment,
                max_pages=TEST_MAX_PAGES_TRAVERSE,
            )
        except ServerError as err:
            pytest.skip(f"AuthorizationPolicy search unavailable: {err}")
        assert matches, f"search_by_claims({fragment!r}) returned no rows"
        sample_uuid = nested_attr(sample, "uuid")
        assert any(nested_attr(row, "uuid") == sample_uuid for row in matches), (
            "search_by_claims should rediscover the source policy"
        )

    def test_vulnerability_search_by_vuln_alias_rediscovers_sample(self) -> None:
        try:
            items = self.client.Vulnerability.list(max_pages=TEST_MAX_PAGES_TRAVERSE)
        except ServerError as err:
            pytest.skip(f"Vulnerability list unavailable: {err}")
        if not items:
            pytest.skip("No vulnerabilities in OSS catalog scope")
        sample = items[0]
        aliases = nested_attr(sample, "spec.aliases") or []
        name = nested_attr(sample, "meta.name")
        needle = aliases[0] if aliases else name
        if not needle:
            pytest.skip("Sample vulnerability has no alias or name to search")
        try:
            matches = self.client.Vulnerability.search_by_vuln_alias(
                str(needle),
                max_pages=TEST_MAX_PAGES_TRAVERSE,
            )
        except ServerError as err:
            pytest.skip(f"Vulnerability search unavailable: {err}")
        assert matches, f"search_by_vuln_alias({needle!r}) returned no rows"
        sample_uuid = nested_attr(sample, "uuid")
        assert any(nested_attr(row, "uuid") == sample_uuid for row in matches), (
            "search_by_vuln_alias should rediscover the source vulnerability"
        )
        assert_search_hit(
            matches[0],
            str(needle),
            ("meta.name", "spec.aliases"),
            uuid_also=True,
        )

    def test_vector_store_search_by_name_matches_query(self) -> None:
        query = "function_summary"
        try:
            matches = self.client.VectorStore.search_by_name(
                query,
                max_pages=TEST_MAX_PAGES_TRAVERSE,
            )
        except ServerError as err:
            pytest.skip(f"VectorStore list unavailable: {err}")
        if not matches:
            pytest.skip(f"No VectorStore matched {query!r} in this tenant")
        assert_search_hit(matches[0], query, ("meta.name",))
