#!/usr/bin/env python3
"""
Environment Validation Script for Endor Cockpit

Validates environment setup and provides actionable error messages.
Used by holocron init and CI workflows to ensure proper configuration.
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict

import requests


class ValidationError(Exception):
    """Custom exception for validation errors."""
    pass


class EnvironmentValidator:
    """Validates environment setup for Endor Cockpit operations."""

    def __init__(self):
        self.results = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "timestamp": None,
            "environment": {}
        }
        self.critical_errors = []
        self.warnings = []

    def validate_environment_variables(self) -> None:
        """Validate required environment variables."""
        required_vars = {
            "OPENAI_API_KEY": (
                "Required for vector embeddings and knowledge base queries"
            ),
            "ENDOR_API": "Endor Labs API endpoint URL",
            "ENDOR_API_CREDENTIALS_KEY": "API authentication key",
            "ENDOR_API_CREDENTIALS_SECRET": "API authentication secret"
        }

        for var, _description in required_vars.items():
            value = os.getenv(var)
            if not value:
                error_msg = (
                    f"{var} not set\n   Fix: export {var}=\"your-value-here\"\n   "
                    "Docs: docs/ESSENTIAL_CONTEXT.md#environment-setup"
                )
                self.critical_errors.append(error_msg)
                self.results["errors"].append({
                    "variable": var,
                    "message": f"{var} not set",
                    "fix": f"export {var}=\"your-value-here\"",
                    "docs": "docs/ESSENTIAL_CONTEXT.md#environment-setup"
                })
            else:
                # Mask sensitive values in output
                masked_value = value[:8] + "..." if len(value) > 8 else "***"
                self.results["environment"][var] = f"{masked_value} (set)"

    def validate_api_connectivity(self) -> None:
        """Test API connectivity with actual ping."""
        endor_api = os.getenv("ENDOR_API")
        if not endor_api:
            return  # Already caught in environment variables check

        try:
            # Test basic connectivity
            response = requests.get(f"{endor_api}/health", timeout=10)
            if response.status_code == 200:
                self.results["environment"]["api_connectivity"] = "healthy"
            else:
                warning = f"API returned status {response.status_code}"
                self.warnings.append(warning)
                self.results["warnings"].append({
                    "message": f"API returned status {response.status_code}",
                    "status_code": response.status_code
                })
        except requests.exceptions.Timeout:
            error_msg = (
                "API connection timeout\n   Fix: Check network connectivity and "
                "ENDOR_API URL\n   "
                "Docs: docs/ESSENTIAL_CONTEXT.md#api-setup"
            )
            self.critical_errors.append(error_msg)
            self.results["errors"].append({
                "message": "API connection timeout",
                "fix": "Check network connectivity and ENDOR_API URL",
                "docs": "docs/ESSENTIAL_CONTEXT.md#api-setup"
            })
        except requests.exceptions.ConnectionError:
            error_msg = (
                "Cannot connect to API\n   Fix: Verify ENDOR_API URL is correct\n   "
                "Docs: docs/ESSENTIAL_CONTEXT.md#api-setup"
            )
            self.critical_errors.append(error_msg)
            self.results["errors"].append({
                "message": "Cannot connect to API",
                "fix": "Verify ENDOR_API URL is correct",
                "docs": "docs/ESSENTIAL_CONTEXT.md#api-setup"
            })
        except Exception as e:
            error_msg = (
                f"API connectivity test failed: {e}\n   Fix: Check ENDOR_API URL and "
                "network\n   "
                "Docs: docs/ESSENTIAL_CONTEXT.md#api-setup"
            )
            self.critical_errors.append(error_msg)
            self.results["errors"].append({
                "message": f"API connectivity test failed: {e}",
                "fix": "Check ENDOR_API URL and network",
                "docs": "docs/ESSENTIAL_CONTEXT.md#api-setup"
            })

    def validate_dependencies(self) -> None:
        """Validate required dependencies are installed."""
        required_packages = {
            "chromadb": "Vector database for knowledge base",
            "openai": "OpenAI API client for embeddings",
            "requests": "HTTP client for API calls",
            "pydantic": "Data validation and serialization"
        }

        missing_packages = []
        for package, _description in required_packages.items():
            try:
                __import__(package)
                self.results["environment"][f"{package}_installed"] = True
            except ImportError:
                missing_packages.append(package)

        if missing_packages:
            packages_str = ", ".join(missing_packages)
            error_msg = (
                f"Missing required packages: {packages_str}\n   Fix: uv pip install -e "
                "'.[rag]'\n   "
                "Docs: docs/ESSENTIAL_CONTEXT.md#dependencies"
            )
            self.critical_errors.append(error_msg)
            self.results["errors"].append({
                "message": f"Missing required packages: {packages_str}",
                "fix": "uv pip install -e '.[rag]'",
                "docs": "docs/ESSENTIAL_CONTEXT.md#dependencies"
            })

    def validate_holocron_data(self) -> None:
        """Check if holocron data directory exists and is initialized."""
        holocron_data_path = Path("holocron_data")
        vector_db_path = holocron_data_path / "vector_db"
        manifest_path = holocron_data_path / "vector_db_manifest.json"

        if not holocron_data_path.exists():
            warning = (
                "Holocron data directory not found\n   Fix: Run 'python -m holocron "
                "init'\n   "
                "Docs: docs/protocols/holocron-setup.md"
            )
            self.warnings.append(warning)
            self.results["warnings"].append({
                "message": "Holocron data directory not found",
                "fix": "Run 'python -m holocron init'",
                "docs": "docs/protocols/holocron-setup.md"
            })
            return

        if not vector_db_path.exists():
            warning = (
                "Vector database not initialized\n   Fix: Run 'python -m holocron "
                "init'\n   "
                "Docs: docs/protocols/holocron-setup.md"
            )
            self.warnings.append(warning)
            self.results["warnings"].append({
                "message": "Vector database not initialized",
                "fix": "Run 'python -m holocron init'",
                "docs": "docs/protocols/holocron-setup.md"
            })
        else:
            self.results["environment"]["vector_db_initialized"] = True

        if not manifest_path.exists():
            warning = (
                "Vector database manifest not found\n   Fix: Run 'python -m holocron "
                "sync'\n   "
                "Docs: docs/protocols/holocron-setup.md"
            )
            self.warnings.append(warning)
            self.results["warnings"].append({
                "message": "Vector database manifest not found",
                "fix": "Run 'python -m holocron sync'",
                "docs": "docs/protocols/holocron-setup.md"
            })
        else:
            self.results["environment"]["manifest_exists"] = True

    def validate_workspace_structure(self) -> None:
        """Check if workspace directory structure is properly set up."""
        workspace_path = Path(".workspace")

        if not workspace_path.exists():
            warning = (
                "Workspace directory not found\n   Fix: Will be created "
                "automatically\n   "
                "Docs: docs/ESSENTIAL_CONTEXT.md#workspace"
            )
            self.warnings.append(warning)
            self.results["warnings"].append({
                "message": "Workspace directory not found",
                "fix": "Will be created automatically",
                "docs": "docs/ESSENTIAL_CONTEXT.md#workspace"
            })
        else:
            self.results["environment"]["workspace_exists"] = True

    def run_validation(self) -> Dict:
        """Run all validation checks."""
        from datetime import datetime
        self.results["timestamp"] = datetime.now().isoformat()

        # Run all validation checks
        self.validate_environment_variables()
        self.validate_api_connectivity()
        self.validate_dependencies()
        self.validate_holocron_data()
        self.validate_workspace_structure()

        # Determine overall validity
        self.results["valid"] = len(self.critical_errors) == 0
        self.results["critical_errors"] = self.critical_errors
        self.results["warnings"] = self.warnings

        return self.results

    def print_results(self) -> None:
        """Print human-readable validation results."""
        print("Environment Validation Results")
        print("=" * 50)

        if self.critical_errors:
            print("\nCritical Errors (must fix):")
            for error in self.critical_errors:
                print(f"\n{error}")

        if self.warnings:
            print("\nWarnings (recommended to fix):")
            for warning in self.warnings:
                print(f"\n{warning}")

        if not self.critical_errors and not self.warnings:
            print("\nEnvironment validation passed!")
            print("   All required components are properly configured.")
        elif not self.critical_errors:
            print("\nEnvironment validation passed with warnings.")
            print(
                "   Core functionality should work, but consider addressing warnings."
            )

        print("\nSummary:")
        print(f"   Critical errors: {len(self.critical_errors)}")
        print(f"   Warnings: {len(self.warnings)}")
        print(f"   Overall status: {'Valid' if self.results['valid'] else 'Invalid'}")

    def save_results(self, output_path: str = ".workspace/validation.log") -> None:
        """Save validation results to file."""
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w") as f:
            json.dump(self.results, f, indent=2)

        print(f"\nValidation results saved to: {output_file}")


def main():
    """Main entry point for validation script."""
    validator = EnvironmentValidator()
    results = validator.run_validation()

    # Print human-readable results
    validator.print_results()

    # Save results to file
    validator.save_results()

    # Exit with appropriate code
    if not results["valid"]:
        sys.exit(1)
    elif results["warnings"]:
        sys.exit(0)  # Warnings are OK
    else:
        sys.exit(0)  # All good


if __name__ == "__main__":
    main()
