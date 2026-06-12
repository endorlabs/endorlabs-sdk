"""End-to-end test for the retrieving-scan-results workflow.

Uses converged facade lanes: search_by_name, list_by_project, list_by_scan.
"""

from __future__ import annotations

import os

import pytest

import endorlabs
from tests.conftest import CANONICAL_SDK_REPO_URL, TEST_MAX_PAGES_TRAVERSE


@pytest.mark.integration
class TestRetrievingScanResultsWorkflow:
    """End-to-end test for retrieving scan results workflow."""

    @pytest.fixture(autouse=True)
    def setup(self, api_client, namespace) -> None:
        self.endor_client = endorlabs.Client(tenant=namespace, api_client=api_client)
        self.namespace = namespace
        self.repo_url = os.getenv("TEST_REPO_URL", CANONICAL_SDK_REPO_URL)

    def _find_project(self):
        print("\n[Step 1] Finding Project by repository URL (search_by_name)...")
        projects = self.endor_client.Project.search_by_name(
            self.repo_url,
            traverse=True,
            max_pages=TEST_MAX_PAGES_TRAVERSE,
        )
        if not projects:
            pytest.fail(f"Project not found for repository URL: {self.repo_url}")
        project = projects[0]
        print(f"Found Project UUID: {project.uuid}")
        return project

    def _get_most_recent_scan(self, project) -> object | None:
        print("\n[Step 2] Getting most recent ScanResult (list_by_project)...")
        route = self.endor_client.ScanResult.list_by_project(
            project,
            limit=1,
            max_pages=TEST_MAX_PAGES_TRAVERSE,
        )
        scans = route.values or []
        if not scans:
            return None
        scan = scans[0]
        print(f"Found ScanResult UUID: {scan.uuid}")
        return scan

    def _get_findings_for_project(self, project) -> list[object]:
        route = self.endor_client.Finding.list_by_project(
            project,
            max_pages=TEST_MAX_PAGES_TRAVERSE,
        )
        findings = route.values or []
        print(f"Found {len(findings)} Findings via list_by_project")
        return findings

    def _get_findings_for_scan(self, scan) -> list[object]:
        route = self.endor_client.Finding.list_by_scan(
            scan,
            max_pages=TEST_MAX_PAGES_TRAVERSE,
        )
        findings = route.values or []
        print(f"Found {len(findings)} Findings via list_by_scan")
        return findings

    def test_complete_workflow_end_to_end(self) -> None:
        from endorlabs.core.exceptions import ServerError

        try:
            self._test_complete_workflow_end_to_end_impl()
        except ServerError:
            pytest.skip("Backend returned ServerError (list); skip")

    def _test_complete_workflow_end_to_end_impl(self) -> None:
        print("\n" + "=" * 60)
        print("COMPLETE WORKFLOW: Repository URL -> Project -> ScanResult -> Findings")
        print("=" * 60)

        project = self._find_project()
        scan = self._get_most_recent_scan(project)

        if scan is None:
            findings = self._get_findings_for_project(project)
        else:
            print(f"\n[Step 3] ScanResult UUID: {scan.uuid}")
            findings = self._get_findings_for_scan(scan)
            if not findings:
                findings = self._get_findings_for_project(project)

        print("\n" + "=" * 60)
        print("WORKFLOW SUMMARY")
        print("=" * 60)
        print(f"Repository URL: {self.repo_url}")
        print(f"Project UUID: {project.uuid}")
        print(f"ScanResult UUID: {getattr(scan, 'uuid', None)}")
        print(f"Total Findings: {len(findings)}")

        if findings:
            level_counts: dict[str, int] = {}
            for finding_obj in findings:
                spec = getattr(finding_obj, "spec", None)
                level = getattr(spec, "level", None) if spec else None
                if level:
                    key = str(level)
                    level_counts[key] = level_counts.get(key, 0) + 1
            print("\nFinding distribution by level:")
            for level, count in sorted(level_counts.items()):
                print(f"  {level}: {count}")

        print("\nComplete workflow executed successfully!")
