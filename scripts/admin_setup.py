#!/usr/bin/env python3
"""
Admin Setup Script for Endor Cockpit

Consolidated script for environment setup and validation:
- Initialize environment (.env file creation)
- Validate environment configuration
- Quick health check

Example:
  # Initialize environment
  uv run python scripts/admin_setup.py init

  # Validate environment
  uv run python scripts/admin_setup.py validate

  # Quick health check
  uv run python scripts/admin_setup.py check
"""

import argparse
import json
import os
import sys
from datetime import datetime
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
            "environment": {},
        }
        self.critical_errors = []
        self.warnings = []

    def validate_environment_variables(self) -> None:
        """Validate required environment variables."""
        required_vars = {
            "ENDOR_API": "Endor Labs API endpoint URL",
            "ENDOR_API_CREDENTIALS_KEY": "API authentication key",
            "ENDOR_API_CREDENTIALS_SECRET": "API authentication secret",
        }

        for var, _description in required_vars.items():
            value = os.getenv(var)
            if not value:
                error_msg = (
                    f'{var} not set\n   Fix: export {var}="your-value-here"\n   '
                    "Docs: README.md#environment-setup"
                )
                self.critical_errors.append(error_msg)
                self.results["errors"].append(
                    {
                        "variable": var,
                        "message": f"{var} not set",
                        "fix": f'export {var}="your-value-here"',
                        "docs": "README.md#environment-setup",
                    }
                )
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
                self.results["warnings"].append(
                    {
                        "message": f"API returned status {response.status_code}",
                        "status_code": response.status_code,
                    }
                )
        except requests.exceptions.Timeout:
            error_msg = (
                "API connection timeout\n   Fix: Check network connectivity and "
                "ENDOR_API URL\n   "
                "Docs: README.md#environment-setup"
            )
            self.critical_errors.append(error_msg)
            self.results["errors"].append(
                {
                    "message": "API connection timeout",
                    "fix": "Check network connectivity and ENDOR_API URL",
                    "docs": "README.md#environment-setup",
                }
            )
        except requests.exceptions.ConnectionError:
            error_msg = (
                "Cannot connect to API\n   Fix: Verify ENDOR_API URL is correct\n   "
                "Docs: README.md#environment-setup"
            )
            self.critical_errors.append(error_msg)
            self.results["errors"].append(
                {
                    "message": "Cannot connect to API",
                    "fix": "Verify ENDOR_API URL is correct",
                    "docs": "README.md#environment-setup",
                }
            )
        except Exception as e:
            error_msg = (
                f"API connectivity test failed: {e}\n   Fix: Check ENDOR_API URL and "
                "network\n   "
                "Docs: README.md#environment-setup"
            )
            self.critical_errors.append(error_msg)
            self.results["errors"].append(
                {
                    "message": f"API connectivity test failed: {e}",
                    "fix": "Check ENDOR_API URL and network",
                    "docs": "README.md#environment-setup",
                }
            )

    def validate_dependencies(self) -> None:
        """Validate required dependencies are installed."""
        required_packages = {
            "requests": "HTTP client for API calls",
            "pydantic": "Data validation and serialization",
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
                ".\n   "
                "Docs: README.md#installation"
            )
            self.critical_errors.append(error_msg)
            self.results["errors"].append(
                {
                    "message": f"Missing required packages: {packages_str}",
                    "fix": "uv pip install -e .",
                    "docs": "README.md#installation",
                }
            )

    def validate_workspace_structure(self) -> None:
        """Check if workspace directory structure is properly set up."""
        workspace_path = Path(".workspace")

        if not workspace_path.exists():
            warning = (
                "Workspace directory not found\n   Fix: Will be created "
                "automatically\n   "
                "Docs: README.md#workspace"
            )
            self.warnings.append(warning)
            self.results["warnings"].append(
                {
                    "message": "Workspace directory not found",
                    "fix": "Will be created automatically",
                    "docs": "README.md#workspace",
                }
            )
        else:
            self.results["environment"]["workspace_exists"] = True

    def run_validation(self) -> Dict:
        """Run all validation checks."""
        self.results["timestamp"] = datetime.now().isoformat()

        # Run all validation checks
        self.validate_environment_variables()
        self.validate_api_connectivity()
        self.validate_dependencies()
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
        print(
            f"   Overall status: {'Valid' if self.results['valid'] else 'Invalid'}"
        )

    def save_results(self, output_path: str = ".workspace/validation.log") -> None:
        """Save validation results to file."""
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w") as f:
            json.dump(self.results, f, indent=2)

        print(f"\nValidation results saved to: {output_file}")


def create_env_file() -> bool:
    """Create .env file from env.example if it doesn't exist."""
    env_path = Path(".env")
    example_path = Path("env.example")

    if env_path.exists():
        print("✅ .env file already exists")
        return True

    if not example_path.exists():
        print("❌ env.example file not found")
        print("   Creating .env file from template...")
        # Create a basic .env file template
        env_template = """# Endor Cockpit Environment Configuration
# Set the following environment variables:
# ENDOR_API: Endor Labs API endpoint (default: https://api.endorlabs.com)
# ENDOR_NAMESPACE: Tenant namespace for operations
# ENDOR_API_CREDENTIALS_KEY: API authentication key
# ENDOR_API_CREDENTIALS_SECRET: API authentication secret
"""
        with open(env_path, "w") as f:
            f.write(env_template)
        print("✅ Created .env file from template")
        return True

    try:
        # Copy env.example to .env
        with open(example_path, "r") as src, open(env_path, "w") as dst:
            dst.write(src.read())
        print("✅ Created .env file from env.example")
        return True
    except Exception as e:
        print(f"❌ Failed to create .env file: {e}")
        return False


def print_setup_instructions():
    """Print setup instructions for the user."""
    print("\n" + "=" * 60)
    print("🚀 ENVIRONMENT SETUP INSTRUCTIONS")
    print("=" * 60)

    print("\n1. 📝 Edit your .env file with actual values:")
    print("   - ENDOR_API: Your Endor Labs API endpoint")
    print("   - ENDOR_API_CREDENTIALS_KEY: Your API key")
    print("   - ENDOR_API_CREDENTIALS_SECRET: Your API secret")
    print("   - ENDOR_NAMESPACE: Your tenant namespace (optional)")

    print("\n2. 🔄 Reload your terminal or IDE:")
    print("   - VS Code: Restart terminal or reload window")
    print("   - Terminal: Run 'source .envrc' (if using direnv)")

    print("\n3. ✅ Verify setup:")
    print("   - Run: python scripts/admin_setup.py validate")
    print("   - Or run: uv run python scripts/admin_setup.py validate")

    print("\n4. 🧪 Test the setup:")
    print(
        "   - Run: uv run python -c 'from endor_cockpit.api_client import "
        'APIClient; print("SDK import successful")\''
    )


def init_command(args):
    """Initialize environment by creating .env file."""
    print("🔧 Endor Cockpit Environment Setup")
    print("=" * 40)

    if create_env_file():
        print_setup_instructions()
        sys.exit(0)
    else:
        print("❌ Failed to create .env file")
        sys.exit(1)


def validate_command(args):
    """Validate environment configuration."""
    validator = EnvironmentValidator()
    results = validator.run_validation()

    # Print human-readable results
    validator.print_results()

    # Save results if requested
    if args.save:
        validator.save_results(args.save)

    # Exit with appropriate code
    if not results["valid"]:
        sys.exit(1)
    elif results["warnings"]:
        sys.exit(0)  # Warnings are OK
    else:
        sys.exit(0)  # All good


def check_command(args):
    """Quick health check (init + validate)."""
    print("🔍 Quick Health Check")
    print("=" * 40)

    # Check if .env exists
    env_exists = Path(".env").exists()
    if not env_exists:
        print("⚠️  .env file not found")
        print("   Run 'admin_setup.py init' to create it")
        sys.exit(1)

    # Run validation
    validator = EnvironmentValidator()
    results = validator.run_validation()

    if results["valid"]:
        print("✅ Environment check passed!")
        sys.exit(0)
    else:
        print("❌ Environment check failed")
        validator.print_results()
        sys.exit(1)


def main():
    """Main entry point for admin setup script."""
    parser = argparse.ArgumentParser(
        description="Endor Cockpit admin setup and validation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Initialize environment
  python admin_setup.py init

  # Validate environment
  python admin_setup.py validate

  # Quick health check
  python admin_setup.py check

  # Validate and save results
  python admin_setup.py validate --save .workspace/validation.json
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Init command
    init_parser = subparsers.add_parser("init", help="Initialize environment")
    init_parser.set_defaults(func=init_command)

    # Validate command
    validate_parser = subparsers.add_parser(
        "validate", help="Validate environment configuration"
    )
    validate_parser.add_argument(
        "--save",
        help="Save validation results to file",
    )
    validate_parser.set_defaults(func=validate_command)

    # Check command
    check_parser = subparsers.add_parser(
        "check", help="Quick health check (init + validate)"
    )
    check_parser.set_defaults(func=check_command)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()

