"""
Authenticate via browser OAuth and store token for reuse.

This script authenticates once via browser and stores the token
in a local config file that tests can use.
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from endor_cockpit.api_client import APIClient
from endor_cockpit.auth_server import get_token
import yaml


def authenticate_and_store(
    auth_method: str = "browser",
    environment: str = "endorlabs.com",
    browser_name: str = None,
    email: str = None,
    config_file: str = None,
):
    """
    Authenticate via browser and store token in config file.

    Args:
        auth_method: Authentication method ('browser', 'admin', 'google', 'github', 'gitlab', 'email')
        environment: API environment (default: 'endorlabs.com')
        browser_name: Browser name (optional)
        email: Email for email-based auth (required if method='email')
        config_file: Path to config file (default: .endorctl/config.yaml in project root)
    """
    # Determine config file path
    if config_file:
        config_path = Path(config_file)
    else:
        # Store in project root .endorctl/config.yaml
        project_root = Path(__file__).parent.parent
        config_path = project_root / ".endorctl" / "config.yaml"
        config_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"🔐 Authenticating via browser ({auth_method})...")
    print(f"   Browser will open for authentication...")

    # Get token via browser OAuth
    if auth_method == "browser":
        auth_method = "admin"  # Default to admin SSO

    token = get_token(
        timeout=60,  # Longer timeout for manual auth
        environment=environment,
        browser_name=browser_name,
        method=auth_method,
        email=email,
    )

    if not token:
        print("❌ Authentication failed or was cancelled")
        sys.exit(1)

    print(f"✅ Authentication successful!")
    print(f"   Token captured and will be stored in: {config_path}")

    # Load existing config or create new
    config = {}
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}
        except Exception as e:
            print(f"⚠️  Warning: Could not read existing config: {e}")
            config = {}

    # Update config with token and auth method
    config["ENDOR_TOKEN"] = token
    config["ENDOR_AUTH_METHOD"] = "browser"  # Use browser mode with stored token
    if "ENDOR_API" not in config:
        # Extract API URL from environment
        if environment == "endorlabs.com":
            config["ENDOR_API"] = "https://api.endorlabs.com"
        else:
            config["ENDOR_API"] = f"https://api.{environment}"

    # Save config
    try:
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)
        print(f"✅ Token stored successfully in {config_path}")
        print(f"\n📝 You can now run tests without re-authenticating:")
        print(f"   uv run pytest ...")
        print(f"\n💡 The token will be automatically used from the config file.")
    except Exception as e:
        print(f"❌ Failed to save config: {e}")
        sys.exit(1)

    # Verify the token works
    print(f"\n🔍 Verifying token...")
    try:
        client = APIClient(token=token, auth_method="browser")
        # Try a simple API call to verify
        response = client.get("/meta/version")
        if response.status_code == 200:
            version_data = response.json()
            print(f"✅ Token verified! API version: {version_data.get('version', 'unknown')}")
        else:
            print(f"⚠️  Token stored but verification returned status {response.status_code}")
    except Exception as e:
        print(f"⚠️  Token stored but verification failed: {e}")
        print(f"   You may need to re-authenticate.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Authenticate via browser OAuth and store token for reuse"
    )
    parser.add_argument(
        "--method",
        choices=["browser", "admin", "google", "github", "gitlab", "email"],
        default="browser",
        help="Authentication method (default: browser/admin SSO)",
    )
    parser.add_argument(
        "--environment",
        default="endorlabs.com",
        help="API environment (default: endorlabs.com)",
    )
    parser.add_argument(
        "--browser",
        help="Browser name (optional, uses default if not specified)",
    )
    parser.add_argument(
        "--email",
        help="Email address (required for email-based auth)",
    )
    parser.add_argument(
        "--config",
        help="Path to config file (default: .endorctl/config.yaml in project root)",
    )

    args = parser.parse_args()

    if args.method == "email" and not args.email:
        print("❌ Error: --email is required for email-based authentication")
        sys.exit(1)

    authenticate_and_store(
        auth_method=args.method,
        environment=args.environment,
        browser_name=args.browser,
        email=args.email,
        config_file=args.config,
    )
