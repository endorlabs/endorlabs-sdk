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
  uv run python scripts/sync_external_docs.py --download-user-docs --max-pages 100
"""

import argparse
import logging
import os
import re
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Optional
from urllib.parse import urlparse

import requests

# Check for optional dependencies for user docs functionality
try:
    from bs4 import BeautifulSoup
    from markdownify import markdownify as md
    HAS_DOCS_DEPS = True
except ImportError:
    HAS_DOCS_DEPS = False

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from endor_cockpit.api_client import APIClient

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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


def download_user_docs(
    sitemap_urls: List[str],
    output_dir: Path,
    max_pages: Optional[int] = None,
    timeout: int = 10,
    force: bool = False,
) -> int:
    """
    Download user documentation pages and convert to markdown.

    Args:
        sitemap_urls: List of URLs to download
        output_dir: Directory to save markdown files
        max_pages: Optional limit on number of pages to download
        timeout: Request timeout in seconds per page
        force: Force re-download even if files exist

    Returns:
        Number of successfully downloaded pages
    """
    try:
        output_dir.mkdir(parents=True, exist_ok=True)

        downloaded_count = 0
        total_urls = len(sitemap_urls)
        if max_pages:
            total_urls = min(total_urls, max_pages)

        logger.info(f"Starting download of {total_urls} pages to {output_dir}")

        for i, url in enumerate(
            sitemap_urls[:max_pages] if max_pages else sitemap_urls
        ):
            try:
                # Handle relative URLs by prepending the base domain
                if url.startswith("/"):
                    full_url = f"https://docs.endorlabs.com{url}"
                elif not url.startswith("http"):
                    full_url = f"https://docs.endorlabs.com/{url}"
                else:
                    full_url = url

                # Generate filename from URL
                parsed_url = urlparse(full_url)
                path_parts = parsed_url.path.strip("/").split("/")
                if not path_parts or path_parts == [""]:
                    filename = "index.md"
                else:
                    # Clean path parts and create filename
                    clean_parts = [
                        re.sub(r"[^\w\-_.]", "_", part) for part in path_parts if part
                    ]
                    if clean_parts:
                        filename = f"{'-'.join(clean_parts)}.md"
                    else:
                        filename = "index.md"

                output_file = output_dir / filename

                # Skip if file exists and not forcing
                if output_file.exists() and not force:
                    logger.debug(f"Skipping existing file: {filename}")
                    continue

                logger.info(f"Downloading ({i+1}/{total_urls}): {full_url}")

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
                downloaded_count += 1

                # Small delay to be respectful
                time.sleep(0.5)

            except Exception as e:
                logger.warning(f"Failed to download {url}: {e}")
                continue

        logger.info(f"Successfully downloaded {downloaded_count} pages")
        return downloaded_count

    except Exception as e:
        logger.error(f"Error in download process: {e}")
        return 0


def download_openapi_spec(
    output_path: str = "external_docs/openapi-swagger.json",
    force: bool = False,
) -> bool:
    """
    Download OpenAPI specification from Endor Labs API.

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

        # Initialize API client
        client = APIClient()

        logger.info("Downloading OpenAPI specification from Endor Labs API...")
        client.get_openapi_spec(url=None, path=str(output_file))

        logger.info(f"OpenAPI spec saved to: {output_path}")
        return True

    except Exception as e:
        logger.error(f"Error downloading OpenAPI spec: {e}")
        return False


def main():
    """Main function to sync external documentation."""
    parser = argparse.ArgumentParser(
        description="Sync external documentation (OpenAPI spec and user docs)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download both OpenAPI spec and user docs
  python sync_external_docs.py --all

  # Download only OpenAPI spec
  python sync_external_docs.py --download-openapi

  # Download only user docs with limit
  python sync_external_docs.py --download-user-docs --max-pages 100

  # Force re-download everything
  python sync_external_docs.py --all --force
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
        help="Output path for OpenAPI spec (default: external_docs/openapi-swagger.json)",
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

    args = parser.parse_args()

    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Determine what to download
    download_openapi = args.download_openapi or args.all
    download_user_docs = args.download_user_docs or args.all

    if not download_openapi and not download_user_docs:
        parser.error("Must specify --download-openapi, --download-user-docs, or --all")

    success = True

    # Download OpenAPI spec
    if download_openapi:
        logger.info("=" * 80)
        logger.info("DOWNLOADING OPENAPI SPECIFICATION")
        logger.info("=" * 80)
        if not download_openapi_spec(args.openapi_output, args.force):
            success = False

    # Download user docs
    if download_user_docs:
        if not HAS_DOCS_DEPS:
            logger.error(
                "Missing required dependencies for user docs download.\n"
                "Install them with: uv pip install -e '.[docs]'"
            )
            success = False
        else:
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
                    success = False
                else:
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

            except KeyboardInterrupt:
                logger.info("Operation cancelled by user")
                sys.exit(1)
            except Exception as e:
                logger.error(f"Unexpected error: {e}", exc_info=True)
                success = False

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

