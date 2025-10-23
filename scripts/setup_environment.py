#!/usr/bin/env python3
"""
Environment Setup Script for Endor Cockpit
Creates .env file from template and validates environment configuration.
"""

import os
import sys
from pathlib import Path
from typing import Dict


def create_env_file() -> bool:
    """Create .env file from env.example if it doesn't exist."""
    env_path = Path(".env")
    example_path = Path("env.example")

    if env_path.exists():
        print("✅ .env file already exists")
        return True

    if not example_path.exists():
        print("❌ env.example file not found")
        return False

    try:
        # Copy env.example to .env
        with open(example_path, "r") as src, open(env_path, "w") as dst:
            dst.write(src.read())
        print("✅ Created .env file from env.example")
        return True
    except Exception as e:
        print(f"❌ Failed to create .env file: {e}")
        return False


def validate_environment() -> Dict[str, bool]:
    """Validate that required environment variables are set."""
    required_vars = [
        "ENDOR_API",
        "ENDOR_API_CREDENTIALS_KEY",
        "ENDOR_API_CREDENTIALS_SECRET",
    ]

    optional_vars = ["ENDOR_NAMESPACE", "AGENT_ID", "OPENAI_API_KEY"]

    results = {}

    print("\n🔍 Validating Environment Variables:")
    print("=" * 50)

    # Check required variables
    print("\n📋 Required Variables:")
    for var in required_vars:
        value = os.getenv(var)
        if value and value != "your-api-key-here" and value != "your-api-secret-here":
            print(f"  ✅ {var}: {'*' * min(len(value), 8)}...")
            results[var] = True
        else:
            print(f"  ❌ {var}: Not set or using placeholder value")
            results[var] = False

    # Check optional variables
    print("\n📋 Optional Variables:")
    for var in optional_vars:
        value = os.getenv(var)
        if value and not value.startswith("your-"):
            print(f"  ✅ {var}: {'*' * min(len(value), 8)}...")
            results[var] = True
        else:
            print(f"  ⚠️  {var}: Not set (optional)")
            results[var] = False

    return results


def check_uv_environment() -> bool:
    """Check if UV environment is properly configured."""
    uv_system_python = os.getenv("UV_SYSTEM_PYTHON", "")

    if uv_system_python == "0":
        print("✅ UV_SYSTEM_PYTHON correctly set to 0")
        return True
    else:
        print(f"⚠️  UV_SYSTEM_PYTHON should be '0', got: {uv_system_python}")
        return False


def print_setup_instructions():
    """Print setup instructions for the user."""
    print("\n" + "=" * 60)
    print("🚀 ENVIRONMENT SETUP INSTRUCTIONS")
    print("=" * 60)

    print("\n1. 📝 Edit your .env file with actual values:")
    print("   - ENDOR_API: Your Endor Labs API endpoint")
    print("   - ENDOR_API_CREDENTIALS_KEY: Your API key")
    print("   - ENDOR_API_CREDENTIALS_SECRET: Your API secret")
    print("   - ENDOR_NAMESPACE: Your tenant namespace (optional)")
    print("   - OPENAI_API_KEY: For RAG functionality (optional)")

    print("\n2. 🔄 Reload your terminal or IDE:")
    print("   - VS Code: Restart terminal or reload window")
    print("   - Terminal: Run 'source .envrc' (if using direnv)")

    print("\n3. ✅ Verify setup:")
    print("   - Run: python scripts/validate_environment.py")
    print("   - Or run: uv run python scripts/validate_environment.py")

    print("\n4. 🧪 Test the setup:")
    print(
        "   - Run: uv run python -c 'from endor_cockpit.api_client import "
        'EndorClient; print("SDK import successful")\''
    )


def main():
    """Main setup function."""
    print("🔧 Endor Cockpit Environment Setup")
    print("=" * 40)

    # Create .env file
    if not create_env_file():
        sys.exit(1)

    # Validate environment
    results = validate_environment()
    uv_ok = check_uv_environment()

    # Summary
    required_ok = all(
        results.get(var, False)
        for var in [
            "ENDOR_API",
            "ENDOR_API_CREDENTIALS_KEY",
            "ENDOR_API_CREDENTIALS_SECRET",
        ]
    )

    print("\n" + "=" * 40)
    print("📊 SETUP SUMMARY")
    print("=" * 40)

    if required_ok and uv_ok:
        print("✅ Environment setup complete!")
        print("🎉 You're ready to use Endor Cockpit")
    else:
        print("⚠️  Environment setup incomplete")
        print_setup_instructions()

        if not required_ok:
            print(
                "\n❌ Required environment variables are missing or using "
                "placeholder values"
            )
        if not uv_ok:
            print("\n⚠️  UV environment configuration needs attention")


if __name__ == "__main__":
    main()
