#!/usr/bin/env python3
"""
Sync External Documentation

Consolidated script for downloading and refreshing:
- OpenAPI/Swagger specification from Endor Labs API
- User documentation from docs.endorlabs.com sitemap

Example:
  # Install dependencies first (if not already installed)
  uv pip install -e ".[docs]"

  # Download both OpenAPI spec and user docs
  uv run python scripts/sync_external_docs.py --all

  # Download only OpenAPI spec
  uv run python scripts/sync_external_docs.py --download-openapi

  # Download only user docs
  uv run python scripts/sync_external_docs.py \\
    --download-user-docs --max-pages 100
"""

import argparse
import json
import logging
import os
import re
import sys
import time
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import List, Optional, Tuple
from urllib.parse import urlparse

import requests

# Check for optional dependencies for user docs functionality
try:
    from bs4 import BeautifulSoup
    from markdownify import markdownify as md
    HAS_DOCS_DEPS = True
except ImportError:
    HAS_DOCS_DEPS = False

# Add src to path for imports (scripts/ is one level below repo root)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from endor_cockpit.api_client import APIClient

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _default_workers() -> int:
    """Heuristic for I/O-bound parallel downloads from local compute."""
    n = os.cpu_count() or 1
    return min(20, max(2, n * 2))


def download_sitemap_urls(sitemap_url: str, timeout: int = 10) -> List[str]:
    """
    Download and parse sitemap.xml to extract URLs.

    Args:
        sitemap_url: URL of the sitemap.xml file
        timeout: Request timeout in seconds

    Returns:
        List of URLs found in the sitemap
    """
    try:
        logger.info(f"Downloading sitemap from: {sitemap_url}")
        response = requests.get(sitemap_url, timeout=timeout)
        response.raise_for_status()

        # Parse XML sitemap
        root = ET.fromstring(response.content)

        # Handle different sitemap namespaces
        namespaces = {
            "sitemap": "http://www.sitemaps.org/schemas/sitemap/0.9",
        }

        urls = []
        for url_elem in root.findall(".//sitemap:url", namespaces):
            loc_elem = url_elem.find("sitemap:loc", namespaces)
            if loc_elem is not None:
                urls.append(loc_elem.text)

        logger.info(f"Found {len(urls)} URLs in sitemap")
        return urls

    except Exception as e:
        logger.error(f"Error downloading sitemap: {e}")
        return []


def _normalize_url(url: str) -> str:
    """Normalize URL (handle relative/absolute)."""
    if url.startswith("/"):
        return f"https://docs.endorlabs.com{url}"
    elif not url.startswith("http"):
        return f"https://docs.endorlabs.com/{url}"
    else:
        return url


def _generate_filename(full_url: str) -> str:
    """Generate filename from URL."""
    parsed_url = urlparse(full_url)
    path_parts = parsed_url.path.strip("/").split("/")
    if not path_parts or path_parts == [""]:
        return "index.md"
    else:
        # Clean path parts and create filename
        clean_parts = [
            re.sub(r"[^\w\-_.]", "_", part) for part in path_parts if part
        ]
        if clean_parts:
            return f"{'-'.join(clean_parts)}.md"
        else:
            return "index.md"


def _download_single_page(
    full_url: str,
    output_file: Path,
    timeout: int,
) -> bool:
    """Download and convert single page."""
    try:
        # Download page
        response = requests.get(full_url, timeout=timeout)
        response.raise_for_status()

        # Parse HTML and extract content
        soup = BeautifulSoup(response.content, "html.parser")

        # Remove unwanted elements
        for element in soup(["script", "style", "nav", "footer", "header"]):
            element.decompose()

        # Convert to markdown
        markdown_content = md(str(soup), heading_style="ATX")

        # Add metadata header
        metadata = f"""---
url: {full_url}
title: {soup.title.string if soup.title else 'Untitled'}
downloaded: {time.strftime('%Y-%m-%d %H:%M:%S')}
---

{markdown_content}
"""

        # Save to file
        output_file.write_text(metadata, encoding="utf-8")
        return True
    except Exception as e:
        logger.warning(f"Failed to download {full_url}: {e}")
        return False


def _download_one(
    item: Tuple[str, Path, int],
) -> int:
    """Download a single page; returns 1 on success, 0 on failure."""
    full_url, output_file, timeout = item
    try:
        return 1 if _download_single_page(full_url, output_file, timeout) else 0
    except Exception as e:
        logger.warning("Failed to process %s: %s", full_url, e)
        return 0


def download_user_docs(
    sitemap_urls: List[str],
    output_dir: Path,
    max_pages: Optional[int] = None,
    timeout: int = 10,
    force: bool = False,
    workers: Optional[int] = None,
) -> int:
    """
    Download user documentation pages and convert to markdown (parallel).

    Args:
        sitemap_urls: List of URLs to download
        output_dir: Directory to save markdown files
        max_pages: Optional limit on number of pages to download
        timeout: Request timeout in seconds per page
        force: Force re-download even if files exist
        workers: Thread pool size (default: heuristic from CPU count)

    Returns:
        Number of successfully downloaded pages
    """
    try:
        output_dir.mkdir(parents=True, exist_ok=True)

        urls = sitemap_urls[:max_pages] if max_pages else sitemap_urls
        work_list: List[Tuple[str, Path, int]] = []
        for url in urls:
            full_url = _normalize_url(url)
            output_file = output_dir / _generate_filename(full_url)
            if force or not output_file.exists():
                work_list.append((full_url, output_file, timeout))

        if not work_list:
            logger.info("No new pages to download (all exist and not --force)")
            return 0

        n_workers = workers if workers is not None else _default_workers()
        logger.info(
            "Starting parallel download of %s pages to %s (%s workers)",
            len(work_list),
            output_dir,
            n_workers,
        )

        with ThreadPoolExecutor(max_workers=n_workers) as executor:
            results = list(executor.map(_download_one, work_list))
        downloaded_count = sum(results)

        logger.info("Successfully downloaded %s pages", downloaded_count)
        return downloaded_count

    except Exception as e:
        logger.error("Error in download process: %s", e)
        return 0


OPENAPI_SPEC_URL = "https://api.endorlabs.com/download/openapiv2.swagger.json"


def download_openapi_spec(
    output_path: str = "external_docs/openapi-swagger.json",
    force: bool = False,
) -> bool:
    """
    Download OpenAPI specification from Endor Labs API.

    Uses APIClient when credentials are set; otherwise fetches the public
    spec URL (same as CI curl) so the script works without auth.

    Args:
        output_path: Path to save the OpenAPI spec file
        force: Force re-download even if file exists

    Returns:
        True if download successful, False otherwise
    """
    try:
        output_file = Path(output_path)

        # Skip if file exists and not forcing
        if output_file.exists() and not force:
            logger.info(f"OpenAPI spec already exists: {output_path}")
            logger.info("Use --force to re-download")
            return True

        response_data = None
        has_creds = bool(
            os.environ.get("ENDOR_API_CREDENTIALS_KEY")
            and os.environ.get("ENDOR_API_CREDENTIALS_SECRET")
        )
        if has_creds:
            try:
                client = APIClient()
                logger.info("Downloading OpenAPI specification from Endor Labs API...")
                response = client.get(
                    "/download/openapiv2.swagger.json",
                    headers={"Accept": "application/json"},
                )
                response_data = response.json()
            except Exception as e:
                logger.warning(f"APIClient fetch failed: {e}, trying public URL")
        if response_data is None:
            logger.info(
                "Downloading OpenAPI specification from public URL (no credentials)"
            )
            resp = requests.get(OPENAPI_SPEC_URL, timeout=60)
            resp.raise_for_status()
            response_data = resp.json()

        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(os.path.abspath(str(output_file))), exist_ok=True)
        with open(output_file, "w") as f:
            json.dump(response_data, f, indent=4)

        logger.info(f"OpenAPI spec saved to: {output_path}")
        return True

    except Exception as e:
        logger.error(f"Error downloading OpenAPI spec: {e}")
        return False


def _setup_parser() -> argparse.ArgumentParser:
    """Create and configure argument parser."""
    parser = argparse.ArgumentParser(
        description="Sync external documentation (OpenAPI spec and user docs)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download both OpenAPI spec and user docs
  python scripts/sync_external_docs.py --all

  # Download only OpenAPI spec
  python scripts/sync_external_docs.py --download-openapi

  # Download only user docs with limit
  python scripts/sync_external_docs.py --download-user-docs --max-pages 100

  # Force re-download everything
  python scripts/sync_external_docs.py --all --force
        """,
    )

    # Action flags
    parser.add_argument(
        "--download-openapi",
        action="store_true",
        help="Download OpenAPI/Swagger specification",
    )
    parser.add_argument(
        "--download-user-docs",
        action="store_true",
        help="Download user documentation from sitemap",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Download both OpenAPI spec and user docs",
    )

    # OpenAPI options
    parser.add_argument(
        "--openapi-output",
        default="external_docs/openapi-swagger.json",
        help=(
            "Output path for OpenAPI spec "
            "(default: external_docs/openapi-swagger.json)"
        ),
    )

    # User docs options
    parser.add_argument(
        "--sitemap-url",
        default="https://docs.endorlabs.com/sitemap.xml",
        help="Sitemap URL (default: https://docs.endorlabs.com/sitemap.xml)",
    )
    parser.add_argument(
        "--user-docs-output",
        default="external_docs/user-docs",
        help="Output directory for user docs (default: external_docs/user-docs)",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        help="Maximum number of pages to download (default: no limit)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=10,
        help="Request timeout in seconds per page (default: 10)",
    )

    # Common options
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-download even if files already exist",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    return parser


def _download_user_docs_section(args) -> bool:
    """Handle user docs download section."""
    if not HAS_DOCS_DEPS:
        logger.error(
            "Missing required dependencies for user docs download.\n"
            "Install them with: uv pip install -e '.[docs]'"
        )
        return False

    logger.info("=" * 80)
    logger.info("DOWNLOADING USER DOCUMENTATION")
    logger.info("=" * 80)

    try:
        output_dir = Path(args.user_docs_output)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Download sitemap and extract URLs
        sitemap_urls = download_sitemap_urls(args.sitemap_url, args.timeout)
        if not sitemap_urls:
            logger.error("No URLs found in sitemap")
            return False

        logger.info(f"Found {len(sitemap_urls)} URLs in sitemap")

        downloaded_count = download_user_docs(
            sitemap_urls=sitemap_urls,
            output_dir=output_dir,
            max_pages=args.max_pages,
            timeout=args.timeout,
            force=args.force,
        )

        logger.info("=" * 80)
        logger.info("USER DOCUMENTATION DOWNLOAD COMPLETE")
        logger.info("=" * 80)
        logger.info(f"Successfully downloaded: {downloaded_count} pages")
        logger.info(f"Output directory: {output_dir}")

        if downloaded_count < len(sitemap_urls):
            logger.info(
                f"Note: {len(sitemap_urls) - downloaded_count} URLs were "
                "skipped or failed"
            )

        return True

    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return False


def _execute_downloads(args) -> bool:
    """Execute download operations based on args."""
    success = True

    # Determine what to download
    download_openapi = args.download_openapi or args.all
    should_download_user_docs = args.download_user_docs or args.all

    # Download OpenAPI spec
    if download_openapi:
        logger.info("=" * 80)
        logger.info("DOWNLOADING OPENAPI SPECIFICATION")
        logger.info("=" * 80)
        if not download_openapi_spec(args.openapi_output, args.force):
            success = False

    # Download user docs
    if should_download_user_docs:
        if not _download_user_docs_section(args):
            success = False

    return success


def main():
    """Main function to sync external documentation."""
    parser = _setup_parser()
    args = parser.parse_args()

    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Determine what to download
    download_openapi = args.download_openapi or args.all
    should_download_user_docs = args.download_user_docs or args.all

    if not download_openapi and not should_download_user_docs:
        parser.error("Must specify --download-openapi, --download-user-docs, or --all")

    success = _execute_downloads(args)

    # Summary
    logger.info("=" * 80)
    logger.info("SYNC COMPLETE")
    logger.info("=" * 80)

    if success:
        logger.info("All downloads completed successfully")
        sys.exit(0)
    else:
        logger.error("Some downloads failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
