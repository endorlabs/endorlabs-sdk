"""
End-to-end test for the retrieving-scan-results workflow.

This test validates the complete workflow described in docs/retrieving-scan-results.md:
1. Get Project UUID from repository URL
2. Get most recent ScanResult for Project
3. Get Findings from ScanResult

Tests against: https://github.com/Endor-Solutions-Architecture/endor-cockpit.git
"""

import os
import sys
from typing import List, Optional

import pytest

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from endor_cockpit.api_client import APIClient
from endor_cockpit.resources import finding, project, scan_result
from endor_cockpit.types import ListParameters


@pytest.mark.integration
class TestRetrievingScanResultsWorkflow:
    """End-to-end test for retrieving scan results workflow."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test environment."""
        self.client = APIClient(auth_method="api-key")
        self.namespace = os.getenv("ENDOR_NAMESPACE", "endor-solutions-tgowan")
        # Allow repository URL to be overridden via environment variable (for CI)
        self.repo_url = os.getenv(
            "TEST_REPO_URL",
            "https://github.com/Endor-Solutions-Architecture/endor-cockpit.git",
        )

        # Validate namespace is set
        if not self.namespace:
            pytest.skip("ENDOR_NAMESPACE environment variable must be set")

        # Extract parent namespace from child namespace if needed
        parts = self.namespace.split(".")
        self.parent_namespace = parts[0] if len(parts) > 1 else self.namespace

    def test_step1_get_project_uuid_from_repo_url(self):
        """Test Step 1: Get Project UUID from repository URL."""
        print("\n=== STEP 1: Finding Project by repository URL ===")

        # Use canonical filter: meta.name matches the repository URL
        import conftest

        list_params = ListParameters(
            filter=f'meta.name=="{self.repo_url}"',
            traverse=True,
            page_size=conftest.TEST_TRAVERSE_PAGE_SIZE,
        )
        projects = project.list_projects(
            self.client,
            self.parent_namespace,
            list_params,
            max_pages=conftest.TEST_MAX_PAGES_TRAVERSE,
        )

        # Fallback: search all projects if filter doesn't match
        if not projects:
            print("  No projects found with filter, searching all projects...")
            list_params = ListParameters(
                traverse=True,
                page_size=conftest.TEST_TRAVERSE_PAGE_SIZE,
            )
            all_projects = project.list_projects(
                self.client,
                self.parent_namespace,
                list_params,
                max_pages=conftest.TEST_MAX_PAGES_TRAVERSE,
            )
            for proj in all_projects:
                if self.repo_url in str(proj.model_dump()).lower():
                    projects = [proj]
                    break

        assert isinstance(projects, list), "Should return a list of projects"
        assert len(projects) > 0, (
            f"Project not found for repository URL: {self.repo_url}"
        )

        project_obj = projects[0]
        assert project_obj.uuid is not None, "Project should have a UUID"
        assert project_obj.meta is not None, "Project should have metadata"

        print(f"✓ Found Project UUID: {project_obj.uuid}")
        print(f"  Project name: {project_obj.meta.name}")

        # Store for next steps
        self.project_uuid = project_obj.uuid
        self.project_obj = project_obj

    def test_step2_get_most_recent_scan_result(self):
        """Test Step 2: Get most recent ScanResult for Project."""
        print("\n=== STEP 2: Getting most recent ScanResult ===")

        # Get the project UUID using canonical filter
        import conftest

        list_params = ListParameters(
            filter=f'meta.name=="{self.repo_url}"',
            traverse=True,
            page_size=conftest.TEST_TRAVERSE_PAGE_SIZE,
        )
        projects = project.list_projects(
            self.client,
            self.parent_namespace,
            list_params,
            max_pages=conftest.TEST_MAX_PAGES_TRAVERSE,
        )

        # Fallback: search all projects if filter doesn't match
        if not projects:
            list_params = ListParameters(
                traverse=True,
                page_size=conftest.TEST_TRAVERSE_PAGE_SIZE,
            )
            all_projects = project.list_projects(
                self.client,
                self.parent_namespace,
                list_params,
                max_pages=conftest.TEST_MAX_PAGES_TRAVERSE,
            )
            for proj in all_projects:
                if self.repo_url in str(proj.model_dump()).lower():
                    projects = [proj]
                    break

        assert len(projects) > 0, "Project should exist"
        project_uuid = projects[0].uuid

        # Get most recent ScanResult (sort by create_time descending, limit to 1)
        list_params = ListParameters(
            filter=f'meta.parent_uuid=="{project_uuid}"',
            traverse=True,
            sort_field="meta.create_time",
            sort_order="descending",
            page_size=1,
        )

        scan_results = scan_result.list_scan_results(
            self.client,
            self.parent_namespace,
            list_params,
            max_pages=conftest.TEST_MAX_PAGES_TRAVERSE,
        )

        if not scan_results or len(scan_results) == 0:
            pytest.skip(
                f"No ScanResult found for Project {project_uuid}. "
                "This is expected if no scans have been run."
            )

        scan_result_obj = scan_results[0]
        assert scan_result_obj.uuid is not None, (
            "ScanResult should have a UUID"
        )
        assert scan_result_obj.meta is not None, (
            "ScanResult should have metadata"
        )
        assert scan_result_obj.meta.parent_uuid == project_uuid, (
            "ScanResult should belong to the project"
        )

        print(f"✓ Found ScanResult UUID: {scan_result_obj.uuid}")
        if scan_result_obj.meta:
            print(f"  Parent UUID: {scan_result_obj.meta.parent_uuid}")
        if scan_result_obj.spec:
            print(f"  Status: {scan_result_obj.spec.status}")

        # Store for next step
        self.scan_result_uuid = scan_result_obj.uuid
        self.scan_result_obj = scan_result_obj

    def test_step3_get_findings_from_scan_result(self):
        """Test Step 3: Get Findings from ScanResult."""
        print("\n=== STEP 3: Retrieving Findings from ScanResult ===")

        # Get the project UUID using canonical filter
        import conftest

        list_params = ListParameters(
            filter=f'meta.name=="{self.repo_url}"',
            traverse=True,
            page_size=conftest.TEST_TRAVERSE_PAGE_SIZE,
        )
        projects = project.list_projects(
            self.client,
            self.parent_namespace,
            list_params,
            max_pages=conftest.TEST_MAX_PAGES_TRAVERSE,
        )

        # Fallback: search all projects if filter doesn't match
        if not projects:
            list_params = ListParameters(
                traverse=True,
                page_size=conftest.TEST_TRAVERSE_PAGE_SIZE,
            )
            all_projects = project.list_projects(
                self.client,
                self.parent_namespace,
                list_params,
                max_pages=conftest.TEST_MAX_PAGES_TRAVERSE,
            )
            for proj in all_projects:
                if self.repo_url in str(proj.model_dump()).lower():
                    projects = [proj]
                    break

        assert len(projects) > 0, "Project should exist"
        project_uuid = projects[0].uuid

        # Get most recent ScanResult
        list_params = ListParameters(
            filter=f'meta.parent_uuid=="{project_uuid}"',
            traverse=True,
            sort_field="meta.create_time",
            sort_order="descending",
            page_size=1,
        )
        scan_results = scan_result.list_scan_results(
            self.client,
            self.parent_namespace,
            list_params,
            max_pages=conftest.TEST_MAX_PAGES_TRAVERSE,
        )

        if not scan_results or len(scan_results) == 0:
            pytest.skip(
                f"No ScanResult found for Project {project_uuid}. "
                "This is expected if no scans have been run."
            )

        scan_result_obj = scan_results[0]
        scan_result_uuid = scan_result_obj.uuid

        # Method 1: Extract Finding UUIDs from spec.findings array
        # Get full ScanResult to access spec.findings
        full_scan_result = scan_result.get_scan_result(
            self.client, self.parent_namespace, scan_result_uuid
        )

        if not full_scan_result or not full_scan_result.spec:
            pytest.skip("Could not retrieve full ScanResult")

        finding_uuids: List[str] = []
        if full_scan_result.spec.findings:
            finding_uuids = full_scan_result.spec.findings

        print(f"  Found {len(finding_uuids)} Finding UUIDs in spec.findings")

        # Method 2: Filter Findings by context.scan_uuid (fallback)
        if not finding_uuids:
            print(
                "  No Finding UUIDs in spec.findings, trying "
                "context.scan_uuid filter..."
            )
            list_params = ListParameters(
                filter=f'context.scan_uuid=="{scan_result_uuid}"',
                traverse=True,
                page_size=conftest.TEST_TRAVERSE_PAGE_SIZE,
            )
            findings = finding.list_findings(
                self.client,
                self.parent_namespace,
                list_params,
                max_pages=conftest.TEST_MAX_PAGES_TRAVERSE,
            )
            print(f"  Found {len(findings)} Findings via context.scan_uuid filter")
        else:
            # Retrieve each Finding by UUID
            findings: List[Optional[object]] = []
            for finding_uuid in finding_uuids[:10]:  # Limit to first 10
                finding_obj = finding.get_finding(
                    self.client, self.parent_namespace, finding_uuid
                )
                if finding_obj:
                    findings.append(finding_obj)

            print(f"  Retrieved {len(findings)} Findings by UUID")

        # Verify findings structure
        if findings:
            for finding_obj in findings[:5]:  # Show first 5
                assert finding_obj.uuid is not None, (
                    "Finding should have a UUID"
                )
                if finding_obj.spec:
                    print(
                        f"    Finding {finding_obj.uuid}: "
                        f"level={finding_obj.spec.level}"
                    )

        print(f"✓ Successfully retrieved {len(findings)} Findings")

    def test_complete_workflow_end_to_end(self):
        """Test complete workflow end-to-end."""
        print("\n" + "=" * 60)
        print("COMPLETE WORKFLOW: Repository URL → Project → ScanResult → Findings")
        print("=" * 60)

        # Step 1: Get Project UUID
        print("\n[Step 1] Finding Project by repository URL...")
        # Use canonical filter: meta.name matches the repository URL
        import conftest

        list_params = ListParameters(
            filter=f'meta.name=="{self.repo_url}"',
            traverse=True,
            page_size=conftest.TEST_TRAVERSE_PAGE_SIZE,
        )
        projects = project.list_projects(
            self.client,
            self.parent_namespace,
            list_params,
            max_pages=conftest.TEST_MAX_PAGES_TRAVERSE,
        )

        # Fallback: search all projects if filter doesn't match
        if not projects:
            print("  No projects found with filter, searching all projects...")
            list_params = ListParameters(
                traverse=True,
                page_size=conftest.TEST_TRAVERSE_PAGE_SIZE,
            )
            all_projects = project.list_projects(
                self.client,
                self.parent_namespace,
                list_params,
                max_pages=conftest.TEST_MAX_PAGES_TRAVERSE,
            )
            for proj in all_projects:
                if self.repo_url in str(proj.model_dump()).lower():
                    projects = [proj]
                    print("  ✓ Found project in full search")
                    break

        if not projects or len(projects) == 0:
            pytest.fail(
                f"Project not found for repository URL: {self.repo_url}"
            )

        project_obj = projects[0]
        project_uuid = project_obj.uuid
        print(f"✓ Found Project UUID: {project_uuid}")

        # Step 2: Get most recent ScanResult
        print("\n[Step 2] Getting most recent ScanResult...")
        list_params = ListParameters(
            filter=f'meta.parent_uuid=="{project_uuid}"',
            traverse=True,
            sort_field="meta.create_time",
            sort_order="descending",
            page_size=1,
        )
        scan_results = scan_result.list_scan_results(
            self.client, self.parent_namespace, list_params
        )

        if not scan_results or len(scan_results) == 0:
            print(
                f"⚠ No ScanResult found for Project {project_uuid}. "
                "Trying to get Findings directly by Project UUID..."
            )
            # Fallback: Get Findings by Project UUID
            list_params = ListParameters(
                filter=f'spec.project_uuid=="{project_uuid}"',
                traverse=True,
            )
            findings = finding.list_findings(
                self.client, self.parent_namespace, list_params
            )
            print(f"✓ Found {len(findings)} Findings directly by Project UUID")
            return  # Early return if no ScanResult

        scan_result_obj = scan_results[0]
        scan_result_uuid = scan_result_obj.uuid
        print(f"✓ Found ScanResult UUID: {scan_result_uuid}")

        if scan_result_obj.spec:
            print(f"  Status: {scan_result_obj.spec.status}")
            if scan_result_obj.spec.start_time:
                print(f"  Start time: {scan_result_obj.spec.start_time}")
            if scan_result_obj.spec.end_time:
                print(f"  End time: {scan_result_obj.spec.end_time}")

        # Step 3: Get ScanResult and extract Finding UUIDs
        print("\n[Step 3] Retrieving ScanResult and extracting Finding UUIDs...")
        full_scan_result = scan_result.get_scan_result(
            self.client, self.parent_namespace, scan_result_uuid
        )

        if not full_scan_result or not full_scan_result.spec:
            pytest.fail("Could not retrieve full ScanResult")

        finding_uuids: List[str] = []
        if full_scan_result.spec.findings:
            finding_uuids = full_scan_result.spec.findings

        print(f"  Found {len(finding_uuids)} Finding UUIDs in spec.findings")

        # Step 4: Retrieve Findings
        print("\n[Step 4] Retrieving Findings...")
        findings: List[object] = []

        if finding_uuids:
            # Method 1: Retrieve by UUID from spec.findings
            for finding_uuid in finding_uuids[:10]:  # Limit to first 10
                finding_obj = finding.get_finding(
                    self.client, self.parent_namespace, finding_uuid
                )
                if finding_obj:
                    findings.append(finding_obj)
            print(f"  Retrieved {len(findings)} Findings by UUID")
        else:
            # Method 2: Filter by context.scan_uuid
            print(
                "  No Finding UUIDs in spec.findings, trying "
                "context.scan_uuid filter..."
            )
            list_params = ListParameters(
                filter=f'context.scan_uuid=="{scan_result_uuid}"',
                traverse=True,
                page_size=conftest.TEST_TRAVERSE_PAGE_SIZE,
            )
            findings = finding.list_findings(
                self.client,
                self.parent_namespace,
                list_params,
                max_pages=conftest.TEST_MAX_PAGES_TRAVERSE,
            )
            print(f"  Found {len(findings)} Findings via context.scan_uuid filter")

        # Display summary
        print("\n" + "=" * 60)
        print("WORKFLOW SUMMARY")
        print("=" * 60)
        print(f"Repository URL: {self.repo_url}")
        print(f"Project UUID: {project_uuid}")
        print(f"ScanResult UUID: {scan_result_uuid}")
        print(f"Total Findings: {len(findings)}")

        if findings:
            # Count by level
            level_counts: dict[str, int] = {}
            for finding_obj in findings:
                if finding_obj.spec and finding_obj.spec.level:
                    level = str(finding_obj.spec.level)
                    level_counts[level] = level_counts.get(level, 0) + 1

            print("\nFinding distribution by level:")
            for level, count in sorted(level_counts.items()):
                print(f"  {level}: {count}")

        print("\n✓ Complete workflow executed successfully!")


if __name__ == "__main__":
    # Run tests directly
    import os

    # Set up environment
    if not os.getenv("ENDOR_NAMESPACE"):
        print("ERROR: ENDOR_NAMESPACE environment variable must be set")
        sys.exit(1)

    # Run pytest
    pytest.main([__file__, "-v", "-s"])
