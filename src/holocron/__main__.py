#!/usr/bin/env python3
"""
Holocron CLI Interface

Entry point for the holocron knowledge base system.
Provides commands for workspace initialization, knowledge sync, and querying.
"""

import argparse
import sys

from .commands.init import init_command
from .commands.query import query_command
from .commands.sync import sync_command


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="holocron",
        description="Holocron Knowledge Base System for Endor Cockpit",
        epilog="For more information, see docs/protocols/holocron-setup.md",
    )

    subparsers = parser.add_subparsers(
        dest="command", help="Available commands", required=True
    )

    # Init command
    init_parser = subparsers.add_parser(
        "init", help="Initialize workspace and knowledge base"
    )
    init_parser.add_argument(
        "--force",
        action="store_true",
        help="Force reinitialization even if workspace exists",
    )
    init_parser.add_argument(
        "--verbose", action="store_true", help="Enable verbose output"
    )

    # Sync command
    sync_parser = subparsers.add_parser(
        "sync", help="Sync knowledge base from documentation"
    )
    sync_parser.add_argument(
        "--rebuild", action="store_true", help="Force full rebuild of vector database"
    )
    sync_parser.add_argument(
        "--verbose", action="store_true", help="Enable verbose output"
    )

    # Query command
    query_parser = subparsers.add_parser("query", help="Query the knowledge base")
    query_parser.add_argument(
        "query_text",
        nargs="?",
        help="Query text (if not provided, enters interactive mode)",
    )
    query_parser.add_argument(
        "--results",
        type=int,
        default=5,
        help="Number of results to return (default: 5)",
    )
    query_parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )
    query_parser.add_argument(
        "--max-content",
        type=int,
        default=500,
        help="Maximum content length to display (default: 500)",
    )

    args = parser.parse_args()

    try:
        if args.command == "init":
            init_command(args)
        elif args.command == "sync":
            sync_command(args)
        elif args.command == "query":
            query_command(args)
        else:
            parser.print_help()
            sys.exit(1)

    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        if args.verbose if hasattr(args, "verbose") else False:
            import traceback

            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
