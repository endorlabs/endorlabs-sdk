"""
Init command implementation for Holocron.

Handles workspace initialization for AI agents.
"""

from ..workspace import init_workspace


def init_command(args):
    """Execute the init command."""
    success = init_workspace(force=args.force, verbose=args.verbose)
    
    if not success:
        exit(1)
