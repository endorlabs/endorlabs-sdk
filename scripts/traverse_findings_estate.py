"""Temporary script: traverse findings across the estate.

Uses list with traverse=True. INFO logs show list start and completion.
Ensures the logging filter for secrets is ALWAYS present (root logger + client).
Requires: ENDOR_NAMESPACE, ENDOR_API_CREDENTIALS_KEY, ENDOR_API_CREDENTIALS_SECRET.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

# Add src to path when run from repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from endor_cockpit.api_client import APIClient, RedactingFilter, redaction_pattern
from endor_cockpit.resources import finding
from endor_cockpit.types import ListParameters


def load_dotenv_if_present() -> None:
    """Load .env from repo root if present (do not override existing env)."""
    repo_root = Path(__file__).resolve().parent.parent
    env_file = repo_root / ".env"
    if not env_file.exists():
        return
    with open(env_file, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, value = line.split("=", 1)
                key, value = key.strip(), value.strip()
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]
                if key and os.getenv(key) is None:
                    os.environ[key] = value


def ensure_redaction_filter() -> None:
    """Ensure the secrets redaction filter is always present on the root logger."""
    root = logging.getLogger()
    for f in root.filters:
        if isinstance(f, RedactingFilter):
            return
    root.addFilter(RedactingFilter([redaction_pattern]))


def main() -> int:
    load_dotenv_if_present()
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    ensure_redaction_filter()

    namespace = os.getenv("ENDOR_NAMESPACE")
    if not namespace:
        print("ERROR: ENDOR_NAMESPACE must be set", file=sys.stderr)
        return 1

    tenant_root = namespace.split(".")[0]

    client = APIClient(auth_method="api-key")
    ops = finding._get_finding_ops(client)

    list_params = ListParameters(
        traverse=True,
        page_size=50,
    )
    max_pages = 20

    print(f"Listing findings (tenant root: {tenant_root}, max_pages={max_pages})...")
    findings = ops.list(
        tenant_root,
        list_params=list_params,
        max_pages=max_pages,
    )
    print(f"Done. Total findings: {len(findings)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
