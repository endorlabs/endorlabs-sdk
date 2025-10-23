"""
Init command implementation for Holocron.

Handles workspace initialization for AI agents.
"""

import json
from datetime import datetime
from pathlib import Path

from ..workspace import init_workspace


def init_command(args):
    """Execute the init command."""
    # Check for stale external docs before initialization
    manifest_path = Path(".workspace/holocron_data/vector_db_manifest.json")

    if manifest_path.exists() and not args.force:
        try:
            with open(manifest_path, "r") as f:
                manifest = json.load(f)

            external = manifest.get("external_docs", {})

            # Check OpenAPI spec freshness
            openapi_last = external.get("openapi_spec", {}).get("last_downloaded")
            if openapi_last:
                last_dl = datetime.fromisoformat(openapi_last)
                age_days = (datetime.now() - last_dl).days
                if age_days > 7:
                    print(f"WARNING: OpenAPI spec is {age_days} days old")
                    print(
                        "   Consider refreshing with: uv run python -m holocron "
                        "init --force"
                    )

            # Check user docs freshness
            userdocs_last = external.get("user_docs", {}).get("last_downloaded")
            if userdocs_last:
                last_dl = datetime.fromisoformat(userdocs_last)
                age_days = (datetime.now() - last_dl).days
                if age_days > 7:
                    print(f"WARNING: User docs are {age_days} days old")
                    print(
                        "   Consider refreshing with: uv run python -m holocron "
                        "init --force"
                    )

        except Exception:
            # Ignore errors in freshness check
            pass

    success = init_workspace(force=args.force, verbose=args.verbose)

    if not success:
        exit(1)
