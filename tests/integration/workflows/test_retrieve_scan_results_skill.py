"""Integration test for retrieve-scan-results skill workflow (live API)."""

from __future__ import annotations

import os

import pytest

from endorlabs.core.exceptions import ServerError
from tests.conftest import (
    CANONICAL_SDK_REPO_URL,
    TEST_MAX_PAGES_TRAVERSE,
    TEST_TRAVERSE_PAGE_SIZE,
)


@pytest.mark.integration
def test_retrieve_scan_results_skill_workflow(
    endor_client,
    namespace,
) -> None:
    """Exercise retrieve-scan-results skill: Project -> ScanResult -> Finding."""
    repo_url = os.getenv("TEST_REPO_URL", CANONICAL_SDK_REPO_URL)
    try:
        projects = endor_client.Project.list(
            filter=f'meta.name=="{repo_url}"',
            traverse=True,
            page_size=TEST_TRAVERSE_PAGE_SIZE,
            max_pages=TEST_MAX_PAGES_TRAVERSE,
        )
    except ServerError:
        pytest.skip("Backend returned ServerError on Project.list")

    if not projects:
        pytest.skip(f"No project found for repository URL: {repo_url}")

    project = projects[0]
    project_namespace = (
        project.tenant_meta.namespace if project.tenant_meta else namespace
    )

    try:
        scan_results = endor_client.ScanResult.list(
            parent=project,
            namespace=project_namespace,
            sort_by="meta.create_time",
            desc=True,
            page_size=TEST_TRAVERSE_PAGE_SIZE,
            max_pages=TEST_MAX_PAGES_TRAVERSE,
        )
    except ServerError:
        pytest.skip("Backend returned ServerError on ScanResult.list")

    try:
        findings = endor_client.Finding.list(
            filter=f'spec.project_uuid=="{project.uuid}"',
            namespace=project_namespace,
            page_size=TEST_TRAVERSE_PAGE_SIZE,
            max_pages=TEST_MAX_PAGES_TRAVERSE,
        )
    except ServerError:
        pytest.skip("Backend returned ServerError on Finding.list")

    assert project.uuid
    assert isinstance(findings, list)
    if scan_results:
        assert scan_results[0].uuid
