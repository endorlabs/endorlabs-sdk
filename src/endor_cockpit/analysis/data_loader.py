"""Data loading from Endor API and database persistence.

This module handles loading findings and rules from the Endor API
and persisting them to SQLite3 database.
"""

import json
import logging
import types
from typing import Any, Self

from ..api_client import APIClient
from ..resources.finding import Finding, FindingCategory
from ..resources.semgrep_rule import SemgrepRule
from .database import FindingDatabase

logger = logging.getLogger(__name__)


class FindingDataLoader:
    """Load findings and rules from API and persist to database."""

    def __init__(self, db_path: str) -> None:
        """Initialize data loader.

        Args:
            db_path: Path to SQLite3 database file

        """
        super().__init__()
        self.db_path = db_path
        self.db = FindingDatabase(db_path)

    def load_findings_from_api(
        self,
        client: APIClient,
        namespace: str,
        project_uuids: list[str] | None = None,
    ) -> list[Finding]:
        """Load findings from Endor API.

        Args:
            client: APIClient instance
            namespace: Tenant namespace
            project_uuids: Optional list of project UUIDs to filter by

        Returns:
            List of Finding objects

        """
        from ..resources.finding import list_findings

        logger.info(f"Loading findings from API for namespace: {namespace}")
        findings = []

        try:
            # Filter for SAST findings
            all_findings = list_findings(client, namespace)
            for finding in all_findings:
                # Check if it's a SAST finding
                if (
                    finding.spec.finding_categories
                    and FindingCategory.SAST in finding.spec.finding_categories
                ):
                    # Optionally filter by project
                    if project_uuids and finding.spec.project_uuid not in project_uuids:
                        continue
                    findings.append(finding)

            logger.info(f"Loaded {len(findings)} SAST findings from API")
        except Exception as e:
            logger.error(f"Error loading findings from API: {e}", exc_info=True)
            raise

        return findings

    def load_rules_from_api(
        self, client: APIClient, namespace: str
    ) -> list[SemgrepRule]:
        """Load semgrep rules from Endor API.

        Args:
            client: APIClient instance
            namespace: Tenant namespace

        Returns:
            List of SemgrepRule objects

        """
        from ..resources.semgrep_rule import list_semgrep_rules

        logger.info(f"Loading rules from API for namespace: {namespace}")
        rules = []

        try:
            rules = list_semgrep_rules(client, namespace)
            logger.info(f"Loaded {len(rules)} rules from API")
        except Exception as e:
            logger.error(f"Error loading rules from API: {e}", exc_info=True)
            raise

        return rules

    def extract_rule_id_from_finding(self, finding: Finding) -> str | None:
        """Extract rule_id from finding metadata.

        Args:
            finding: Finding object

        Returns:
            Rule ID if found, None otherwise

        """
        if not finding.spec.finding_metadata:
            return None

        metadata = finding.spec.finding_metadata

        # Try various paths where rule_id might be stored
        # Common paths: source_policy_info.results[].rule_id
        if isinstance(metadata, dict):
            # Check source_policy_info
            source_policy_info = metadata.get("source_policy_info", {})
            if isinstance(source_policy_info, dict):
                results = source_policy_info.get("results", [])
                if isinstance(results, list) and results:
                    # Get first result's rule_id
                    first_result = results[0]
                    if isinstance(first_result, dict):
                        rule_id = first_result.get("rule_id")
                        if rule_id:
                            return rule_id

            # Check for rule_id directly
            rule_id = metadata.get("rule_id")
            if rule_id:
                return rule_id

            # Check for ruleId (camelCase)
            rule_id = metadata.get("ruleId")
            if rule_id:
                return rule_id

        return None

    def extract_finding_metadata(self, finding: Finding) -> dict[str, Any]:
        """Extract metadata fields from finding.

        Args:
            finding: Finding object

        Returns:
            Dictionary with extracted metadata

        """
        metadata = {
            "file_path": None,
            "line_number": None,
            "code_snippet": None,
        }

        if finding.spec.finding_metadata:
            finding_meta = finding.spec.finding_metadata
            if isinstance(finding_meta, dict):
                metadata["file_path"] = finding_meta.get("file_path")
                metadata["line_number"] = finding_meta.get("line_number")
                metadata["code_snippet"] = finding_meta.get("code_snippet")

                # Also check nested structures
                if not metadata["file_path"]:
                    # Check source_policy_info.results[].file_path
                    source_policy_info = finding_meta.get("source_policy_info", {})
                    if isinstance(source_policy_info, dict):
                        results = source_policy_info.get("results", [])
                        if isinstance(results, list) and results:
                            first_result = results[0]
                            if isinstance(first_result, dict):
                                metadata["file_path"] = first_result.get("file_path")
                                metadata["line_number"] = first_result.get(
                                    "line_number"
                                )
                                metadata["code_snippet"] = first_result.get(
                                    "code_snippet"
                                )

        return metadata

    def extract_cwe_from_finding(self, finding: Finding) -> str | None:
        """Extract CWE from finding.

        Args:
            finding: Finding object

        Returns:
            CWE identifier if found, None otherwise

        """
        # Check finding_metadata for CWE
        if finding.spec.finding_metadata:
            metadata = finding.spec.finding_metadata
            if isinstance(metadata, dict):
                cwe = metadata.get("cwe")
                if cwe:
                    return str(cwe)

        # Check summary/description for CWE pattern
        if finding.spec.summary:
            import re

            cwe_match = re.search(r"CWE-(\d+)", finding.spec.summary)
            if cwe_match:
                return f"CWE-{cwe_match.group(1)}"

        return None

    def extract_language_from_finding(self, finding: Finding) -> str | None:
        """Extract language from finding.

        Args:
            finding: Finding object

        Returns:
            Language identifier if found, None otherwise

        """
        if finding.spec.finding_metadata:
            metadata = finding.spec.finding_metadata
            if isinstance(metadata, dict):
                language = metadata.get("language")
                if language:
                    return str(language)

        # Try to infer from file_path
        file_path = self.extract_finding_metadata(finding).get("file_path")
        if file_path:
            if file_path.endswith(".java"):
                return "java"
            elif file_path.endswith(".py"):
                return "python"
            elif file_path.endswith(".js") or file_path.endswith(".ts"):
                return "javascript"
            elif file_path.endswith(".go"):
                return "go"

        return None

    def save_findings_to_db(
        self, findings: list[Finding], labels: dict[str, str] | None = None
    ) -> None:
        """Save findings to database.

        Args:
            findings: List of Finding objects
            labels: Optional dictionary mapping finding UUID to label (TP/FP/FN/TN)

        """
        logger.info(f"Saving {len(findings)} findings to database")
        labels = labels or {}

        for finding in findings:
            rule_id = self.extract_rule_id_from_finding(finding)
            finding_meta = self.extract_finding_metadata(finding)
            cwe = self.extract_cwe_from_finding(finding)
            language = self.extract_language_from_finding(finding)
            label = labels.get(finding.uuid)

            # Extract rule name from finding metadata or summary
            rule_name = None
            if finding.spec.finding_metadata:
                metadata = finding.spec.finding_metadata
                if isinstance(metadata, dict):
                    rule_name = metadata.get("rule_name")

            if not rule_name and finding.meta.name:
                rule_name = finding.meta.name

            meta = finding.spec.finding_metadata
            self.db.insert_finding(
                uuid=finding.uuid,
                rule_id=rule_id,
                rule_name=rule_name,
                file_path=finding_meta.get("file_path"),
                line_number=finding_meta.get("line_number"),
                code_snippet=finding_meta.get("code_snippet"),
                finding_metadata=(
                    meta.model_dump(mode="json") if meta is not None else None
                ),
                cwe=cwe,
                language=language,
                label=label,
                project_uuid=finding.spec.project_uuid,
                level=str(finding.spec.level) if finding.spec.level else None,
                summary=finding.spec.summary,
                description=finding.meta.description if finding.meta else None,
            )

        logger.info("Finished saving findings to database")

    def save_rules_to_db(self, rules: list[SemgrepRule]) -> None:
        """Save rules to database and extract patterns.

        Args:
            rules: List of SemgrepRule objects

        """
        logger.info(f"Saving {len(rules)} rules to database")

        for rule in rules:
            if not rule.spec or not rule.spec.rule:
                continue

            native_rule = rule.spec.rule
            rule_id = native_rule.id
            if not rule_id:
                logger.warning(f"Rule {rule.uuid} has no rule_id, skipping")
                continue

            # Extract CWE from metadata
            cwe = None
            if native_rule.metadata and native_rule.metadata.cwe:
                cwe_list = native_rule.metadata.cwe
                if cwe_list:
                    cwe = cwe_list[0]  # Use first CWE

            # Extract language
            language = None
            if native_rule.languages:
                language = native_rule.languages[0]  # Use first language

            # Save rule
            rule_json = native_rule.model_dump() if native_rule else None
            self.db.insert_rule(
                uuid=rule.uuid,
                rule_id=rule_id,
                rule_name=rule.meta.name if rule.meta else None,
                language=language,
                cwe=cwe,
                yaml_content=rule.spec.yaml,
                rule_json=rule_json,
                disabled=rule.spec.disabled or False,
            )

        logger.info("Finished saving rules to database")

    def load_ground_truth(self, file_path: str) -> None:
        """Load ground truth labels from JSON file.

        Args:
            file_path: Path to ground truth JSON file

        """
        logger.info(f"Loading ground truth from {file_path}")

        try:
            with open(file_path, encoding="utf-8") as f:
                data = json.load(f)

            if not isinstance(data, list):
                logger.error("Ground truth file must contain a JSON array")
                return

            for entry in data:
                file_path_gt = entry.get("file_path")
                line_number = entry.get("line_number")
                cwe = entry.get("cwe")
                label = entry.get("label")
                language = entry.get("language")

                if file_path_gt and line_number is not None and cwe and label:
                    self.db.insert_ground_truth(
                        file_path=file_path_gt,
                        line_number=line_number,
                        cwe=cwe,
                        label=label,
                        language=language or "unknown",
                    )

            logger.info("Finished loading ground truth")
        except Exception as e:
            logger.error(f"Error loading ground truth: {e}", exc_info=True)
            raise

    def close(self) -> None:
        """Close database connection."""
        self.db.close()

    def __enter__(self) -> Self:
        """Context manager entry."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> None:
        """Context manager exit."""
        self.close()
