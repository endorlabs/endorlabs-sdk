"""
Workspace initialization for Holocron.

Provides functions to validate and initialize the workspace environment
for AI agents working with the Endor Cockpit SDK.
"""

import os
from pathlib import Path
from typing import Optional

from .config import HolocronConfig, load_config
from .manager import VectorDBManager


def create_directories(config: HolocronConfig) -> None:
    """Create necessary directories for holocron."""
    directories = [
        "holocron_data",
        "holocron_data/vector_db",
        ".workspace",
        ".workspace/downloads",
        ".workspace/downloads/user-docs",
        # Add directories from config
        os.path.dirname(config.db_path),
        os.path.dirname(config.manifest_path),
        config.external_docs.openapi_output,
        config.external_docs.sitemap_output,
        config.external_docs.user_docs_output,
    ]

    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)


def init_workspace(  # noqa: C901
    force: bool = False,
    verbose: bool = False,
    download_external: bool = True,
    config: Optional[HolocronConfig] = None,
) -> bool:
    """
    Initialize the workspace for AI agents.

    Performs comprehensive workspace setup including environment validation,
    dependency checking, directory creation, external documentation downloads,
    and knowledge base initialization.

    Args:
        force: Force reinitialization even if workspace exists
        verbose: Enable verbose output
        download_external: Download external documentation (OpenAPI, user docs)
        config: HolocronConfig instance (loads from pyproject.toml if None)

    Returns:
        True if initialization successful, False otherwise
    """
    print("Initializing Holocron workspace...")

    # Load configuration
    if config is None:
        try:
            config = load_config()
        except Exception as e:
            print(f"Warning: Could not load configuration: {e}. Using defaults.")
            from .config import get_default_config

            config = get_default_config()

    # Check if workspace already exists
    if not force and Path(config.db_path).exists():
        print("Workspace already exists. Use --force to reinitialize.")
        return True

    # Validate environment
    if verbose:
        print("Validating environment...")

    # Check required environment variables
    required_vars = ["OPENAI_API_KEY"]
    missing_required = [var for var in required_vars if not os.getenv(var)]

    if missing_required:
        print(f"Missing required environment variables: {', '.join(missing_required)}")
        print("   Set them before running: uv run python -m holocron init")
        return False

    # Check optional environment variables
    optional_vars = [
        "ENDOR_API",
        "ENDOR_API_CREDENTIALS_KEY",
        "ENDOR_API_CREDENTIALS_SECRET",
    ]
    missing_optional = [var for var in optional_vars if not os.getenv(var)]

    if missing_optional:
        print(
            f"⚠️  Optional environment variables not set: {', '.join(missing_optional)}"
        )
        print(
            "   These are needed for API operations but not for knowledge base queries."
        )

    # Validate dependencies
    if verbose:
        print("Validating dependencies...")

    required_packages = ["chromadb", "openai", "requests", "pydantic"]
    missing_packages = []

    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)

    if missing_packages:
        print(f"❌ Missing required packages: {', '.join(missing_packages)}")
        print("   Install with: uv pip install -e '.[holocron]'")
        return False

    # Create directories
    if verbose:
        print("Creating directories...")

    create_directories(config)

    # Ensure holocron_data directory exists for manifest
    Path(os.path.dirname(config.manifest_path)).mkdir(parents=True, exist_ok=True)

    # Download external documentation
    openapi_metadata = None
    pages_count = 0

    if download_external:
        if verbose:
            print("Downloading external documentation...")

        try:
            from .external_docs import (
                download_openapi_spec_with_config,
                download_sitemap_with_config,
                download_user_docs_with_config,
            )

            # Download OpenAPI spec
            print("Downloading OpenAPI specification...")
            openapi_metadata = download_openapi_spec_with_config(
                config.external_docs, force=force
            )

            # Download and parse sitemap
            print("Downloading sitemap.xml...")
            sitemap_urls = download_sitemap_with_config(
                config.external_docs, force=force
            )

            # Download user docs
            print(f"Downloading {len(sitemap_urls)} documentation pages...")
            pages_count = download_user_docs_with_config(
                config.external_docs, sitemap_urls, force=force
            )

            print(f"External documentation downloaded: {pages_count} pages")

        except Exception as e:
            print(f"Warning: Failed to download external documentation: {e}")
            if verbose:
                import traceback

                traceback.print_exc()
            print("Continuing with initialization...")

    # Initialize vector database
    if verbose:
        print("Initializing knowledge base...")

    try:
        manager = VectorDBManager(config=config)

        # Update external docs metadata if we downloaded them
        if download_external and openapi_metadata is not None:
            manager.update_external_docs_metadata(
                openapi_metadata=openapi_metadata, user_docs_count=pages_count
            )

        manager.initialize_db(rebuild=force, verbose=verbose)

        if verbose:
            info = manager.manifest
            print(
                f"Knowledge base initialized with {info.get('total_chunks', 0)} chunks"
            )
            print(f"   From {info.get('total_documents', 0)} documents")
    except Exception as e:
        print(f"Failed to initialize knowledge base: {e}")
        if verbose:
            import traceback

            traceback.print_exc()
        return False

    print("Holocron workspace initialization complete!")
    print(
        "   You can now query the knowledge base with: uv run python -m holocron query"
    )

    return True
