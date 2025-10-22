"""
Sync command implementation for Holocron.

Handles knowledge base synchronization from documentation.
"""

import logging

from ..manager import VectorDBManager


def sync_command(args):
    """Execute the sync command."""
    if args.verbose:
        from endor_cockpit.utils.logging_config import setup_logging
        logger = setup_logging("holocron")

    print("Syncing knowledge base...")

    try:
        manager = VectorDBManager()
        manager.initialize_db(rebuild=args.rebuild)

        info = manager.manifest
        print("Knowledge base synced successfully!")
        print(f"   Total chunks: {info.get('total_chunks', 0)}")
        print(f"   Total documents: {info.get('total_documents', 0)}")
        print(f"   Last updated: {info.get('last_updated', 'unknown')}")

    except Exception as e:
        print(f"Failed to sync knowledge base: {e}")
        if args.verbose:
            import traceback

            traceback.print_exc()
        exit(1)
