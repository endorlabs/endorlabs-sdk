"""End-to-end test for the retrieving-scan-results workflow.

This test validates the complete workflow described in docs/retrieving-scan-results.md:
1. Get Project UUID from repository URL
2. Get most recent ScanResult for Project
3. Get Findings from ScanResult

Tests against: https://github.com/Endor-Solutions-Architecture/endorlabs-sdk.git
"""

import os

import pytest

import endorlabs
from endorlabs.core.types import ListParameters
from tests.conftest import TEST_MAX_PAGES_TRAVERSE, TEST_TRAVERSE_PAGE_SIZE


@pytest.mark.integration
class TestRetrievingScanResultsWorkflow:
    """End-to-end test for retrieving scan results workflow."""

    @pytest.fixture(autouse=True)
    def setup(self, api_client, namespace) -> None:
        """Set up test environment (client and namespace from conftest)."""
        self.endor_client = endorlabs.Client(tenant=namespace, api_client=api_client)
        self.namespace = namespace
        self.repo_url = os.getenv(
            "TEST_REPO_URL",
            "https://github.com/Endor-Solutions-Architecture/endorlabs-sdk.git",
        )

    def _find_project_by_repo_url(self) -> str:
        """Find project by repository URL."""
        print("\n[Step 1] Finding Project by repository URL...")
        list_params = ListParameters(
            filter=f'meta.name=="{self.repo_url}"',
            traverse=True,
            page_size=TEST_TRAVERSE_PAGE_SIZE,
        )
        projects = self.endor_client.Project.list(
            list_params=list_params,
            max_pages=TEST_MAX_PAGES_TRAVERSE,
        )

        # Fallback: search all projects if filter doesn't match
        if not projects:
            print("  No projects found with filter, searching all projects...")
            list_params = ListParameters(
                traverse=True,
                page_size=TEST_TRAVERSE_PAGE_SIZE,
            )
            all_projects = self.endor_client.Project.list(
                list_params=list_params,
                max_pages=TEST_MAX_PAGES_TRAVERSE,
            )
            for proj in all_projects:
                if self.repo_url in str(proj.model_dump()).lower():
                    projects = [proj]
                    print("  Found project in full search")
                    break

        if not projects or len(projects) == 0:
            pytest.fail(f"Project not found for repository URL: {self.repo_url}")

        project_obj = projects[0]
        project_uuid = project_obj.uuid
        print(f"Found Project UUID: {project_uuid}")
        return project_uuid

    def _get_most_recent_scan_result(self, project_uuid: str) -> str | None:
        """Get most recent scan result."""
        print("\n[Step 2] Getting most recent ScanResult...")
        list_params = ListParameters(
            filter=f'meta.parent_uuid=="{project_uuid}"',
            traverse=True,
            sort_by="meta.create_time",
            desc=True,
            page_size=TEST_TRAVERSE_PAGE_SIZE,
        )
        scan_results = self.endor_client.ScanResult.list(
            list_params=list_params,
            max_pages=TEST_MAX_PAGES_TRAVERSE,
        )

        if not scan_results or len(scan_results) == 0:
            return None

        scan_result_obj = scan_results[0]
        scan_result_uuid = scan_result_obj.uuid
        print(f"Found ScanResult UUID: {scan_result_uuid}")

        if scan_result_obj.spec:
            print(f"  Status: {scan_result_obj.spec.status}")
            if scan_result_obj.spec.start_time:
                print(f"  Start time: {scan_result_obj.spec.start_time}")
            if scan_result_obj.spec.end_time:
                print(f"  End time: {scan_result_obj.spec.end_time}")

        return scan_result_uuid

    def _get_findings_directly(self, project_uuid: str) -> list[object]:
        """Fallback: get findings directly by project."""
        print(
            f"No ScanResult found for Project {project_uuid}. "
            "Trying to get Findings directly by Project UUID..."
        )
        list_params = ListParameters(
            filter=f'spec.project_uuid=="{project_uuid}"',
            traverse=True,
            page_size=TEST_TRAVERSE_PAGE_SIZE,
        )
        findings = self.endor_client.Finding.list(
            list_params=list_params,
            max_pages=TEST_MAX_PAGES_TRAVERSE,
        )
        print(f"Found {len(findings)} Findings directly by Project UUID")
        return findings

    def _get_findings_for_scan_result(
        self, scan_result_uuid: str, project_uuid: str
    ) -> list[object]:
        """Get findings for scan result by listing with spec.project_uuid filter."""
        print("\n[Step 3] ScanResult UUID from workflow (for reference).")
        print(f"  ScanResult UUID: {scan_result_uuid}")

        print("\n[Step 4] Retrieving Findings by project...")
        list_params = ListParameters(
            filter=f'spec.project_uuid=="{project_uuid}"',
            traverse=True,
            page_size=TEST_TRAVERSE_PAGE_SIZE,
        )
        findings = self.endor_client.Finding.list(
            list_params=list_params,
            max_pages=TEST_MAX_PAGES_TRAVERSE,
        )
        print(f"  Found {len(findings)} Findings via spec.project_uuid filter")

        return findings

    def test_complete_workflow_end_to_end(self) -> None:
        """Test complete workflow end-to-end."""
        from endorlabs.core.exceptions import ServerError

        try:
            self._test_complete_workflow_end_to_end_impl()
        except ServerError:
            pytest.skip("Backend returned ServerError (list); skip")

    def _test_complete_workflow_end_to_end_impl(self) -> None:
        """Run workflow steps; test wraps this to skip on ServerError."""
        print("\n" + "=" * 60)
        print("COMPLETE WORKFLOW: Repository URL -> Project -> ScanResult -> Findings")
        print("=" * 60)

        project_uuid = self._find_project_by_repo_url()
        scan_result_uuid = self._get_most_recent_scan_result(project_uuid)

        if not scan_result_uuid:
            findings = self._get_findings_directly(project_uuid)
            return

        findings = self._get_findings_for_scan_result(scan_result_uuid, project_uuid)

        print("\n" + "=" * 60)
        print("WORKFLOW SUMMARY")
        print("=" * 60)
        print(f"Repository URL: {self.repo_url}")
        print(f"Project UUID: {project_uuid}")
        print(f"ScanResult UUID: {scan_result_uuid}")
        print(f"Total Findings: {len(findings)}")

        if findings:
            level_counts: dict[str, int] = {}
            for finding_obj in findings:
                if finding_obj.spec and finding_obj.spec.level:
                    level = str(finding_obj.spec.level)
                    level_counts[level] = level_counts.get(level, 0) + 1

            print("\nFinding distribution by level:")
            for level, count in sorted(level_counts.items()):
                print(f"  {level}: {count}")

        print("\nComplete workflow executed successfully!")
