#!/usr/bin/env python3
"""
Detect Schema Drift from Test Output

This script runs integration tests and captures schema drift warnings/errors,
then generates a report that can be used to create GitHub issues.

Usage:
    python scripts/detect_schema_drift.py --run-tests
    python scripts/detect_schema_drift.py --check-existing
"""

import argparse
import json
import logging
import os
import re
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

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
        
        # Run pytest with verbose output to capture warnings
        cmd = [
            sys.executable, "-m", "pytest",
            test_path,
            "-v",
            "--tb=short",
            "-W", "default::UserWarning",  # Capture warnings
            "-q"  # Quiet mode but still show warnings
        ]
        
        env = os.environ.copy()
        env["PYTHONWARNINGS"] = "default"
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                env=env,
                timeout=600  # 10 minute timeout
            )
            
            # Parse output for schema drift warnings
            drifts = self._parse_drift_warnings(result.stdout + result.stderr)
            
            # Parse validation errors
            validation_errors = self._parse_validation_errors(
                result.stdout + result.stderr
            )
            
            return {
                "drifts": drifts,
                "validation_errors": validation_errors,
                "test_exit_code": result.returncode,
                "test_output": result.stdout + result.stderr
            }
            
        except subprocess.TimeoutExpired:
            logger.error("Test execution timed out")
            return {"error": "Test execution timed out"}
        except Exception as e:
            logger.error(f"Error running tests: {e}")
            return {"error": str(e)}

    def _parse_drift_warnings(self, output: str) -> List[Dict]:
        """Parse schema drift warnings from test output."""
        drifts = []
        
        # Pattern for schema drift warnings with resource context
        # Matches: "API Schema Drift Detected in {Resource}.{Model}.{Field}: Unknown fields found: {fields}"
        # or: "API Schema Drift Detected in {Model}.{Field}: Unknown fields found: {fields}" (legacy)
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
                    logger.info(f"New drift detected: {field_path} (Resource: {resource_name})")
        
        return drifts
    
    def _get_resource_file_path(self, resource_name: str) -> str:
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
            error_count = match.group(1)
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
                "validation_errors": len(test_results.get("validation_errors", [])),
                "test_status": "passed" if test_results.get("test_exit_code") == 0 else "failed"
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
    
    args = parser.parse_args()
    
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

