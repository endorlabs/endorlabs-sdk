#!/usr/bin/env python3
"""
Holocron System Validation Script

Validates Holocron knowledge base system health and provides actionable error messages.
Used by holocron init, CI workflows, and troubleshooting to ensure proper system
configuration.
"""

import json
import sys
from pathlib import Path
from typing import Dict

try:
    import chromadb
    # Settings import not used in this script
except ImportError:
    chromadb = None

try:
    from holocron.config import load_config, validate_config
    from holocron.manager import VectorDBManager
    from holocron.query import HolocronQuery
except ImportError:
    # Fallback for when holocron is not installed
    load_config = None
    validate_config = None
    VectorDBManager = None
    HolocronQuery = None


class ValidationError(Exception):
    """Custom exception for validation errors."""

    pass


class HolocronValidator:
    """Validates Holocron system health and configuration."""

    def __init__(self):
        self.results = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "timestamp": None,
            "system": {},
        }
        self.critical_errors = []
        self.warnings = []

    def validate_dependencies(self) -> None:
        """Validate required dependencies are installed."""
        required_packages = {
            "chromadb": "Vector database for knowledge base",
            "openai": "OpenAI API client for embeddings",
            "pydantic": "Data validation and serialization",
        }

        missing_packages = []
        for package, _description in required_packages.items():
            try:
                __import__(package)
                self.results["system"][f"{package}_installed"] = True
            except ImportError:
                missing_packages.append(package)

        if missing_packages:
            packages_str = ", ".join(missing_packages)
            error_msg = (
                f"Missing required packages: {packages_str}\n   Fix: uv pip install -e "
                "'.[holocron]'\n   "
                "Docs: docs/holocron/TROUBLESHOOTING.md#missing-dependencies"
            )
            self.critical_errors.append(error_msg)
            self.results["errors"].append(
                {
                    "message": f"Missing required packages: {packages_str}",
                    "fix": "uv pip install -e '.[holocron]'",
                    "docs": "docs/holocron/TROUBLESHOOTING.md#missing-dependencies",
                }
            )

    def validate_holocron_imports(self) -> None:
        """Validate that holocron modules can be imported."""
        if not load_config:
            error_msg = (
                "Holocron modules not available\n   "
                "Fix: Install holocron dependencies\n   "
                "Docs: docs/holocron/TROUBLESHOOTING.md#missing-dependencies"
            )
            self.critical_errors.append(error_msg)
            self.results["errors"].append(
                {
                    "message": "Holocron modules not available",
                    "fix": "Install holocron dependencies",
                    "docs": "docs/holocron/TROUBLESHOOTING.md#missing-dependencies",
                }
            )
            return

        self.results["system"]["holocron_imports"] = True

    def validate_configuration_file(self) -> None:
        """Validate holocron configuration file."""
        if not load_config:
            return  # Already caught in imports check

        try:
            config = load_config()
            self.results["system"]["config_loaded"] = True

            # Validate configuration
            warnings = validate_config(config)
            if warnings:
                for warning in warnings:
                    self.warnings.append(f"Configuration warning: {warning}")
                    self.results["warnings"].append(
                        {
                            "message": f"Configuration warning: {warning}",
                            "type": "config_warning",
                        }
                    )

        except FileNotFoundError:
            error_msg = (
                "Configuration file not found\n   "
                "Fix: Ensure pyproject.toml exists with [tool.holocron] section\n   "
                "Docs: docs/holocron/CONFIGURATION.md"
            )
            self.critical_errors.append(error_msg)
            self.results["errors"].append(
                {
                    "message": "Configuration file not found",
                    "fix": "Ensure pyproject.toml exists with [tool.holocron] section",
                    "docs": "docs/holocron/CONFIGURATION.md",
                }
            )
        except Exception as e:
            error_msg = (
                f"Configuration loading failed: {e}\n   "
                "Fix: Check pyproject.toml syntax\n   "
                "Docs: docs/holocron/CONFIGURATION.md"
            )
            self.critical_errors.append(error_msg)
            self.results["errors"].append(
                {
                    "message": f"Configuration loading failed: {e}",
                    "fix": "Check pyproject.toml syntax",
                    "docs": "docs/holocron/CONFIGURATION.md",
                }
            )

    def validate_vector_database(self) -> None:
        """Validate vector database initialization and health."""
        if not VectorDBManager or not load_config:
            return  # Already caught in imports check

        try:
            config = load_config()
            manager = VectorDBManager(config=config)

            # Check if database directory exists
            db_path = Path(config.db_path)
            if not db_path.exists():
                warning = (
                    "Vector database directory not found\n   "
                    "Fix: Run 'uv run python -m holocron init'\n   "
                    "Docs: docs/protocols/holocron-setup.md"
                )
                self.warnings.append(warning)
                self.results["warnings"].append(
                    {
                        "message": "Vector database directory not found",
                        "fix": "Run 'uv run python -m holocron init'",
                        "docs": "docs/protocols/holocron-setup.md",
                    }
                )
                return

            self.results["system"]["vector_db_directory"] = True

            # Check if collection exists
            try:
                collections = manager.get_available_collections()
                if not collections:
                    warning = (
                        "No collections found in vector database\n   "
                        "Fix: Run 'uv run python -m holocron sync'\n   "
                        "Docs: docs/protocols/holocron-setup.md"
                    )
                    self.warnings.append(warning)
                    self.results["warnings"].append(
                        {
                            "message": "No collections found in vector database",
                            "fix": "Run 'uv run python -m holocron sync'",
                            "docs": "docs/protocols/holocron-setup.md",
                        }
                    )
                else:
                    self.results["system"]["collections_found"] = len(collections)
                    self.results["system"]["collection_names"] = list(
                        collections.keys()
                    )

                    # Check total chunks
                    total_chunks = sum(
                        info.get("count", 0) for info in collections.values()
                    )
                    if total_chunks == 0:
                        warning = (
                            "No chunks found in collections\n   "
                            "Fix: Run 'uv run python -m holocron sync --rebuild'\n   "
                            "Docs: docs/holocron/TROUBLESHOOTING.md"
                        )
                        self.warnings.append(warning)
                        self.results["warnings"].append(
                            {
                                "message": "No chunks found in collections",
                                "fix": "Run 'uv run python -m holocron sync --rebuild'",
                                "docs": "docs/holocron/TROUBLESHOOTING.md",
                            }
                        )
                    else:
                        self.results["system"]["total_chunks"] = total_chunks

            except Exception as e:
                error_msg = (
                    f"Vector database access failed: {e}\n   "
                    "Fix: Check database integrity\n   "(
                        "Docs: docs/holocron/TROUBLESHOOTING.md#"
                        "chromadb-collection-not-found-error"
                    )
                )
                self.critical_errors.append(error_msg)
                self.results["errors"].append(
                    {
                        "message": f"Vector database access failed: {e}",
                        "fix": "Check database integrity",
                        "docs": (
                            "docs/holocron/TROUBLESHOOTING.md#"
                            "chromadb-collection-not-found-error"
                        ),
                    }
                )

        except Exception as e:
            error_msg = (
                f"Vector database validation failed: {e}\n   "
                "Fix: Check configuration and dependencies\n   "
                "Docs: docs/holocron/TROUBLESHOOTING.md"
            )
            self.critical_errors.append(error_msg)
            self.results["errors"].append(
                {
                    "message": f"Vector database validation failed: {e}",
                    "fix": "Check configuration and dependencies",
                    "docs": "docs/holocron/TROUBLESHOOTING.md",
                }
            )

    def validate_content_type_detection(self) -> None:
        """Validate content type detection is working correctly."""
        if not load_config:
            return  # Already caught in imports check

        try:
            config = load_config()
            from holocron.content_types import ContentTypeRegistry

            registry = ContentTypeRegistry(config.content_types)

            # Test content type detection with sample files
            test_files = [
                "docs/README.md",
                "src/holocron/manager.py",
                ".workspace/downloads/openapi-swagger.json",
                ".workspace/downloads/user-docs/getting-started.md",
            ]

            detection_results = {}
            for file_path in test_files:
                detected_type = registry.detect_content_type(file_path)
                detection_results[file_path] = detected_type

            self.results["system"]["content_type_detection"] = detection_results

            # Check if any files failed detection
            failed_detections = [
                path
                for path, content_type in detection_results.items()
                if content_type is None
            ]

            if failed_detections:
                warning = (
                    f"Content type detection failed for: "
                    f"{', '.join(failed_detections)}\n   "
                    "Fix: Check file patterns in configuration\n   "
                    "Docs: docs/holocron/CONFIGURATION.md#content-type-configuration"
                )
                self.warnings.append(warning)
                self.results["warnings"].append(
                    {
                        "message": (
                            f"Content type detection failed for: "
                            f"{', '.join(failed_detections)}"
                        ),
                        "fix": "Check file patterns in configuration",
                        "docs": (
                            "docs/holocron/CONFIGURATION.md#content-type-configuration"
                        ),
                    }
                )

        except Exception as e:
            error_msg = (
                f"Content type detection validation failed: {e}\n   "
                "Fix: Check content type configuration\n   "
                "Docs: docs/holocron/CONFIGURATION.md"
            )
            self.critical_errors.append(error_msg)
            self.results["errors"].append(
                {
                    "message": f"Content type detection validation failed: {e}",
                    "fix": "Check content type configuration",
                    "docs": "docs/holocron/CONFIGURATION.md",
                }
            )

    def validate_chunking_strategy(self) -> None:
        """Validate chunking strategy configuration."""
        if not load_config:
            return  # Already caught in imports check

        try:
            config = load_config()

            # Check chunk sizes are reasonable
            for content_type, ct_config in config.content_types.items():
                if ct_config.chunk_size <= 0:
                    error_msg = (
                        f"Invalid chunk size for {content_type}: "
                        f"{ct_config.chunk_size}\n   "
                        "Fix: Set positive chunk size\n   "(
                            "Docs: docs/holocron/CONFIGURATION.md#"
                            "chunking-strategy-optimization"
                        )
                    )
                    self.critical_errors.append(error_msg)
                    self.results["errors"].append(
                        {
                            "message": (
                                f"Invalid chunk size for {content_type}: "
                                f"{ct_config.chunk_size}"
                            ),
                            "fix": "Set positive chunk size",
                            "docs": (
                                "docs/holocron/CONFIGURATION.md#"
                                "chunking-strategy-optimization"
                            ),
                        }
                    )

                if ct_config.overlap >= ct_config.chunk_size:
                    error_msg = (
                        f"Overlap too large for {content_type}: {ct_config.overlap} >= "
                        f"{ct_config.chunk_size}\n   "
                        "Fix: Set overlap < chunk_size\n   "(
                            "Docs: docs/holocron/CONFIGURATION.md#"
                            "chunking-strategy-optimization"
                        )
                    )
                    self.critical_errors.append(error_msg)
                    self.results["errors"].append(
                        {
                            "message": (
                                f"Overlap too large for {content_type}: "
                                f"{ct_config.overlap} >= {ct_config.chunk_size}"
                            ),
                            "fix": "Set overlap < chunk_size",
                            "docs": (
                                "docs/holocron/CONFIGURATION.md#"
                                "chunking-strategy-optimization"
                            ),
                        }
                    )

            self.results["system"]["chunking_strategy_valid"] = True

        except Exception as e:
            error_msg = (
                f"Chunking strategy validation failed: {e}\n   Fix: Check chunking "
                "configuration\n   "
                "Docs: docs/holocron/CONFIGURATION.md"
            )
            self.critical_errors.append(error_msg)
            self.results["errors"].append(
                {
                    "message": f"Chunking strategy validation failed: {e}",
                    "fix": "Check chunking configuration",
                    "docs": "docs/holocron/CONFIGURATION.md",
                }
            )

    def validate_cross_platform_paths(self) -> None:
        """Validate cross-platform path handling."""
        if not load_config:
            return  # Already caught in imports check

        try:
            # Test path normalization
            test_paths = [
                "docs/README.md",
                "docs\\README.md",  # Windows style
                "src/holocron/manager.py",
                "src\\holocron\\manager.py",  # Windows style
            ]

            path_results = {}
            for test_path in test_paths:
                normalized = str(Path(test_path))
                path_results[test_path] = normalized

            self.results["system"]["path_normalization"] = path_results

        except Exception as e:
            error_msg = (
                f"Cross-platform path validation failed: {e}\n   "
                "Fix: Check path handling\n   "
                "Docs: docs/holocron/TROUBLESHOOTING.md#path-normalization-requirements"
            )
            self.critical_errors.append(error_msg)
            self.results["errors"].append(
                {
                    "message": f"Cross-platform path validation failed: {e}",
                    "fix": "Check path handling",
                    "docs": (
                        "docs/holocron/TROUBLESHOOTING.md#"
                        "path-normalization-requirements"
                    ),
                }
            )

    def validate_query_functionality(self) -> None:
        """Validate query functionality is working."""
        if not HolocronQuery or not load_config:
            return  # Already caught in imports check

        try:
            config = load_config()
            query = HolocronQuery(config=config)

            # Test basic query
            test_query = "test query"
            results = query.query(test_query, n_results=1)

            if results and "results" in results:
                self.results["system"]["query_functionality"] = True
                self.results["system"]["query_result_count"] = len(results["results"])
            else:
                warning = (
                    "Query functionality not working\n   "
                    "Fix: Check vector database and embeddings\n   "
                    "Docs: docs/holocron/TROUBLESHOOTING.md"
                )
                self.warnings.append(warning)
                self.results["warnings"].append(
                    {
                        "message": "Query functionality not working",
                        "fix": "Check vector database and embeddings",
                        "docs": "docs/holocron/TROUBLESHOOTING.md",
                    }
                )

        except Exception as e:
            error_msg = (
                f"Query functionality validation failed: {e}\n   "
                "Fix: Check query system\n   "
                "Docs: docs/holocron/TROUBLESHOOTING.md"
            )
            self.critical_errors.append(error_msg)
            self.results["errors"].append(
                {
                    "message": f"Query functionality validation failed: {e}",
                    "fix": "Check query system",
                    "docs": "docs/holocron/TROUBLESHOOTING.md",
                }
            )

    def run_validation(self) -> Dict:
        """Run all validation checks."""
        from datetime import datetime

        self.results["timestamp"] = datetime.now().isoformat()

        # Run all validation checks
        self.validate_dependencies()
        self.validate_holocron_imports()
        self.validate_configuration_file()
        self.validate_vector_database()
        self.validate_content_type_detection()
        self.validate_chunking_strategy()
        self.validate_cross_platform_paths()
        self.validate_query_functionality()

        # Determine overall validity
        self.results["valid"] = len(self.critical_errors) == 0
        self.results["critical_errors"] = self.critical_errors
        self.results["warnings"] = self.warnings

        return self.results

    def print_results(self) -> None:
        """Print human-readable validation results."""
        print("Holocron System Validation Results")
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
            print("\nHolocron system validation passed!")
            print("   All components are properly configured and working.")
        elif not self.critical_errors:
            print("\nHolocron system validation passed with warnings.")
            print(
                "   Core functionality should work, but consider addressing warnings."
            )

        print("\nSummary:")
        print(f"   Critical errors: {len(self.critical_errors)}")
        print(f"   Warnings: {len(self.warnings)}")
        print(f"   Overall status: {'Valid' if self.results['valid'] else 'Invalid'}")

    def save_results(
        self, output_path: str = ".workspace/holocron_validation.log"
    ) -> None:
        """Save validation results to file."""
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w") as f:
            json.dump(self.results, f, indent=2)

        print(f"\nValidation results saved to: {output_file}")


def main():
    """Main entry point for validation script."""
    import argparse

    parser = argparse.ArgumentParser(description="Validate Holocron system health")
    parser.add_argument(
        "--check-config",
        action="store_true",
        help="Only check configuration",
    )
    parser.add_argument(
        "--check-database",
        action="store_true",
        help="Only check database",
    )
    parser.add_argument(
        "--check-chunking",
        action="store_true",
        help="Only check chunking",
    )
    parser.add_argument(
        "--output",
        help="Output file path for results",
    )

    args = parser.parse_args()

    validator = HolocronValidator()
    results = validator.run_validation()

    # Print human-readable results
    validator.print_results()

    # Save results to file
    output_path = args.output or ".workspace/holocron_validation.log"
    validator.save_results(output_path)

    # Exit with appropriate code
    if not results["valid"]:
        sys.exit(1)
    elif results["warnings"]:
        sys.exit(0)  # Warnings are OK
    else:
        sys.exit(0)  # All good


if __name__ == "__main__":
    main()
