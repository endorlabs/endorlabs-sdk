"""
Sync command implementation for Holocron.

Handles knowledge base synchronization from documentation.
"""

from ..manager import VectorDBManager


def _handle_list_collections(manager: VectorDBManager) -> None:
    """Handle list collections request."""
    collections = manager.get_available_collections()
    if not collections:
        print(
            "No collections found. Run 'holocron sync' first to populate the "
            "knowledge base."
        )
        return

    print("Available content collections:")
    print("=" * 50)
    for content_type, info in collections.items():
        print(f"{content_type:15} | {info['count']:4d} chunks | {info['description']}")


def _handle_collection_filter(manager: VectorDBManager, args) -> bool:
    """Handle collection filtering. Returns True if successful."""
    if not (args.include or args.exclude):
        return True

    try:
        collection_filter = manager.get_collection_filter(
            include=args.include, exclude=args.exclude
        )
        if collection_filter:
            print(f"Filtering collections: {collection_filter}")
        return True
    except ValueError as e:
        print(f"Error: {e}")
        return False


def _handle_sync_operation(manager: VectorDBManager, args) -> None:
    """Handle the main sync operation."""
    print("Syncing knowledge base...")
    manager.initialize_db(rebuild=args.rebuild)

    info = manager.manifest
    print("Knowledge base synced successfully!")
    print(f"   Total chunks: {info.get('total_chunks', 0)}")
    print(f"   Total documents: {info.get('total_documents', 0)}")
    print(f"   Last updated: {info.get('last_updated', 'unknown')}")

    # Show available collections after sync
    collections = manager.get_available_collections()
    if collections:
        print("\nAvailable content collections:")
        for content_type, info in collections.items():
            print(
                f"   {content_type:15} | {info['count']:4d} chunks | "
                f"{info['description']}"
            )


def sync_command(args):
    """Execute the sync command."""
    if args.verbose:
        pass
        # logger = setup_logging("holocron")  # Not used

    try:
        manager = VectorDBManager()

        # Handle list collections request
        if args.list_collections:
            _handle_list_collections(manager)
            return

        # Build collection filter
        if not _handle_collection_filter(manager, args):
            return

        # Perform sync operation
        _handle_sync_operation(manager, args)

    except Exception as e:
        print(f"Failed to sync knowledge base: {e}")
        if args.verbose:
            import traceback

            traceback.print_exc()
        exit(1)
