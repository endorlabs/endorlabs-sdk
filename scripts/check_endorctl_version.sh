#!/bin/bash
# Fast check for endorctl version updates (shell version)
#
# This script queries the public Endor Labs API to check if a new version
# of endorctl is available. Designed for cron jobs - fast, lightweight,
# and requires no authentication.
#
# Usage:
#   ./scripts/check_endorctl_version.sh [--state-file PATH] [--notify]
#
# Exit codes:
#   0 - No update available (or first run)
#   1 - Update available
#   2 - Error querying API
#
# Example cron job (check every 6 hours):
#   0 */6 * * * /path/to/scripts/check_endorctl_version.sh --state-file /tmp/endorctl_version.state --notify

set -euo pipefail

STATE_FILE=""
NOTIFY=false
QUIET=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --state-file)
            STATE_FILE="$2"
            shift 2
            ;;
        --notify)
            NOTIFY=true
            shift
            ;;
        --quiet)
            QUIET=true
            shift
            ;;
        *)
            echo "Unknown option: $1" >&2
            exit 2
            ;;
    esac
done

# Query API for latest version
# Try both ClientVersion and Version fields
LATEST_VERSION=$(curl -s --max-time 5 "https://api.endorlabs.com/meta/version" | \
    grep -oE '"ClientVersion":"[^"]*"|"Version":"[^"]*"' | \
    head -1 | \
    sed 's/.*"\([^"]*\)".*/\1/' | \
    sed 's/^v//')

if [ -z "$LATEST_VERSION" ]; then
    [ "$QUIET" = false ] && echo "Error: Could not retrieve latest version" >&2
    exit 2
fi

# If no state file, just print latest version and exit
if [ -z "$STATE_FILE" ]; then
    [ "$QUIET" = false ] && echo "Latest endorctl version: $LATEST_VERSION"
    exit 0
fi

# Load stored version
STORED_VERSION=""
if [ -f "$STATE_FILE" ]; then
    STORED_VERSION=$(cat "$STATE_FILE" | tr -d '\n' | sed 's/^v//')
fi

# If no stored version, save current and exit (first run)
if [ -z "$STORED_VERSION" ]; then
    echo "$LATEST_VERSION" > "$STATE_FILE"
    [ "$QUIET" = false ] && echo "Initialized: Latest version is $LATEST_VERSION"
    exit 0
fi

# Compare versions (simple numeric comparison)
# This works for semantic versions like 1.6.322
compare_versions() {
    local v1="$1"
    local v2="$2"
    
    # Use sort -V for version comparison (available on most systems)
    if command -v sort >/dev/null 2>&1 && sort -V <<< "$v1"$'\n'"$v2" | head -1 | grep -q "^$v1$"; then
        if [ "$v1" = "$v2" ]; then
            return 0  # Equal
        else
            return 1  # v1 < v2
        fi
    else
        # Fallback: simple string comparison (less reliable)
        if [ "$v1" \< "$v2" ]; then
            return 1  # v1 < v2
        elif [ "$v1" = "$v2" ]; then
            return 0  # Equal
        else
            return 2  # v1 > v2
        fi
    fi
}

# Compare versions
if compare_versions "$STORED_VERSION" "$LATEST_VERSION"; then
    # Versions are equal or stored is newer
    if [ "$STORED_VERSION" != "$LATEST_VERSION" ]; then
        [ "$QUIET" = false ] && echo "Warning: Stored version ($STORED_VERSION) is newer than API version ($LATEST_VERSION)" >&2
    else
        [ "$QUIET" = false ] && echo "No update available (current: $LATEST_VERSION)"
    fi
    exit 0
else
    # Update available
    if [ "$NOTIFY" = true ]; then
        echo "endorctl update available: $STORED_VERSION -> $LATEST_VERSION"
        echo "Download: https://api.endorlabs.com/download/latest/endorctl_linux_amd64"
    fi
    echo "$LATEST_VERSION" > "$STATE_FILE"
    exit 1
fi

