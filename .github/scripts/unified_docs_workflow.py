#!/usr/bin/env python3
"""
Unified Documentation & Schema Drift Workflow

This script orchestrates both documentation sync and schema drift detection
workflows, ensuring documentation is fresh before detecting drift.

Usage:
    # Full workflow (docs + drift detection)
    python scripts/unified_docs_workflow.py --all

    # Only update docs
    python scripts/unified_docs_workflow.py --update-docs-only

    # Only check drift (assumes docs are up to date)
    python scripts/unified_docs_workflow.py --check-drift-only

    # Force update docs and check drift
    python scripts/unified_docs_workflow.py --all --force
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional, Tuple

# Add src and scripts to path for imports
scripts_dir = Path(__file__).parent
sys.path.insert(0, str(scripts_dir.parent / "src"))
sys.path.insert(0, str(scripts_dir))

# Import functions from existing scripts using importlib
import importlib.util

# Load sync_external_docs module
spec_sync = importlib.util.spec_from_file_location(
    "sync_external_docs", scripts_dir / "sync_external_docs.py"
)
sync_external_docs = importlib.util.module_from_spec(spec_sync)
spec_sync.loader.exec_module(sync_external_docs)

# Load detect_schema_drift module
spec_drift = importlib.util.spec_from_file_location(
    "detect_schema_drift", scripts_dir / "detect_schema_drift.py"
)
detect_schema_drift = importlib.util.module_from_spec(spec_drift)
spec_drift.loader.exec_module(detect_schema_drift)

# Load create_drift_issues module
spec_issues = importlib.util.spec_from_file_location(
    "create_drift_issues", scripts_dir / "create_drift_issues.py"
)
create_drift_issues = importlib.util.module_from_spec(spec_issues)
spec_issues.loader.exec_module(create_drift_issues)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class UnifiedDocsWorkflow:
    """Orchestrates documentation sync and schema drift detection."""

    def __init__(
        self,
        openapi_output: str = "external_docs/openapi-swagger.json",
        user_docs_output: str = "external_docs/user-docs",
        drift_report_output: str = "schema_drift_report.json",
        sitemap_url: str = "https://docs.endorlabs.com/sitemap.xml",
        max_pages: Optional[int] = None,
        test_path: str = "tests/",
    ):
        self.openapi_output = Path(openapi_output)
        self.user_docs_output = Path(user_docs_output)
        self.drift_report_output = Path(drift_report_output)
        self.sitemap_url = sitemap_url
        self.max_pages = max_pages
        self.test_path = test_path
        self.docs_updated = False
        self.drift_detected = False

    def update_docs(
        self,
        download_openapi: bool = True,
        download_user_docs: bool = False,
        force: bool = False,
    ) -> Tuple[bool, Dict]:
        """
        Phase 1: Update documentation.

        Args:
            download_openapi: Whether to download OpenAPI spec
            download_user_docs: Whether to download user docs
            force: Force re-download even if files exist

        Returns:
            Tuple of (success: bool, summary: Dict)
        """
        logger.info("=" * 80)
        logger.info("PHASE 1: DOCUMENTATION SYNC")
        logger.info("=" * 80)

        summary = {
            "openapi_updated": False,
            "user_docs_updated": False,
            "openapi_path": str(self.openapi_output),
            "user_docs_path": str(self.user_docs_output),
        }

        success = True

        # Download OpenAPI spec
        if download_openapi:
            logger.info("Downloading OpenAPI specification...")
            try:
                # Check if file exists before download
                file_existed_before = self.openapi_output.exists()
                file_mtime_before = (
                    self.openapi_output.stat().st_mtime
                    if file_existed_before
                    else None
                )

                openapi_updated = sync_external_docs.download_openapi_spec(
                    str(self.openapi_output), force=force
                )
                summary["openapi_updated"] = openapi_updated

                if openapi_updated:
                    # Check if file was actually updated
                    if force or not file_existed_before:
                        # Forced download or new file - definitely updated
                        self.docs_updated = True
                        logger.info("OpenAPI spec updated successfully")
                    elif file_existed_before and self.openapi_output.exists():
                        # File existed - check if it was modified
                        file_mtime_after = self.openapi_output.stat().st_mtime
                        if file_mtime_after > file_mtime_before:
                            self.docs_updated = True
                            logger.info("OpenAPI spec updated successfully")
                        else:
                            logger.info(
                                "OpenAPI spec already exists "
                                "(use --force to re-download)"
                            )
                    else:
                        logger.info("OpenAPI spec downloaded successfully")
                        self.docs_updated = True
                else:
                    logger.error("Failed to download OpenAPI spec")
                    success = False
            except Exception as e:
                logger.error(f"Error downloading OpenAPI spec: {e}")
                success = False

        # Download user docs
        if download_user_docs:
            logger.info("Downloading user documentation...")
            try:
                sitemap_urls = sync_external_docs.download_sitemap_urls(
                    self.sitemap_url, timeout=10
                )
                if not sitemap_urls:
                    logger.warning("No URLs found in sitemap")
                else:
                    downloaded_count = sync_external_docs.download_user_docs(
                        sitemap_urls=sitemap_urls,
                        output_dir=self.user_docs_output,
                        max_pages=self.max_pages,
                        timeout=10,
                        force=force,
                    )
                    summary["user_docs_updated"] = downloaded_count > 0
                    summary["user_docs_downloaded"] = downloaded_count
                    if downloaded_count > 0:
                        self.docs_updated = True
                        logger.info(
                            f"User docs updated: {downloaded_count} pages downloaded"
                        )
            except Exception as e:
                logger.error(f"Error downloading user docs: {e}")
                # Don't fail the whole workflow if user docs fail
                logger.warning("Continuing without user docs...")

        logger.info("=" * 80)
        logger.info(f"PHASE 1 COMPLETE: {'SUCCESS' if success else 'FAILED'}")
        logger.info("=" * 80)

        return success, summary

    def check_drift(
        self, force: bool = False, create_issues: bool = True
    ) -> Tuple[bool, Optional[Dict]]:
        """
        Phase 2: Check for schema drift.

        Args:
            force: Force drift check even if docs weren't updated
            create_issues: Whether to create GitHub issues for new drifts

        Returns:
            Tuple of (drift_detected: bool, drift_report: Optional[Dict])
        """
        # Only run drift detection if docs were updated or forced
        if not self.docs_updated and not force:
            logger.info("=" * 80)
            logger.info("PHASE 2: SCHEMA DRIFT DETECTION")
            logger.info("=" * 80)
            logger.info(
                "Skipping drift detection: docs were not updated "
                "(use --force to check anyway)"
            )
            logger.info("=" * 80)
            return False, None

        logger.info("=" * 80)
        logger.info("PHASE 2: SCHEMA DRIFT DETECTION")
        logger.info("=" * 80)

        try:
            # Initialize drift detector
            detector = detect_schema_drift.SchemaDriftDetector(
                output_file=str(self.drift_report_output)
            )

            # Run tests to detect drift
            logger.info(f"Running tests in {self.test_path} to detect drift...")
            test_results = detector.run_tests(self.test_path)

            if "error" in test_results:
                logger.error(f"Error running tests: {test_results['error']}")
                return False, None

            # Generate drift report
            report = detector.generate_report(test_results)

            # Check if drift was detected
            new_drifts = report.get("summary", {}).get("new_drifts", 0)
            self.drift_detected = new_drifts > 0

            logger.info("=" * 80)
            logger.info("SCHEMA DRIFT DETECTION SUMMARY")
            logger.info("=" * 80)
            logger.info(f"New drifts detected: {new_drifts}")
            logger.info(
                f"Validation errors: {report.get('summary', {}).get('validation_errors', 0)}"
            )
            logger.info(
                f"Test status: {report.get('summary', {}).get('test_status', 'unknown')}"
            )
            logger.info(f"Report saved to: {self.drift_report_output}")

            if new_drifts > 0:
                logger.info("\nNew drifts:")
                for drift in report.get("drifts", []):
                    logger.info(f"  - {drift.get('field_path', 'unknown')}")

            # Create GitHub issues if requested
            if create_issues and self.drift_detected:
                logger.info("\nCreating GitHub issues for new drifts...")
                issue_result = self.create_issues(report)
                report["issue_creation"] = issue_result

            logger.info("=" * 80)
            logger.info(
                f"PHASE 2 COMPLETE: {'DRIFT DETECTED' if self.drift_detected else 'NO DRIFT'}"
            )
            logger.info("=" * 80)

            return True, report

        except Exception as e:
            logger.error(f"Error in drift detection: {e}", exc_info=True)
            return False, None

    def create_issues(self, report: Dict) -> Dict:
        """
        Create GitHub issues for new drifts.

        Args:
            report: Drift report dictionary

        Returns:
            Issue creation summary
        """
        repo = os.getenv("GITHUB_REPOSITORY")
        token = os.getenv("GITHUB_TOKEN")

        if not repo or not token:
            logger.warning(
                "GITHUB_REPOSITORY or GITHUB_TOKEN not set - skipping issue creation"
            )
            return {"error": "Missing GitHub credentials"}

        try:
            creator = create_drift_issues.GitHubIssueCreator(
                repo=repo, token=token, label="schema-drift"
            )
            result = creator.create_issues_from_report(str(self.drift_report_output))

            logger.info(f"Issues created: {len(result.get('created', []))}")
            logger.info(f"Issues skipped (duplicates): {len(result.get('skipped', []))}")

            if result.get("created"):
                logger.info("\nCreated issues:")
                for item in result["created"]:
                    logger.info(
                        f"  #{item['issue_number']}: "
                        f"{item['drift']['field_path']}"
                    )
                    logger.info(f"    {item['issue_url']}")

            return result

        except Exception as e:
            logger.error(f"Error creating GitHub issues: {e}")
            return {"error": str(e)}

    def run(
        self,
        update_docs: bool = False,
        check_drift: bool = False,
        download_openapi: bool = True,
        download_user_docs: bool = False,
        force: bool = False,
        create_issues: bool = True,
    ) -> int:
        """
        Run the unified workflow.

        Args:
            update_docs: Whether to update documentation
            check_drift: Whether to check for schema drift
            download_openapi: Whether to download OpenAPI spec
            download_user_docs: Whether to download user docs
            force: Force operations even if not needed
            create_issues: Whether to create GitHub issues for drifts

        Returns:
            Exit code: 0 (success), 1 (drift detected), 2 (error)
        """
        logger.info("=" * 80)
        logger.info("UNIFIED DOCUMENTATION & SCHEMA DRIFT WORKFLOW")
        logger.info("=" * 80)
        logger.info(f"Started at: {datetime.now(timezone.utc).isoformat()}")

        overall_success = True

        # Phase 1: Update documentation
        if update_docs:
            docs_success, docs_summary = self.update_docs(
                download_openapi=download_openapi,
                download_user_docs=download_user_docs,
                force=force,
            )
            if not docs_success:
                overall_success = False
        else:
            docs_summary = {}

        # Phase 2: Check for schema drift
        drift_report = None
        if check_drift:
            drift_success, drift_report = self.check_drift(
                force=force, create_issues=create_issues
            )
            if not drift_success:
                overall_success = False

        # Phase 3: Generate summary report
        logger.info("=" * 80)
        logger.info("PHASE 3: SUMMARY")
        logger.info("=" * 80)

        summary = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "docs_updated": self.docs_updated,
            "drift_detected": self.drift_detected,
            "docs_summary": docs_summary,
            "drift_summary": drift_report.get("summary", {}) if drift_report else None,
            "new_drifts_count": drift_report.get("summary", {}).get("new_drifts", 0)
            if drift_report
            else 0,
        }

        logger.info(f"Documentation updated: {self.docs_updated}")
        logger.info(f"Schema drift detected: {self.drift_detected}")
        if drift_report:
            logger.info(
                f"New drifts: {summary['new_drifts_count']}"
            )

        logger.info("=" * 80)
        logger.info("WORKFLOW COMPLETE")
        logger.info("=" * 80)

        # Determine exit code
        if not overall_success:
            return 2  # Error
        elif self.drift_detected:
            return 1  # Drift detected (successful run, but action needed)
        else:
            return 0  # Success, no drift


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Unified documentation and schema drift workflow",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full workflow (docs + drift detection)
  python scripts/unified_docs_workflow.py --all

  # Only update docs
  python scripts/unified_docs_workflow.py --update-docs-only

  # Only check drift
  python scripts/unified_docs_workflow.py --check-drift-only

  # Force update and check
  python scripts/unified_docs_workflow.py --all --force

  # Update docs with user docs included
  python scripts/unified_docs_workflow.py --update-docs-only --download-user-docs
        """,
    )

    # Action flags (mutually exclusive group)
    action_group = parser.add_mutually_exclusive_group(required=True)
    action_group.add_argument(
        "--all",
        action="store_true",
        help="Run both documentation update and drift detection",
    )
    action_group.add_argument(
        "--update-docs-only",
        action="store_true",
        help="Only update documentation (skip drift detection)",
    )
    action_group.add_argument(
        "--check-drift-only",
        action="store_true",
        help="Only check for schema drift (skip docs update)",
    )

    # Documentation options
    parser.add_argument(
        "--download-openapi",
        action="store_true",
        default=True,
        help="Download OpenAPI spec (default: True when updating docs)",
    )
    parser.add_argument(
        "--no-download-openapi",
        action="store_false",
        dest="download_openapi",
        help="Skip OpenAPI spec download",
    )
    parser.add_argument(
        "--download-user-docs",
        action="store_true",
        help="Download user documentation from sitemap",
    )
    parser.add_argument(
        "--openapi-output",
        default="external_docs/openapi-swagger.json",
        help="Output path for OpenAPI spec",
    )
    parser.add_argument(
        "--user-docs-output",
        default="external_docs/user-docs",
        help="Output directory for user docs",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        help="Maximum number of user doc pages to download",
    )

    # Drift detection options
    parser.add_argument(
        "--test-path",
        default="tests/",
        help="Path to test directory (default: tests/)",
    )
    parser.add_argument(
        "--drift-report-output",
        default="schema_drift_report.json",
        help="Output file for drift report",
    )
    parser.add_argument(
        "--no-create-issues",
        action="store_true",
        help="Don't create GitHub issues for new drifts",
    )

    # Common options
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force operations even if not needed",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Determine what to run
    update_docs = args.all or args.update_docs_only
    check_drift = args.all or args.check_drift_only

    # Initialize workflow
    workflow = UnifiedDocsWorkflow(
        openapi_output=args.openapi_output,
        user_docs_output=args.user_docs_output,
        drift_report_output=args.drift_report_output,
        max_pages=args.max_pages,
        test_path=args.test_path,
    )

    # Run workflow
    exit_code = workflow.run(
        update_docs=update_docs,
        check_drift=check_drift,
        download_openapi=args.download_openapi,
        download_user_docs=args.download_user_docs,
        force=args.force,
        create_issues=not args.no_create_issues,
    )

    sys.exit(exit_code)


if __name__ == "__main__":
    main()

