"""End-to-end test for the retrieving-scan-results workflow."""

from __future__ import annotations

import os

import pytest

import endorlabs
from endorlabs.core.exceptions import ServerError
from tests.conftest import CANONICAL_SDK_REPO_URL, TEST_MAX_PAGES_TRAVERSE
from tests.integration.client.helper_assertions import nested_attr


@pytest.mark.integration
class TestRetrievingScanResultsWorkflow:
    """End-to-end test for retrieving scan results workflow."""

    @pytest.fixture(autouse=True)
    def setup(self, api_client, namespace) -> None:
        self.endor_client = endorlabs.Client(tenant=namespace, api_client=api_client)
        self.namespace = namespace
        self.repo_url = os.getenv("TEST_REPO_URL", CANONICAL_SDK_REPO_URL)

    def test_complete_workflow_end_to_end(self) -> None:
        try:
            self._test_complete_workflow_end_to_end_impl()
        except ServerError as err:
            pytest.skip(f"Backend returned ServerError (list): {err}")

    def _test_complete_workflow_end_to_end_impl(self) -> None:
        projects = self.endor_client.Project.search_by_name(
            self.repo_url,
            traverse=True,
            max_pages=TEST_MAX_PAGES_TRAVERSE,
        )
        if not projects:
            pytest.fail(f"No project matched repo URL: {self.repo_url}")
        project = projects[0]

        route = self.endor_client.ScanResult.list_by_project(
            project,
            limit=1,
            max_pages=TEST_MAX_PAGES_TRAVERSE,
        )
        scan = route.values[0] if route.values else None

        if scan is None:
            findings = list(
                self.endor_client.Finding.list_by_project(
                    project,
                    max_pages=TEST_MAX_PAGES_TRAVERSE,
                ).values
                or []
            )
        else:
            ctx = getattr(scan, "context", None)
            if ctx is None or not getattr(ctx, "type", None):
                findings = list(
                    self.endor_client.Finding.list_by_project(
                        project,
                        max_pages=TEST_MAX_PAGES_TRAVERSE,
                    ).values
                    or []
                )
            else:
                findings = list(
                    self.endor_client.Finding.list_for_context(
                        scan,
                        max_pages=TEST_MAX_PAGES_TRAVERSE,
                    ).values
                    or []
                )

        assert isinstance(findings, list)
        if findings:
            assert all(nested_attr(f, "uuid") for f in findings[:5])
