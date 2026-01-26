"""
Ensure ENDOR_TOKEN is set and valid.

This script validates the existing ENDOR_TOKEN environment variable or
triggers browser authentication if needed. The token is written to .env
for uv to automatically load.
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from endor_cockpit.api_client import APIClient
from endor_cockpit.auth_server import get_token
import requests


def validate_token(token: str, base_url: str = "https://api.endorlabs.com") -> bool:
    """Validate that a token is valid by making a test API call."""
    try:
        response = requests.get(
            f"{base_url}/meta/version",
            headers={"Authorization": f"Bearer {token}"},
            timeout=5,
        )
        return response.status_code == 200
    except Exception:
        return False


def ensure_token(
    auth_method: str = "admin",
    environment: str = "endorlabs.com",
    browser_name: str = None,
    email: str = None,
    quiet: bool = False,
) -> str:
    """
    Ensure ENDOR_TOKEN is set and valid.

    Args:
        auth_method: Authentication method ('admin', 'google', 'github', 'gitlab', 'email')
        environment: API environment (default: 'endorlabs.com')
        browser_name: Browser name (optional)
        email: Email for email-based auth (required if method='email')
        quiet: If True, suppress output (useful for automation)

    Returns:
        Valid token string
    """
    project_root = Path(__file__).parent.parent
    env_file = project_root / ".env"

    # Determine base URL
    base_url = os.getenv("ENDOR_API", f"https://api.{environment}")
    if environment == "endorlabs.com":
        base_url = "https://api.endorlabs.com"

    # Check existing token from environment
    existing_token = os.getenv("ENDOR_TOKEN")
    if existing_token:
        if validate_token(existing_token, base_url):
            if not quiet:
                print("✅ ENDOR_TOKEN is valid")
            return existing_token
        elif not quiet:
            print("⚠️  Existing ENDOR_TOKEN is invalid, re-authenticating...")

    # Check .env file for token
    if env_file.exists():
        try:
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("ENDOR_TOKEN="):
                        token = line.split("=", 1)[1].strip().strip('"').strip("'")
                        if validate_token(token, base_url):
                            if not quiet:
                                print("✅ Found valid token in .env file")
                            return token
                        break
        except Exception:
            pass

    # Need to authenticate
    if not quiet:
        print(f"🔐 Authenticating via browser ({auth_method})...")
        print("   Browser will open for authentication...")

    token = get_token(
        timeout=60,
        environment=environment,
        browser_name=browser_name,
        method=auth_method,
        email=email,
    )

    if not token:
        print("❌ Authentication failed or was cancelled", file=sys.stderr)
        sys.exit(1)

    if not quiet:
        print("✅ Authentication successful!")

    # Write to .env file for uv to load automatically
    try:
        env_content = []
        if env_file.exists():
            with open(env_file, "r", encoding="utf-8") as f:
                env_content = f.readlines()

        # Update or add ENDOR_TOKEN
        updated = False
        for i, line in enumerate(env_content):
            if line.strip().startswith("ENDOR_TOKEN="):
                env_content[i] = f'ENDOR_TOKEN="{token}"\n'
                updated = True
                break

        if not updated:
            env_content.append(f'ENDOR_TOKEN="{token}"\n')

        # Ensure ENDOR_API is set
        has_api = any(line.strip().startswith("ENDOR_API=") for line in env_content)
        if not has_api:
            env_content.append(f'ENDOR_API="{base_url}"\n')

        with open(env_file, "w", encoding="utf-8") as f:
            f.writelines(env_content)

        if not quiet:
            print(f"✅ Token saved to {env_file}")
            print("   uv will automatically load it when using 'uv run'")
    except Exception as e:
        if not quiet:
            print(f"⚠️  Warning: Could not write to .env file: {e}", file=sys.stderr)

    return token


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Ensure ENDOR_TOKEN is set and valid"
    )
    parser.add_argument(
        "--method",
        choices=["admin", "google", "github", "gitlab", "email"],
        default="admin",
        help="Authentication method (default: admin SSO)",
    )
    parser.add_argument(
        "--environment",
        default="endorlabs.com",
        help="API environment (default: endorlabs.com)",
    )
    parser.add_argument(
        "--browser",
        help="Browser name (optional)",
    )
    parser.add_argument(
        "--email",
        help="Email address (required for email-based auth)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress output (useful for automation)",
    )

    args = parser.parse_args()

    if args.method == "email" and not args.email:
        print("❌ Error: --email is required for email-based authentication", file=sys.stderr)
        sys.exit(1)

    token = ensure_token(
        auth_method=args.method,
        environment=args.environment,
        browser_name=args.browser,
        email=args.email,
        quiet=args.quiet,
    )

    # In quiet mode, just output the token (for automation)
    if args.quiet:
        print(token, end="")
    else:
        # Output helpful information
        print(f"\n💡 To use this token, ensure .env is loaded:")
        print(f"   - With direnv: Already configured in .envrc")
        print(f"   - With uv: Set UV_ENV_FILE=.env or use 'uv run'")
        print(f"   - Manual: export ENDOR_TOKEN='{token[:20]}...'")
