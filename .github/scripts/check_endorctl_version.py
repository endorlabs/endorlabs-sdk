#!/usr/bin/env python3
"""Fast check for endorctl version updates.

This script queries the public Endor Labs API to check if a new version
of endorctl is available. Designed for cron jobs - fast, lightweight,
and requires no authentication.

Usage:
    python .github/scripts/check_endorctl_version.py [--state-file PATH] [--notify]

The script:
1. Queries https://api.endorlabs.com/meta/version (public endpoint)
2. Extracts the latest version number
3. Compares with stored state (if --state-file provided)
4. Exits with code 0 if no update, 1 if update available
5. Optionally sends notification (if --notify provided)

Example cron job (check every 6 hours):
    0 */6 * * * /path/to/python /path/to/.github/scripts/check_endorctl_version.py \\
        --state-file /tmp/endorctl_version.state --notify
"""

import argparse
import sys
import time
from pathlib import Path

import httpx


def get_latest_version(
    *,
    attempts: int = 3,
    backoff_seconds: float = 1.0,
) -> str | None:
    """Query the public Endor Labs API for the latest endorctl version.

    Returns:
        Version string (e.g., "v1.6.322") or None if query fails
    """
    for attempt in range(1, attempts + 1):
        try:
            # Public endpoint - no authentication required
            response = httpx.get(
                "https://api.endorlabs.com/meta/version",
                timeout=5,  # Fast timeout for cron job
            )
            response.raise_for_status()

            data = response.json()

            # Try both field names (documentation shows both)
            version = data.get("ClientVersion") or data.get("Version")

            if version:
                # Remove 'v' prefix if present for consistent comparison
                return version.lstrip("v")

            return None
        except Exception as e:
            if attempt == attempts:
                message = (
                    f"Error querying version API after {attempts} attempts: {e}"
                )
                print(message, file=sys.stderr)
                return None
            time.sleep(backoff_seconds * attempt)


def load_stored_version(state_file: Path) -> str | None:
    """Load the last known version from state file."""
    try:
        if state_file.exists():
            return state_file.read_text().strip()
    except Exception as e:
        print(f"Warning: Could not read state file: {e}", file=sys.stderr)
    return None


def save_version(state_file: Path, version: str) -> None:
    """Save the current version to state file."""
    try:
        state_file.parent.mkdir(parents=True, exist_ok=True)
        state_file.write_text(version)
    except Exception as e:
        print(f"Warning: Could not write state file: {e}", file=sys.stderr)


def compare_versions(current: str, latest: str) -> int:
    """Compare two version strings.

    Returns:
        -1 if current < latest (update available)
        0 if current == latest (no update)
        1 if current > latest (shouldn't happen, but handle gracefully)
    """
    def version_tuple(v: str) -> tuple:
        """Convert version string to tuple for comparison."""
        # Remove 'v' prefix and split by dots
        parts = v.lstrip("v").split(".")
        # Convert to integers, padding with 0s if needed
        return tuple(int(p) if p.isdigit() else 0 for p in parts)

    current_tuple = version_tuple(current)
    latest_tuple = version_tuple(latest)

    if current_tuple < latest_tuple:
        return -1
    elif current_tuple > latest_tuple:
        return 1
    else:
        return 0


def notify_update(old_version: str, new_version: str, method: str = "print") -> None:
    """Notify about version update."""
    message = (
        f"endorctl update available: {old_version} -> {new_version}\n"
        f"Download: https://api.endorlabs.com/download/latest/endorctl_linux_amd64"
    )

    if method == "print":
        print(message)
    elif method == "stderr":
        print(message, file=sys.stderr)
    # Add more notification methods here (email, webhook, etc.) if needed


def _setup_parser() -> argparse.ArgumentParser:
    """Create and configure argument parser."""
    parser = argparse.ArgumentParser(
        description="Fast check for endorctl version updates",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Simple check (just print latest version)
  python .github/scripts/check_endorctl_version.py

  # Check with state file (tracks last known version)
  python .github/scripts/check_endorctl_version.py \\
    --state-file /tmp/endorctl_version.state

  # Check and notify if update available
  python .github/scripts/check_endorctl_version.py \\
    --state-file /tmp/endorctl_version.state --notify

  # Cron job example (check every 6 hours)
  0 */6 * * * /path/to/python /path/to/.github/scripts/check_endorctl_version.py \\
    --state-file /tmp/endorctl_version.state --notify
        """
    )

    parser.add_argument(
        "--state-file",
        type=Path,
        help="Path to state file storing last known version (optional)"
    )
    parser.add_argument(
        "--notify",
        action="store_true",
        help="Print notification if update is available"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress output (only exit code indicates result)"
    )
    parser.add_argument(
        "--attempts",
        type=int,
        default=3,
        help="Number of retries for version API calls (default: 3)",
    )
    parser.add_argument(
        "--backoff-seconds",
        type=float,
        default=1.0,
        help="Linear backoff base between retries (default: 1.0)",
    )
    return parser


def _handle_version_retrieval(
    quiet: bool, *, attempts: int = 3, backoff_seconds: float = 1.0
) -> str | None:
    """Handle API version retrieval and error cases."""
    latest_version = get_latest_version(
        attempts=attempts, backoff_seconds=backoff_seconds
    )
    if not latest_version:
        if not quiet:
            print("Error: Could not retrieve latest version", file=sys.stderr)
        sys.exit(2)  # Error exit code
    return latest_version


def _handle_state_file_logic(
    state_file: Path,
    latest_version: str,
    quiet: bool,
    notify: bool,
) -> None:
    """Handle state file loading, saving, and comparison."""
    stored_version = load_stored_version(state_file)

    # If no stored version, save current and exit (first run)
    if not stored_version:
        save_version(state_file, latest_version)
        if not quiet:
            print(f"Initialized: Latest version is {latest_version}")
        sys.exit(0)

    # Compare versions
    comparison = compare_versions(stored_version, latest_version)

    if comparison < 0:
        # Update available
        if notify:
            notify_update(stored_version, latest_version)
        save_version(state_file, latest_version)
        sys.exit(1)  # Update available
    elif comparison > 0:
        # Stored version is newer (shouldn't happen, but handle gracefully)
        if not quiet:
            print(
                f"Warning: Stored version ({stored_version}) is newer than "
                f"API version ({latest_version})",
                file=sys.stderr
            )
        sys.exit(0)
    else:
        # No update
        if not quiet:
            print(f"No update available (current: {latest_version})")
        sys.exit(0)


def main():
    """Main function."""
    parser = _setup_parser()
    args = parser.parse_args()

    # Get latest version from API
    latest_version = _handle_version_retrieval(
        args.quiet,
        attempts=max(args.attempts, 1),
        backoff_seconds=max(args.backoff_seconds, 0.0),
    )

    # If no state file, just print latest version and exit
    if not args.state_file:
        if not args.quiet:
            print(f"Latest endorctl version: {latest_version}")
        sys.exit(0)

    # Handle state file logic
    _handle_state_file_logic(
        args.state_file, latest_version, args.quiet, args.notify
    )


if __name__ == "__main__":
    main()

