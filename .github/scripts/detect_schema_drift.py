#!/usr/bin/env python3
"""
Detect Schema Drift from Test Output

This script runs integration tests and captures schema drift warnings/errors,
then generates a report that can be used to create GitHub issues.

Model consistency: compares Pydantic model field coverage vs OpenAPI spec
(model-enumerator uses Pydantic introspection; no tree-sitter).

Usage:
    python .github/scripts/detect_schema_drift.py --run-tests
    python .github/scripts/detect_schema_drift.py --check-existing
    python .github/scripts/detect_schema_drift.py --model-consistency --output-format json
"""

import argparse
import json
import logging
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

# Repo root and src so endorlabs can be imported when script is run from repo root
_repo_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_repo_root))
sys.path.insert(0, str(_repo_root / "src"))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class SchemaDriftDetector:
    """Detect schema drift from test execution and validation errors."""

    def __init__(self, output_file: str = "schema_drift_report.json"):
        self.output_file = Path(output_file)
        self.drift_report = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "drifts": [],
            "validation_errors": [],
            "summary": {}
        }
        self.known_drifts = self._load_known_drifts()

    def _load_known_drifts(self) -> Dict:
        """Load previously tracked drifts to avoid duplicates."""
        if self.output_file.exists():
            try:
                with open(self.output_file) as f:
                    data = json.load(f)
                    return {
                        drift["field_path"]: drift
                        for drift in data.get("drifts", [])
                    }
            except Exception as e:
                logger.warning(f"Could not load existing drift report: {e}")
        return {}

    def run_tests(self, test_path: str = "tests/") -> Dict:
        """Run integration tests and capture schema drift."""
        logger.info("Running integration tests to detect schema drift...")
        logger.info(f"Test path: {test_path}")
        logger.info("=" * 80)

        # Run pytest with verbose output to capture warnings
        # Remove -q flag to show progress, use -v for verbose output
        cmd = [
            sys.executable, "-m", "pytest",
            test_path,
            "-v",  # Verbose output
            "--tb=short",  # Short traceback format
            "-W", "default::UserWarning",  # Capture warnings
            "--durations=10",  # Show 10 slowest tests
            "-ra",  # Show extra test summary info
        ]

        env = os.environ.copy()
        env["PYTHONWARNINGS"] = "default"

        try:
            # Use Popen to stream output in real-time while capturing it
            logger.info("Starting test execution (output will stream below)...")
            logger.info(f"Command: {' '.join(cmd)}")
            logger.info("-" * 80)

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # Merge stderr into stdout
                text=True,
                env=env,
                bufsize=1,  # Line buffered
                universal_newlines=True
            )

            # Collect output while streaming
            output_lines = []
            exit_code = None
            timeout_seconds = 600  # 10 minutes
            start_time = time.time()

            # Stream output in real-time with timeout handling
            def check_timeout():
                elapsed = time.time() - start_time
                if elapsed > timeout_seconds:
                    logger.error(
                        f"Test execution exceeded timeout of {timeout_seconds} seconds"
                    )
                    process.kill()
                    return True
                return False

            # Stream output in real-time
            while True:
                # Check for timeout periodically
                if check_timeout():
                    raise subprocess.TimeoutExpired(cmd, timeout_seconds)

                # Read line (non-blocking check)
                line = process.stdout.readline()
                if not line:
                    # Check if process is still running
                    if process.poll() is not None:
                        break
                    # Process still running but no output yet, wait a bit
                    time.sleep(0.1)
                    continue

                # Print immediately so user sees progress
                print(line, end='', flush=True)
                output_lines.append(line)

            # Wait for process to complete
            exit_code = process.wait()

            logger.info("-" * 80)
            elapsed_time = time.time() - start_time
            logger.info(
                f"Test execution completed in {elapsed_time:.1f} seconds "
                f"with exit code: {exit_code}"
            )

            # Combine all output
            full_output = ''.join(output_lines)

            # Parse output for schema drift warnings
            logger.info("Parsing test output for schema drift warnings...")
            drifts = self._parse_drift_warnings(full_output)

            # Parse validation errors
            logger.info("Parsing validation errors...")
            validation_errors = self._parse_validation_errors(full_output)

            return {
                "drifts": drifts,
                "validation_errors": validation_errors,
                "test_exit_code": exit_code,
                "test_output": full_output
            }

        except subprocess.TimeoutExpired:
            logger.error("Test execution timed out after 10 minutes")
            return {"error": "Test execution timed out"}
        except Exception as e:
            logger.error(f"Error running tests: {e}", exc_info=True)
            return {"error": str(e)}

    def _parse_drift_warnings(self, output: str) -> List[Dict]:
        """Parse schema drift warnings from test output."""
        drifts = []

        # Pattern for schema drift warnings with resource context
        # Matches: "API Schema Drift Detected in {Resource}.{Model}.{Field}:
        # Unknown fields found: {fields}"
        # or: "API Schema Drift Detected in {Model}.{Field}:
        # Unknown fields found: {fields}" (legacy)
        pattern = re.compile(
            r"API Schema Drift Detected in (?:([^.]+)\.)?([^:]+): "
            r"Unknown fields found: ([^.]+)"
        )

        for match in pattern.finditer(output):
            resource_name = match.group(1).strip() if match.group(1) else None
            model_path = match.group(2).strip()
            fields_str = match.group(3).strip()
            fields = [f.strip() for f in fields_str.split(",")]

            # Extract model name and field name from model_path
            # Format: "ResourceSpec.field" or "Resource.field" or "Model.field"
            model_parts = model_path.split(".")
            if len(model_parts) >= 2:
                model_name = ".".join(model_parts[:-1])
                base_field = model_parts[-1]
            else:
                model_name = model_path
                base_field = None

            # Infer resource name from model name if not provided
            if not resource_name:
                # Try to extract from model name (e.g., "FindingSpec" -> "Finding")
                if model_name.endswith("Spec"):
                    resource_name = model_name[:-4]
                elif "." in model_name:
                    # Handle nested paths like "FindingSpec.actions"
                    parts = model_name.split(".")
                    resource_name = parts[0].replace("Spec", "")
                else:
                    resource_name = model_name

            # Determine file path based on resource name
            file_path = self._get_resource_file_path(resource_name)

            # Calculate nested depth (count of dots in model_path)
            nested_depth = model_path.count(".")

            for field in fields:
                # Build full field path
                if base_field:
                    field_path = f"{model_path}.{field}"
                else:
                    field_path = f"{model_name}.{field}"

                # Check if this is a new drift
                if field_path not in self.known_drifts:
                    drift = {
                        "field_path": field_path,
                        "resource_name": resource_name,
                        "model_path": model_path,
                        "model": model_name,
                        "field": field,
                        "file_path": file_path,
                        "nested_depth": nested_depth,
                        "first_seen": datetime.now(timezone.utc).isoformat(),
                        "status": "new",
                        "issue_number": None
                    }
                    drifts.append(drift)
                    logger.info(
                        f"New drift detected: {field_path} "
                        f"(Resource: {resource_name})"
                    )

        return drifts

    def _get_resource_file_path(self, resource_name: str) -> str:
        """Map resource name to source file path."""
        if not resource_name:
            return "src/endorlabs/models/base.py"

        # Map resource names to their file paths
        resource_file_map = {
            "Finding": "src/endorlabs/resources/finding.py",
            "Policy": "src/endorlabs/resources/policy.py",
            "Project": "src/endorlabs/resources/project.py",
            "Namespace": "src/endorlabs/resources/namespace.py",
            "Repository": "src/endorlabs/resources/repository.py",
            "RepositoryVersion": "src/endorlabs/resources/repository_version.py",
            "PackageVersion": "src/endorlabs/resources/package_version.py",
            "DependencyMetadata": "src/endorlabs/resources/dependency_metadata.py",
            "ScanResult": "src/endorlabs/resources/scan_result.py",
            "LinterResult": "src/endorlabs/resources/linter_result.py",
            "Metric": "src/endorlabs/resources/metric.py",
            "User": "src/endorlabs/resources/user.py",
            "Installation": "src/endorlabs/resources/installation.py",
            "BaseResource": "src/endorlabs/models/base.py",
            "BaseSpec": "src/endorlabs/models/base.py",
        }

        return resource_file_map.get(resource_name, "src/endorlabs/models/base.py")

    def _parse_validation_errors(self, output: str) -> List[Dict]:
        """Parse Pydantic validation errors from test output."""
        errors = []

        # Pattern for validation errors
        pattern = re.compile(
            r"(\d+) validation error for (\w+)\s*\n"
            r"([^\n]+)\s*\n"
            r"([^\n]+)"
        )

        for match in pattern.finditer(output):
            match.group(1)
            model_name = match.group(2)
            field_path = match.group(3).strip()
            error_msg = match.group(4).strip()

            error = {
                "model": model_name,
                "field_path": field_path,
                "error": error_msg,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            errors.append(error)
            logger.warning(f"Validation error: {model_name}.{field_path}")

        return errors

    def generate_report(self, test_results: Dict) -> Dict:
        """Generate comprehensive drift report."""
        self.drift_report.update({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "drifts": test_results.get("drifts", []),
            "validation_errors": test_results.get("validation_errors", []),
            "summary": {
                "new_drifts": len(test_results.get("drifts", [])),
                "validation_errors": len(
                    test_results.get("validation_errors", [])
                ),
                "test_status": (
                    "passed"
                    if test_results.get("test_exit_code") == 0
                    else "failed"
                ),
            }
        })

        # Save report
        with open(self.output_file, "w") as f:
            json.dump(self.drift_report, f, indent=2)

        logger.info(f"Drift report saved to {self.output_file}")
        return self.drift_report

    def get_new_drifts(self) -> List[Dict]:
        """Get drifts that haven't been tracked yet."""
        return [
            drift for drift in self.drift_report.get("drifts", [])
            if drift.get("status") == "new"
        ]


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Detect schema drift from test execution"
    )
    parser.add_argument(
        "--run-tests",
        action="store_true",
        help="Run tests to detect drift"
    )
    parser.add_argument(
        "--test-path",
        default="tests/",
        help="Path to test directory (default: tests/)"
    )
    parser.add_argument(
        "--output",
        default="schema_drift_report.json",
        help="Output file for drift report (default: schema_drift_report.json)"
    )
    parser.add_argument(
        "--check-existing",
        action="store_true",
        help="Check existing drift report without running tests"
    )
    parser.add_argument(
        "--model-consistency",
        action="store_true",
        help="Generate model consistency report (AF Pydantic vs OpenAPI spec)"
    )
    parser.add_argument(
        "--output-format",
        choices=["text", "json", "txt"],
        default="json",
        help="Output format for model consistency report (default: json)"
    )
    parser.add_argument(
        "--spec-path",
        default=None,
        help="Path to OpenAPI spec JSON (default: .endorlabs-context/openapiv2.swagger.json)"
    )
    parser.add_argument(
        "--spec-url",
        default=None,
        help="URL to OpenAPI spec (used if spec-path file missing)"
    )
    parser.add_argument(
        "--consistency-output",
        default="model_consistency_report",
        help="Output file base name for model consistency report (default: model_consistency_report)"
    )

    args = parser.parse_args()

    if args.model_consistency:
        from endorlabs.utils.model_consistency import run_model_consistency_report

        spec_path = args.spec_path
        if spec_path is None:
            spec_path = str(_repo_root / ".endorlabs-context" / "openapiv2.swagger.json")
        spec_url = args.spec_url
        if spec_url is None:
            spec_url = "https://api.endorlabs.com/download/openapiv2.swagger.json"
        report = run_model_consistency_report(
            spec_path=spec_path,
            spec_url=spec_url,
            output_file=args.consistency_output,
            output_format=args.output_format,
            inheritance_aware=True,
        )
        print("\n" + "=" * 60)
        print("MODEL CONSISTENCY REPORT")
        print("=" * 60)
        summary = report["summary"]
        print(f"Missing in AF: {summary['missing_in_sdk_count']}")
        print(f"Extra in AF (resource-specific): {summary['extra_in_sdk_count']}")
        print(f"Resources compared: {summary['resources_compared']}")
        if "shared_sdk_paths_count" in summary:
            print(f"Shared paths (excluded from per-resource extra): {summary['shared_sdk_paths_count']}")  # key from src/
        print(f"Attribute overlap (2+ defs): {summary.get('overlap_attribute_count', 0)}")
        print(f"Same meaning: {summary.get('same_meaning_count', 0)}")
        print(f"Collisions: {summary.get('collisions_count', 0)}")
        collisions = report.get("attribute_overlap_report", {}).get("collisions", [])
        if collisions:
            print("\nCollisions list:")
            for c in collisions:
                print(f"  - {c}")
        return 0

    detector = SchemaDriftDetector(output_file=args.output)

    if args.run_tests:
        test_results = detector.run_tests(args.test_path)
        report = detector.generate_report(test_results)

        # Print summary
        print("\n" + "="*60)
        print("SCHEMA DRIFT DETECTION SUMMARY")
        print("="*60)
        print(f"New drifts detected: {report['summary']['new_drifts']}")
        print(f"Validation errors: {report['summary']['validation_errors']}")
        print(f"Test status: {report['summary']['test_status']}")
        print(f"\nReport saved to: {args.output}")

        if report['summary']['new_drifts'] > 0:
            print("\nNew drifts:")
            for drift in report['drifts']:
                print(f"  - {drift['field_path']}")

        return 0 if report['summary']['new_drifts'] == 0 else 1

    elif args.check_existing:
        if detector.output_file.exists():
            report = json.loads(detector.output_file.read_text())
            detector.drift_report = report  # Load the report into detector
            new_drifts = detector.get_new_drifts()
            print(f"Found {len(new_drifts)} new drifts in existing report")
            if new_drifts:
                print("\nNew drifts:")
                for drift in new_drifts:
                    print(f"  - {drift['field_path']}")
            return 0 if len(new_drifts) == 0 else 1
        else:
            print("No existing drift report found")
            return 1

    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())

