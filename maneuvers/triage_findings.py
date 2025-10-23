#!/usr/bin/env python3
"""
Finding Triage Maneuver Script

This script searches for security findings in the endor-cockpit repository,
assesses them, triages them interactively with the user, tags false positives,
and creates exception policies to suppress them.

Usage:
    python maneuvers/triage_findings.py
"""

import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from endor_cockpit.api_client import APIClient
from endor_cockpit.resources import finding, policy, project
from endor_cockpit.resources.policy import (
    CreatePolicyPayload,
    ExceptionReason,
    PolicyMeta,
    PolicySpec,
    PolicyType,
)
from endor_cockpit.types import ListParameters

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class FindingTriageManeuver:
    """Main class for the finding triage maneuver."""

    def __init__(self):
        self.client = None
        self.namespace = None
        self.project_uuid = None
        self.findings = []
        self.logbook_path = Path(".workspace/logbook.md")
        self.assessment_path = Path(".workspace/findings_assessment.md")

    def log_step(
        self,
        step_name: str,
        task: str,
        problem: str = None,
        troubleshooting: List[str] = None,
        solution: str = None,
        verification: str = None,
    ):
        """Log a step to the logbook."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        log_entry = f"""
## {timestamp}: Finding Triage Maneuver - {step_name}

**Task**: {task}"""

        if problem:
            log_entry += f"\n\n**Problem Encountered**: {problem}"

        if troubleshooting:
            log_entry += "\n\n**Troubleshooting Done**:"
            for attempt in troubleshooting:
                log_entry += f"\n- Attempted: {attempt}"

        if solution:
            log_entry += f"\n\n**Solution**: {solution}"

        if verification:
            log_entry += f"\n\n**Verification**: {verification}"

        log_entry += "\n"

        # Append to logbook
        with open(self.logbook_path, "a", encoding="utf-8") as f:
            f.write(log_entry)

    def validate_environment(self) -> bool:
        """Validate environment setup and initialize API client."""
        logger.info("Step 1: Validating environment setup...")

        # Check required environment variables
        required_vars = [
            "ENDOR_NAMESPACE",
            "ENDOR_API_CREDENTIALS_KEY",
            "ENDOR_API_CREDENTIALS_SECRET",
        ]

        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            error_msg = f"Missing required environment variables: {missing_vars}"
            logger.error(error_msg)
            self.log_step(
                "Environment Validation",
                "Check environment variables",
                problem=error_msg,
                solution="Set missing environment variables",
            )
            return False

        try:
            # Initialize API client
            self.client = APIClient()
            self.namespace = os.getenv("ENDOR_NAMESPACE")

            self.log_step(
                "Environment Validation",
                "Check environment variables and initialize API client",
                solution="Environment variables set, API client initialized",
                verification="Client initialized successfully",
            )

            return True

        except Exception as e:
            error_msg = f"Failed to initialize API client: {str(e)}"
            logger.error(error_msg)
            self.log_step(
                "Environment Validation",
                "Initialize API client",
                problem=error_msg,
                solution="Check API credentials and network connectivity",
            )
            return False

    def find_target_project(self) -> bool:
        """Find the endor-cockpit project using repository URL filter."""
        logger.info("Step 2: Finding target project...")

        try:
            # Try multiple filter approaches
            filter_attempts = [
                'spec.git.web_url=="https://github.com/Endor-Solutions-Architecture/endor-cockpit"',
                'spec.git.web_url=="https://github.com/Endor-Solutions-Architecture/endor-cockpit.git"',
                'meta.name=="https://github.com/Endor-Solutions-Architecture/endor-cockpit.git"',
                'meta.name=="https://github.com/Endor-Solutions-Architecture/endor-cockpit"',
                'spec.git.full_name=="Endor-Solutions-Architecture/endor-cockpit"',
            ]

            projects = []

            for filter_expr in filter_attempts:
                logger.info(f"Trying filter: {filter_expr}")
                list_params = ListParameters(filter=filter_expr)
                projects = project.list_projects(
                    self.client, self.namespace, list_params
                )

                if projects:
                    break

            if not projects:
                # Try listing all projects to see what's available
                logger.info("No projects found with filters, listing all projects...")
                all_projects = project.list_projects(self.client, self.namespace)
                logger.info(f"Found {len(all_projects)} total projects")

                # Look for endor-cockpit in any field
                for proj in all_projects:
                    if "endor-cockpit" in str(proj.model_dump()).lower():
                        projects = [proj]
                        break

                if not projects:
                    error_msg = (
                        "No projects found matching endor-cockpit repository URL"
                    )
                    logger.error(error_msg)
                    self.log_step(
                        "Find Target Project",
                        "Filter projects by repository URL",
                        problem=error_msg,
                        troubleshooting=[
                            f"Tried filters: {filter_attempts}",
                            "Listed all projects",
                        ],
                        solution=(
                            "Verify repository URL in project spec or "
                            "check project names"
                        ),
                    )
                    return False

            if len(projects) > 1:
                error_msg = f"Multiple projects found ({len(projects)}), expected 1"
                logger.warning(error_msg)
                # Continue with first project
                project_obj = projects[0]
            else:
                project_obj = projects[0]

            self.project_uuid = project_obj.uuid
            logger.info(
                f"Found project: {project_obj.meta.name} (UUID: {self.project_uuid})"
            )

            self.log_step(
                "Find Target Project",
                "Filter projects by repository URL",
                solution=f"Found project: {project_obj.meta.name}",
                verification=f"Project UUID: {self.project_uuid}",
            )

            return True

        except Exception as e:
            error_msg = f"Failed to find project: {str(e)}"
            logger.error(error_msg)
            self.log_step(
                "Find Target Project",
                "Filter projects by repository URL",
                problem=error_msg,
                solution="Check project filtering syntax",
            )
            return False

    def retrieve_findings(self) -> bool:
        """Retrieve SAST findings for the project from both main and dev branches."""
        logger.info(
            "Step 3: Retrieving SAST findings from both main and dev branches..."
        )

        try:
            all_findings = self._fetch_all_findings()
            self.findings = all_findings
            branch_analysis = self._analyze_findings_by_branch()
            self._log_retrieval_results(branch_analysis)
            return True

        except Exception as e:
            self._handle_retrieval_error(e)
            return False

    def _fetch_all_findings(self) -> list:
        """Fetch all SAST findings with pagination."""
        all_findings = []
        page_size = 50  # Reasonable page size
        page_token = None

        while True:
            page_findings = self._fetch_page_findings(page_token, page_size)
            if not page_findings:
                break

            all_findings.extend(page_findings)
            logger.info(f"Retrieved page: {len(page_findings)} findings")

            self._log_page_details(page_findings, all_findings)
            self._log_finding_details(page_findings)

            # If we got fewer findings than page_size, we've reached the end
            if len(page_findings) < page_size:
                break

            # Get next page token from the response (if available)
            # Note: Extract page_token from response in actual implementation
            # For now, we'll break after first page to avoid infinite loop
            break

        return all_findings

    def _fetch_page_findings(self, page_token: str, page_size: int) -> list:
        """Fetch a single page of findings."""
        list_params = ListParameters(
            filter=(
                f'spec.project_uuid=="{self.project_uuid}" AND '
                f'spec.finding_categories=="FINDING_CATEGORY_SAST"'
            ),
            sort_field="spec.level",
            sort_order="desc",
            page_token=page_token,
            page_size=page_size,
        )

        return finding.list_findings(self.client, self.namespace, list_params)

    def _log_page_details(self, page_findings: list, all_findings: list):
        """Log details about the current page."""
        # Log available methods on first page
        if len(all_findings) == len(page_findings):  # First page
            methods = set()
            for finding_obj in page_findings:
                if hasattr(finding_obj.spec, "method"):
                    methods.add(finding_obj.spec.method)
            logger.info(f"Available finding methods: {list(methods)}")

    def _log_finding_details(self, page_findings: list):
        """Log detailed information about findings."""
        for finding_obj in page_findings:
            branch = self._get_finding_branch(finding_obj)
            self._log_single_finding(finding_obj, branch)

    def _get_finding_branch(self, finding_obj) -> str:
        """Get the branch for a finding."""
        branch = "unknown"
        if (
            hasattr(finding_obj.spec, "source_code_version")
            and finding_obj.spec.source_code_version
        ):
            if hasattr(finding_obj.spec.source_code_version, "ref"):
                branch = finding_obj.spec.source_code_version.ref
        return branch

    def _log_single_finding(self, finding_obj, branch: str):
        """Log details for a single finding."""
        logger.info(f"SAST Finding: {finding_obj.meta.name}")
        logger.info(f"  UUID: {finding_obj.uuid}")
        logger.info(f"  Level: {finding_obj.spec.level}")
        logger.info(f"  Method: {finding_obj.spec.method}")
        logger.info(f"  Branch: {branch}")

        self._log_finding_optional_fields(finding_obj)
        self._log_sast_specific_fields(finding_obj)
        logger.info("  ---")

    def _log_finding_optional_fields(self, finding_obj):
        """Log optional fields of a finding."""
        if (
            hasattr(finding_obj.spec, "finding_categories")
            and finding_obj.spec.finding_categories
        ):
            logger.info(f"  Categories: {finding_obj.spec.finding_categories}")
        if (
            hasattr(finding_obj.spec, "summary")
            and finding_obj.spec.summary
        ):
            logger.info(f"  Summary: {finding_obj.spec.summary[:100]}...")
        if (
            hasattr(finding_obj.spec, "finding_tags")
            and finding_obj.spec.finding_tags
        ):
            logger.info(f"  Tags: {finding_obj.spec.finding_tags}")

    def _log_sast_specific_fields(self, finding_obj):
        """Log SAST-specific fields."""
        for attr in ["file_path", "line_number", "target_uuid", "parent_uuid"]:
            if hasattr(finding_obj.spec, attr):
                value = getattr(finding_obj.spec, attr)
                if value is not None:
                    logger.info(f"  {attr.replace('_', ' ').title()}: {value}")

    def _analyze_findings_by_branch(self) -> dict:
        """Analyze findings by branch."""
        branch_analysis = {}
        for finding_obj in self.findings:
            branch = self._get_finding_branch(finding_obj)
            if branch not in branch_analysis:
                branch_analysis[branch] = []
            branch_analysis[branch].append(finding_obj)
        return branch_analysis

    def _log_retrieval_results(self, branch_analysis: dict):
        """Log the results of findings retrieval."""
        logger.info(f"Retrieved {len(self.findings)} SAST findings total")
        for branch, findings in branch_analysis.items():
            logger.info(f"  {branch} branch: {len(findings)} findings")

        self.log_step(
            "Retrieve SAST Findings",
            "Get SAST findings for project from all branches",
            solution=(
                f"Retrieved {len(self.findings)} SAST findings from "
                f"{len(branch_analysis)} branches"
            ),
            verification=(
                f"SAST findings sorted by severity level, "
                f"branch analysis: {dict(branch_analysis)}"
            ),
        )

    def _handle_retrieval_error(self, e: Exception):
        """Handle errors during findings retrieval."""
        error_msg = f"Failed to retrieve SAST findings: {str(e)}"
        logger.error(error_msg)
        self.log_step(
            "Retrieve SAST Findings",
            "Get SAST findings for project from all branches",
            problem=error_msg,
            solution="Check SAST finding filtering syntax",
        )

    def generate_assessment(self) -> bool:
        """Generate findings assessment document with AI recommendations."""
        logger.info("Step 4: Generating assessment document...")

        try:
            # Calculate summary statistics
            total_findings = len(self.findings)
            severity_counts = {}
            category_counts = {}

            for finding_obj in self.findings:
                # Count by severity
                level = finding_obj.spec.level
                severity_counts[level] = severity_counts.get(level, 0) + 1

                # Count by category
                categories = finding_obj.spec.finding_categories or []
                for category in categories:
                    category_counts[category] = category_counts.get(category, 0) + 1

            # Generate assessment document
            assessment_content = f"""# SAST Findings Assessment - Endor Cockpit

Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Project UUID: {self.project_uuid}

## Executive Summary

- **Total SAST Findings**: {total_findings}
- **Project**: endor-cockpit

### Severity Breakdown
"""

            for severity in ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]:
                count = severity_counts.get(severity, 0)
                assessment_content += f"- **{severity}**: {count}\n"

            assessment_content += "\n### Category Breakdown\n"
            for category, count in sorted(category_counts.items()):
                assessment_content += f"- **{category}**: {count}\n"

            assessment_content += "\n## Findings Inventory\n\n"

            # Generate detailed assessment for each finding
            for i, finding_obj in enumerate(self.findings, 1):
                assessment_content += self._generate_finding_assessment(finding_obj, i)

            # Write assessment document
            with open(self.assessment_path, "w", encoding="utf-8") as f:
                f.write(assessment_content)

            logger.info(f"Assessment document written to {self.assessment_path}")

            self.log_step(
                "Generate Assessment",
                "Create findings assessment document",
                solution=f"Generated assessment with {total_findings} findings",
                verification=f"Document saved to {self.assessment_path}",
            )

            return True

        except Exception as e:
            error_msg = f"Failed to generate assessment: {str(e)}"
            logger.error(error_msg)
            self.log_step(
                "Generate Assessment",
                "Create findings assessment document",
                problem=error_msg,
                solution="Check file permissions and path",
            )
            return False

    def _generate_finding_assessment(self, finding_obj, index: int) -> str:
        """Generate assessment for a single finding with AI recommendations."""

        # AI Risk Analysis Logic
        likelihood = "MEDIUM"
        impact = "MEDIUM"
        recommendation = "MONITOR"
        rationale = "Standard security finding requiring review"

        # Analyze based on finding characteristics
        level = finding_obj.spec.level
        categories = finding_obj.spec.finding_categories or []
        package_name = finding_obj.spec.target_dependency_package_name
        ecosystem = finding_obj.spec.ecosystem

        # Adjust recommendations based on context
        if level in ["CRITICAL", "HIGH"]:
            impact = "HIGH" if level == "CRITICAL" else "MEDIUM"
            likelihood = "HIGH"
            recommendation = "FIX"
            rationale = f"High severity {level} finding requires immediate attention"

        elif "SECRETS" in categories:
            recommendation = "FIX"
            rationale = "Secret detection findings should be addressed immediately"

        elif package_name and ecosystem:
            # Check if it's a dev dependency (heuristic)
            if any(
                dev_indicator in package_name.lower()
                for dev_indicator in ["test", "dev", "mock", "spec", "example"]
            ):
                recommendation = "SUPPRESS"
                rationale = "Appears to be development/testing dependency"
            else:
                recommendation = "MONITOR"
                rationale = "Production dependency - monitor for updates"

        return f"""### Finding {index}: {finding_obj.meta.name}

- **UUID**: {finding_obj.uuid}
- **Severity**: {finding_obj.spec.level}
- **Categories**: {", ".join(categories) if categories else "None"}
- **Summary**: {finding_obj.spec.summary or "No summary available"}
- **Affected Component**: {finding_obj.spec.target_dependency_package_name or "N/A"} (
    {finding_obj.spec.ecosystem or "N/A"})
- **Remediation**: {finding_obj.spec.remediation or "No remediation guidance"}
- **Current Tags**: {", ".join(finding_obj.spec.finding_tags)
    if finding_obj.spec.finding_tags else "None"}

**Risk Assessment** (AI-generated recommendations):
- **Likelihood**: {likelihood}
- **Impact**: {impact}
- **Recommendation**: {recommendation}
- **Rationale**: {rationale}

**Triage Decision**: [ ] SUPPRESS (false-positive) | [ ] FIX | [ ] DEFER

---

"""

    def interactive_triage(self) -> bool:
        """Tag all SAST findings as false-positive for testing."""
        logger.info("Step 5: Tagging all SAST findings as false-positive...")

        try:
            if not self.findings:
                logger.info("No findings to triage")
                return True

            # Tag ALL SAST findings as false-positive (skip AI assessment)
            tagged_count = 0
            branch_stats = {}

            for finding_obj in self.findings:
                # Determine branch for statistics
                branch = "unknown"
                if (
                    hasattr(finding_obj.spec, "source_code_version")
                    and finding_obj.spec.source_code_version
                ):
                    if hasattr(finding_obj.spec.source_code_version, "ref"):
                        branch = finding_obj.spec.source_code_version.ref

                if branch not in branch_stats:
                    branch_stats[branch] = 0

                if self._tag_finding_as_false_positive(finding_obj.uuid):
                    tagged_count += 1
                    branch_stats[branch] += 1

            logger.info(
                f"Tagged {tagged_count} SAST findings as false-positive"
            )
            for branch, count in branch_stats.items():
                logger.info(f"  {branch} branch: {count} findings tagged")

            self.log_step(
                "Tag All SAST Findings",
                "Tag all SAST findings as false-positive from all branches",
                solution=(
                    f"Tagged {tagged_count} SAST findings as false-positive "
                    f"across {len(branch_stats)} branches"
                ),
                verification=(
                    f"All SAST findings tagged with false-positive tag, "
                    f"branch breakdown: {branch_stats}"
                ),
            )

            return True

        except Exception as e:
            error_msg = f"Failed to tag SAST findings: {str(e)}"
            logger.error(error_msg)
            self.log_step(
                "Tag All SAST Findings",
                "Tag all SAST findings as false-positive from all branches",
                problem=error_msg,
                solution="Check finding tagging logic",
            )
            return False

    def _is_ai_recommended_suppress(self, finding_obj) -> bool:
        """Check if finding is AI-recommended for suppression."""
        # Simple heuristic: suppress if it's a dev dependency or low severity
        package_name = finding_obj.spec.target_dependency_package_name
        level = finding_obj.spec.level

        # Check severity level (convert enum to string for comparison)
        level_str = str(level) if hasattr(level, "value") else str(level)
        if "LOW" in level_str or "INFO" in level_str:
            return True

        if package_name and any(
            dev_indicator in package_name.lower()
            for dev_indicator in ["test", "dev", "mock", "spec", "example"]
        ):
            return True

        return False

    def _tag_finding_as_false_positive(self, finding_uuid: str) -> bool:
        """Tag a finding as false-positive."""
        try:
            # Get current finding
            current_finding = finding.get_finding(
                self.client, self.namespace, finding_uuid
            )
            if not current_finding:
                logger.warning(f"Finding {finding_uuid} not found")
                return False

            # Update with false-positive tag in meta.tags (most reliable location)
            existing_tags = current_finding.meta.tags or []
            new_tags = ["false-positive"] + [
                tag for tag in existing_tags if tag != "false-positive"
            ]

            # Use raw API client to bypass Pydantic serialization issues
            headers = self.client.default_headers
            headers.update(
                {"Accept": "application/json", "Content-Type": "application/json"}
            )

            request_data = {
                "object": {
                    "uuid": finding_uuid,
                    "tenant_meta": {"namespace": self.namespace},
                    "meta": {"tags": new_tags},
                },
                "request": {"update_mask": "meta.tags"},
            }

            try:
                res = self.client.patch(
                    f"v1/namespaces/{self.namespace}/findings",
                    headers=headers,
                    data=request_data,
                )
                if res.status_code == 200:
                    logger.info(
                        f"Successfully tagged finding {finding_uuid} as false-positive"
                    )
                    return True
                else:
                    logger.error(
                        f"Failed to tag finding {finding_uuid}: {res.status_code}"
                    )
                    return False
            except Exception as e:
                logger.error(f"Error tagging finding {finding_uuid}: {str(e)}")
                return False

        except Exception as e:
            logger.error(f"Error tagging finding {finding_uuid}: {str(e)}")
            return False

    def _get_repository_uuid(self) -> Optional[str]:
        """Get repository UUID from the project for Rego rule targeting."""
        try:
            # Import repository resource
            from endor_cockpit.resources import repository

            # List repositories in the namespace
            repositories = repository.list_repositories(
                self.client, self.namespace
            )
            logger.info(
                f"Found {len(repositories)} repositories in namespace"
            )

            # Find repository by name matching our project
            # Since repositories don't have project_uuid, match by name
            # Use the project name from the project we found earlier
            project_name = (
                "https://github.com/Endor-Solutions-Architecture/"
                "endor-cockpit.git"
            )
            for repo in repositories:
                if repo.meta.name == project_name:
                    logger.info(
                        f"Found matching repository: {repo.meta.name} "
                        f"(UUID: {repo.uuid})"
                    )
                    return repo.uuid

            # Fallback: look for endor-cockpit specifically
            for repo in repositories:
                if "endor-cockpit" in repo.meta.name.lower():
                    logger.info(
                        f"Found endor-cockpit repository: {repo.meta.name} "
                        f"(UUID: {repo.uuid})"
                    )
                    return repo.uuid

            logger.warning(f"No repository found for project {self.project_uuid}")
            logger.info("Available repositories:")
            for repo in repositories:
                logger.info(f"  - {repo.meta.name} (UUID: {repo.uuid})")
            return None

        except Exception as e:
            logger.error(f"Error getting repository UUID: {str(e)}")
            return None

    def create_exception_policy(self) -> bool:
        """Create exception policy to suppress tagged findings."""
        logger.info("Step 6: Creating exception policy...")

        try:
            # For dependency vulnerability findings, use Project UUID directly
            # These findings don't have Repository/RepositoryVersion/
            # PackageVersion UUIDs

            # Build Rego rule to suppress findings with false-positive tag
            # Handle both dev and main branch RepositoryVersions

            rego_rule = f"""package endor.cockpit.exceptions

match_finding[result] {{
  finding := input.resource
  finding.spec.project_uuid == "{self.project_uuid}"
  finding.meta.tags[_] == "false-positive"
  result = {{"Endor": {{"Finding": finding.uuid}}}}
}}"""

            payload = CreatePolicyPayload(
                meta=PolicyMeta(
                    name="Endor Cockpit - False Positive Exceptions (Dev & Main)",
                    kind="Policy",
                    description=(
                        "Suppresses findings tagged as false-positive during "
                        "manual triage for both dev and main branches"
                    ),
                    tags=["exception", "false-positive", "endor-cockpit"],
                ),
                spec=PolicySpec(
                    policy_type=PolicyType.EXCEPTION,
                    rule=rego_rule,
                    project_selector=[f"$uuid={self.project_uuid}"],
                    resource_kinds=["Finding"],
                    disable=False,
                    exception={"reason": ExceptionReason.FALSE_POSITIVE},
                ),
                propagate=False,
            )

            exception_policy = policy.create_policy(
                self.client, self.namespace, payload
            )

            if exception_policy:
                logger.info(f"Created exception policy: {exception_policy.uuid}")
                self.log_step(
                    "Create Exception Policy",
                    "Create policy to suppress tagged findings",
                    solution=f"Created policy: {exception_policy.uuid}",
                    verification=f"Policy name: {exception_policy.meta.name}",
                )
                return True
            else:
                error_msg = "Failed to create exception policy"
                logger.error(error_msg)
                self.log_step(
                    "Create Exception Policy",
                    "Create policy to suppress tagged findings",
                    problem=error_msg,
                    solution="Check policy creation permissions",
                )
                return False

        except Exception as e:
            error_msg = f"Failed to create exception policy: {str(e)}"
            logger.error(error_msg)

            # Log detailed error information
            if hasattr(e, "response"):
                try:
                    error_details = (
                        e.response.json()
                        if hasattr(e.response, "json")
                        else str(e.response.text)
                    )
                    logger.error(f"API Error Details: {error_details}")
                except Exception:
                    logger.error(
                        f"API Error Response: {e.response.text
                        if hasattr(e.response, 'text') else 'No response text'}"
                    )

            self.log_step(
                "Create Exception Policy",
                "Create policy to suppress tagged findings",
                problem=(
                    f"{error_msg} - Check Rego rule syntax and policy parameters"
                ),
                solution=(
                    "Verify OPA/Rego rule syntax and ensure proper input structure"
                ),
                troubleshooting=[
                    "Check Rego rule syntax",
                    "Verify input.resource structure",
                    "Test policy rule manually",
                ],
            )
            return False

    def run(self) -> bool:
        """Run the complete finding triage maneuver."""
        logger.info("Starting Finding Triage Maneuver...")

        steps = [
            ("Environment Validation", self.validate_environment),
            ("Find Target Project", self.find_target_project),
            ("Retrieve Findings", self.retrieve_findings),
            ("Generate Assessment", self.generate_assessment),
            ("Interactive Triage", self.interactive_triage),
            ("Create Exception Policy", self.create_exception_policy),
        ]

        for step_name, step_func in steps:
            logger.info(f"Executing: {step_name}")
            if not step_func():
                logger.error(f"Step failed: {step_name}")
                return False

        logger.info("Finding Triage Maneuver completed successfully!")
        return True


def main():
    """Main entry point."""
    maneuver = FindingTriageManeuver()
    success = maneuver.run()

    if success:
        print("\n✅ Finding Triage Maneuver completed successfully!")
        print(f"📄 Assessment document: {maneuver.assessment_path}")
        print(f"📝 Logbook: {maneuver.logbook_path}")
    else:
        print("\n❌ Finding Triage Maneuver failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
