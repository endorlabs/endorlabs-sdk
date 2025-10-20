"""
Workspace initialization for Holocron.

Provides functions to validate and initialize the workspace environment
for AI agents working with the Endor Cockpit SDK.
"""

import os
import sys
from pathlib import Path
from typing import List, Tuple

from .manager import VectorDBManager


def validate_environment() -> Tuple[bool, List[str]]:
    """
    Validate that required environment variables are set.
    
    Returns:
        Tuple of (is_valid, missing_variables)
    """
    required_vars = [
        "OPENAI_API_KEY",  # Required for vector embeddings
    ]
    
    optional_vars = [
        "ENDOR_API",
        "ENDOR_API_CREDENTIALS_KEY", 
        "ENDOR_API_CREDENTIALS_SECRET",
    ]
    
    missing_required = [var for var in required_vars if not os.getenv(var)]
    missing_optional = [var for var in optional_vars if not os.getenv(var)]
    
    if missing_required:
        return False, missing_required
    
    if missing_optional:
        print(f"⚠️  Optional environment variables not set: {', '.join(missing_optional)}")
        print("   These are needed for API operations but not for knowledge base queries.")
    
    return True, []


def validate_dependencies() -> bool:
    """
    Validate that required dependencies are installed.
    
    Returns:
        True if all dependencies are available, False otherwise
    """
    required_packages = [
        "chromadb",
        "openai", 
        "requests",
        "pydantic",
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ Missing required packages: {', '.join(missing_packages)}")
        print("   Install with: uv pip install -e '.[rag]'")
        return False
    
    return True


def create_directories() -> None:
    """Create necessary directories for holocron."""
    directories = [
        "holocron_data",
        "holocron_data/vector_db", 
        "workspace",
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)


def init_workspace(force: bool = False, verbose: bool = False) -> bool:
    """
    Initialize the workspace for AI agents.
    
    Performs comprehensive workspace setup including environment validation,
    dependency checking, directory creation, and knowledge base initialization.
    
    Args:
        force: Force reinitialization even if workspace exists
        verbose: Enable verbose output
        
    Returns:
        True if initialization successful, False otherwise
    """
    print("Initializing Holocron workspace...")
    
    # Check if workspace already exists
    if not force and Path("holocron_data").exists():
        print("Workspace already exists. Use --force to reinitialize.")
        return True
    
    # Validate environment
    if verbose:
        print("Validating environment...")
    
    env_valid, missing_vars = validate_environment()
    if not env_valid:
        print(f"Missing required environment variables: {', '.join(missing_vars)}")
        print("   Set them before running: python -m holocron init")
        return False
    
    # Validate dependencies
    if verbose:
        print("Validating dependencies...")
    
    if not validate_dependencies():
        return False
    
    # Create directories
    if verbose:
        print("Creating directories...")
    
    create_directories()
    
    # Initialize vector database
    if verbose:
        print("Initializing knowledge base...")
    
    try:
        manager = VectorDBManager()
        manager.initialize_db(rebuild=force)
        
        if verbose:
            info = manager.manifest
            print(f"Knowledge base initialized with {info.get('total_chunks', 0)} chunks")
            print(f"   From {info.get('total_documents', 0)} documents")
    except Exception as e:
        print(f"Failed to initialize knowledge base: {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        return False
    
    print("Holocron workspace initialization complete!")
    print("   You can now query the knowledge base with: python -m holocron query")
    
    return True
