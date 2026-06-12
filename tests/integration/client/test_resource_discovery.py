"""Live integration tests for search_by_* discovery helpers."""

from __future__ import annotations

import os

import pytest

import endorlabs
from tests.conftest import CANONICAL_SDK_REPO_URL, TEST_MAX_PAGES_TRAVERSE


@pytest.mark.integration
class TestResourceDiscovery:
    """Validate bounded project search against a live tenant."""

    @pytest.fixture(autouse=True)
    def setup_client(self, api_client, namespace) -> None:
        self.client = endorlabs.Client(tenant=namespace, api_client=api_client)
        self.repo_url = os.getenv("TEST_REPO_URL", CANONICAL_SDK_REPO_URL)

    def test_project_search_by_name_finds_canonical_repo(self) -> None:
        from endorlabs.core.exceptions import ServerError

        try:
            matches = self.client.Project.search_by_name(
                self.repo_url,
                traverse=True,
                max_pages=TEST_MAX_PAGES_TRAVERSE,
            )
        except ServerError as err:
            pytest.skip(f"Project list unavailable: {err}")
        assert matches, f"No project matched repo URL: {self.repo_url}"
