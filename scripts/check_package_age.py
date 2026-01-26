#!/usr/bin/env python3
"""
Check if a PyPI package version is newer than a specified age threshold.

This script queries PyPI's JSON API to get the actual upload time of a package
version, since PyPI is proxied from GitHub but the upload times may differ.
"""

import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import requests


def check_package_age(package_name: str, version: str = None, hours: int = 48):
    """Check if a package version is newer than the specified hours.
    
    Args:
        package_name: Name of the package (e.g., 'soupsieve')
        version: Specific version to check (optional, defaults to latest)
        hours: Age threshold in hours (default: 48)
    
    Returns:
        Tuple of (is_newer_than_threshold, upload_time, age)
    """
    try:
        # Query PyPI JSON API
        url = f"https://pypi.org/pypi/{package_name}/json"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Get version (latest if not specified)
        if version:
            target_version = version
        else:
            target_version = data["info"]["version"]
        
        # Get upload time for this version
        releases = data.get("releases", {}).get(target_version, [])
        if not releases:
            print(f"Error: Version {target_version} not found for {package_name}")
            return None, None, None
        
        # Get the first (earliest) upload time for this version
        upload_time_str = releases[0]["upload_time"]
        upload_time = datetime.fromisoformat(upload_time_str.replace("Z", "+00:00"))
        
        # Calculate age
        now = datetime.now(timezone.utc)
        age = now - upload_time
        age_hours = age.total_seconds() / 3600
        
        is_newer = age_hours < hours
        
        return is_newer, upload_time, age
    
    except Exception as e:
        print(f"Error checking package: {e}", file=sys.stderr)
        return None, None, None


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Check if a PyPI package version is newer than threshold"
    )
    parser.add_argument("package", help="Package name (e.g., soupsieve)")
    parser.add_argument("--version", help="Specific version to check")
    parser.add_argument(
        "--hours", type=int, default=48, help="Age threshold in hours (default: 48)"
    )
    
    args = parser.parse_args()
    
    is_newer, upload_time, age = check_package_age(
        args.package, args.version, args.hours
    )
    
    if upload_time is None:
        sys.exit(1)
    
    print(f"Package: {args.package}")
    if args.version:
        print(f"Version: {args.version}")
    print(f"Upload time (PyPI): {upload_time.isoformat()}")
    print(f"Age: {age}")
    print(f"Age in hours: {age.total_seconds() / 3600:.2f}")
    print(f"Is newer than {args.hours} hours: {is_newer}")
    
    sys.exit(0 if is_newer else 1)
