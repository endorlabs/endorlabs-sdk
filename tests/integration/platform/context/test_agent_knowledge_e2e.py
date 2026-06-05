"""End-to-end tests for agent bundle bootstrap and skill-aligned workflows."""

from __future__ import annotations

import json
import os

import pytest

import endorlabs
from tests.conftest import (
    CANONICAL_SDK_REPO_URL,
    TEST_MAX_PAGES_TRAVERSE,
    TEST_TRAVERSE_PAGE_SIZE,
)


@pytest.mark.integration
class TestAgentBundleE2e:
    """Validate shipped bundle materialization and retrieve-scan-results skill flow."""

    def test_init_materializes_sdk_bundle_without_auth(self, tmp_path) -> None:
        status = endorlabs.init(
            output_dir=tmp_path,
            include_openapi=False,
            include_user_docs=False,
        )
        assert status.agent_bundle_path is not None
        assert (status.agent_bundle_path / "INDEX.md").is_file()
        assert (
            status.agent_bundle_path / "skills" / "retrieve-scan-results" / "SKILL.md"
        ).is_file()
        assert status.context_json_path is not None
        assert status.context_json_path.is_file()
        payload = json.loads(status.context_json_path.read_text(encoding="utf-8"))
        assert payload["agent_bundle_path"] is not None
        assert str(payload["agent_bundle_path"]).endswith("sdk")

    def test_wheel_manifest_matches_materialized_skill_paths(self, tmp_path) -> None:
        wheel_manifest = endorlabs.agent_manifest()
        status = endorlabs.init(
            output_dir=tmp_path,
            include_openapi=False,
            include_user_docs=False,
        )
        assert status.agent_bundle_path is not None
        materialized = json.loads(
            (status.agent_bundle_path / "MANIFEST.json").read_text(encoding="utf-8")
        )
        wheel_skill = next(
            entry
            for entry in wheel_manifest["skills"]
            if entry["id"] == "troubleshoot-sdk"
        )
        materialized_skill = next(
            entry
            for entry in materialized["skills"]
            if entry["id"] == "troubleshoot-sdk"
        )
        assert wheel_skill["description"] == materialized_skill["description"]
        assert (status.agent_bundle_path / wheel_skill["path"]).is_file()

    def test_retrieve_scan_results_skill_workflow(
        self,
        endor_client,
        namespace,
    ) -> None:
        """Exercise retrieve-scan-results skill: Project -> ScanResult -> Finding."""
        from endorlabs.core.exceptions import ServerError

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
