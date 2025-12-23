#!/usr/bin/env python3
"""
Create GitHub Issues for Schema Drift

This script reads schema drift reports and creates GitHub issues,
avoiding duplicates by checking existing issues.

Usage:
    python scripts/create_drift_issues.py --report schema_drift_report.json
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path
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

    def issue_exists(self, field_path: str, existing_issues: List[Dict]) -> Optional[int]:
        """Check if an issue already exists for this field path."""
        for issue in existing_issues:
            if field_path in issue.get("title", "") or field_path in issue.get("body", ""):
                return issue.get("number")
        return None

    def create_issue(self, drift: Dict) -> Optional[Dict]:
        """Create a GitHub issue for a schema drift."""
        field_path = drift["field_path"]
        model = drift["model"]
        field = drift["field"]
        
        title = f"Schema Drift: {field_path}"
        
        body = f"""## Schema Drift Detected

**Field Path**: `{field_path}`
**Model**: `{model}`
**Field**: `{field}`
**First Seen**: {drift.get("first_seen", "Unknown")}

### Details

This field was detected in API responses but is not defined in the Pydantic model.

### Action Required

1. Review the API response structure for `{model}`
2. Check if this field should be added to the model
3. Update the Pydantic model if needed
4. Add appropriate validation and documentation

### Related

- Check `external_docs/openapi-swagger.json` for API specification
- Review `src/endor_cockpit/resources/{model.lower()}.py` for current model definition

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

