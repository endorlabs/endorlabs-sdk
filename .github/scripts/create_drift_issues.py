#!/usr/bin/env python3
"""
Create GitHub Issues for Schema Drift

This script reads schema drift reports and creates GitHub issues,
avoiding duplicates by checking existing issues.

Usage:
    python .github/scripts/create_drift_issues.py --report schema_drift_report.json
"""

import argparse
import json
import logging
import os
import sys
from typing import Dict, List, Optional

import requests

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class GitHubIssueCreator:
    """Create GitHub issues for schema drift detection."""

    def __init__(
        self,
        repo: str,
        token: str,
        label: str = "schema-drift"
    ):
        self.repo = repo
        self.token = token
        self.label = label
        self.base_url = f"https://api.github.com/repos/{repo}"
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json"
        }

    def get_existing_issues(self) -> List[Dict]:
        """Get existing schema drift issues to avoid duplicates."""
        issues = []
        page = 1
        per_page = 100

        while True:
            url = f"{self.base_url}/issues"
            params = {
                "state": "open",
                "labels": self.label,
                "per_page": per_page,
                "page": page
            }

            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()

            page_issues = response.json()
            if not page_issues:
                break

            issues.extend(page_issues)
            page += 1

        logger.info(f"Found {len(issues)} existing {self.label} issues")
        return issues

    def get_resource_file_path(self, resource_name: str) -> str:
        """Map resource name to source file path."""
        if not resource_name:
            return "src/endor_cockpit/models/base.py"

        # Map resource names to their file paths
        resource_file_map = {
            "Finding": "src/endor_cockpit/resources/finding.py",
            "Policy": "src/endor_cockpit/resources/policy.py",
            "Project": "src/endor_cockpit/resources/project.py",
            "Namespace": "src/endor_cockpit/resources/namespace.py",
            "Repository": "src/endor_cockpit/resources/repository.py",
            "RepositoryVersion": "src/endor_cockpit/resources/repository_version.py",
            "PackageVersion": "src/endor_cockpit/resources/package_version.py",
            "DependencyMetadata": "src/endor_cockpit/resources/dependency_metadata.py",
            "ScanResult": "src/endor_cockpit/resources/scan_result.py",
            "LinterResult": "src/endor_cockpit/resources/linter_result.py",
            "Metric": "src/endor_cockpit/resources/metric.py",
            "User": "src/endor_cockpit/resources/user.py",
            "Installation": "src/endor_cockpit/resources/installation.py",
            "BaseResource": "src/endor_cockpit/models/base.py",
            "BaseSpec": "src/endor_cockpit/models/base.py",
        }

        return resource_file_map.get(resource_name, "src/endor_cockpit/models/base.py")

    def extract_model_class(self, model_path: str) -> str:
        """Extract model class name from model path."""
        # Format: "FindingSpec.actions" -> "FindingSpec"
        # or "FindingSpec.actions.policy_uuids" -> "Actions"
        parts = model_path.split(".")
        if len(parts) >= 2:
            # For nested paths, try to infer the model class
            # "FindingSpec.actions.policy_uuids" -> "Actions"
            if parts[1] in [
                "actions",
                "finding_metadata",
                "fixing_patch",
                "source_code_version",
            ]:
                # Map field names to model classes
                field_to_model = {
                    "actions": "Actions",
                    "finding_metadata": "FindingMetadata",
                    "fixing_patch": "FixingPatch",
                    "source_code_version": "SourceCodeVersion",
                }
                return field_to_model.get(parts[1], parts[0])
            return parts[0]
        return model_path

    def issue_exists(
        self, field_path: str, existing_issues: List[Dict]
    ) -> Optional[int]:
        """Check if an issue already exists for this field path."""
        for issue in existing_issues:
            if field_path in issue.get("title", "") or field_path in issue.get(
                "body", ""
            ):
                return issue.get("number")
        return None

    def _generate_example_fix(
        self, resource_name: str, model_class: str, field: str, nested_depth: int
    ) -> str:
        """Generate example code snippet for fixing the drift."""
        if nested_depth == 0:
            # Simple field addition
            return f"""class {model_class}(BaseModel):
    # ... existing fields ...
    {field}: Optional[str] = Field(
        None, description="TODO: Add description from OpenAPI spec"
    )"""
        else:
            # Nested field - may need to create a new model
            return f"""# Option 1: Add to existing nested model
class {model_class}(BaseModel):
    # ... existing fields ...
    {field}: Optional[str] = Field(
        None, description="TODO: Add description from OpenAPI spec"
    )

# Option 2: If nested, may need to create a new model class
# Check OpenAPI spec for the exact structure"""

    def create_issue(self, drift: Dict) -> Optional[Dict]:
        """Create a GitHub issue for a schema drift."""
        field_path = drift["field_path"]
        model_path = drift.get("model_path", drift.get("model", "Unknown"))
        field = drift["field"]
        resource_name = drift.get("resource_name", "Unknown")
        file_path = drift.get("file_path", self.get_resource_file_path(resource_name))
        model_class = self.extract_model_class(model_path)
        nested_depth = drift.get("nested_depth", 0)

        title = f"Schema Drift: {resource_name}.{field_path}"

        # Build OpenAPI reference
        openapi_ref = model_class
        if resource_name != "Unknown":
            openapi_ref = (
                f"v1{resource_name}Spec"
                if "Spec" in model_class
                else f"v1{resource_name}"
            )

        # Build example fix code
        example_fix = self._generate_example_fix(
            resource_name, model_class, field, nested_depth
        )

        body = f"""## Schema Drift Detected

**Resource**: `{resource_name}`
**Model**: `{model_path}`
**Model Class**: `{model_class}`
**Field Path**: `{field_path}`
**Field**: `{field}`
**File to Modify**: `{file_path}`
**Nested Depth**: {nested_depth}
**First Seen**: {drift.get("first_seen", "Unknown")}

### Details

This field was detected in API responses but is not defined in the Pydantic model.

### Action Required

1. Review OpenAPI spec: https://api.endorlabs.com/download/openapiv2.swagger.json or obtain locally by running `.github/scripts/sync_external_docs.py --download-openapi` (writes to `external_docs/openapi-swagger.json`).
   (search for `{openapi_ref}`)
2. Add field to model: `{file_path}` in class `{model_class}`
3. Update drift detection known_fields if applicable
4. Add validation and documentation

### Code Location

- **File**: `{file_path}`
- **Class**: `{model_class}`
- **Field**: `{field}`

### Example Fix

```python
{example_fix}
```

### Related

- Check https://api.endorlabs.com/download/openapiv2.swagger.json (or obtain locally via sync script) for API specification
- Review `{file_path}` for current model definition

### Detection Method

This issue was automatically created by the schema drift detection workflow.
"""

        payload = {
            "title": title,
            "body": body,
            "labels": [self.label, "automated", "api-schema"]
        }

        try:
            response = requests.post(
                f"{self.base_url}/issues",
                headers=self.headers,
                json=payload
            )
            response.raise_for_status()

            issue = response.json()
            logger.info(f"Created issue #{issue['number']}: {title}")
            return issue

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to create issue: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            return None

    def create_issues_from_report(self, report_file: str) -> Dict:
        """Create issues for all new drifts in the report."""
        with open(report_file) as f:
            report = json.load(f)

        existing_issues = self.get_existing_issues()
        new_drifts = [
            d for d in report.get("drifts", [])
            if d.get("status") == "new"
        ]

        created = []
        skipped = []

        for drift in new_drifts:
            field_path = drift["field_path"]

            # Check if issue already exists
            existing_issue_num = self.issue_exists(field_path, existing_issues)
            if existing_issue_num:
                logger.info(
                    f"Skipping {field_path} - issue #{existing_issue_num} exists"
                )
                skipped.append({
                    "drift": drift,
                    "existing_issue": existing_issue_num
                })
                continue

            # Create new issue
            issue = self.create_issue(drift)
            if issue:
                created.append({
                    "drift": drift,
                    "issue_number": issue["number"],
                    "issue_url": issue["html_url"]
                })

        return {
            "created": created,
            "skipped": skipped,
            "total_new_drifts": len(new_drifts)
        }


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Create GitHub issues for schema drift"
    )
    parser.add_argument(
        "--report",
        required=True,
        help="Path to schema drift report JSON file"
    )
    parser.add_argument(
        "--repo",
        default=os.getenv("GITHUB_REPOSITORY"),
        help="GitHub repository (default: GITHUB_REPOSITORY env var)"
    )
    parser.add_argument(
        "--token",
        default=os.getenv("GITHUB_TOKEN"),
        help="GitHub token (default: GITHUB_TOKEN env var)"
    )
    parser.add_argument(
        "--label",
        default="schema-drift",
        help="Label to apply to issues (default: schema-drift)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't create issues, just show what would be created"
    )

    args = parser.parse_args()

    if not args.repo:
        logger.error("Repository not specified. Use --repo or set GITHUB_REPOSITORY")
        return 1

    if not args.token:
        logger.error("GitHub token not specified. Use --token or set GITHUB_TOKEN")
        return 1

    if args.dry_run:
        logger.info("DRY RUN MODE - No issues will be created")

    creator = GitHubIssueCreator(
        repo=args.repo,
        token=args.token,
        label=args.label
    )

    if args.dry_run:
        # Just show what would be created
        with open(args.report) as f:
            report = json.load(f)
        new_drifts = [
            d for d in report.get("drifts", [])
            if d.get("status") == "new"
        ]
        print(f"\nWould create {len(new_drifts)} issues:")
        for drift in new_drifts:
            print(f"  - {drift['field_path']}")
        return 0

    result = creator.create_issues_from_report(args.report)

    print("\n" + "="*60)
    print("GITHUB ISSUE CREATION SUMMARY")
    print("="*60)
    print(f"Total new drifts: {result['total_new_drifts']}")
    print(f"Issues created: {len(result['created'])}")
    print(f"Issues skipped (duplicates): {len(result['skipped'])}")

    if result['created']:
        print("\nCreated issues:")
        for item in result['created']:
            print(f"  #{item['issue_number']}: {item['drift']['field_path']}")
            print(f"    {item['issue_url']}")

    return 0 if result['total_new_drifts'] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

