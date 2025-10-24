"""
External Documentation Downloads for Holocron

Provides functions to download and process external documentation sources:
- OpenAPI specification from Endor API
- Sitemap.xml from docs.endorlabs.com
- User documentation pages from sitemap URLs
"""

import hashlib
import json
import logging
import os
import time
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md

from .config import ExternalDocsConfig

logger = logging.getLogger(__name__)


def download_openapi_spec_with_config(
    config: ExternalDocsConfig, timeout: int = 30, force: bool = False
) -> Dict[str, Any]:
    """
    Download OpenAPI specification using configuration.

    Args:
        config: ExternalDocsConfig instance
        timeout: Request timeout in seconds
        force: Force re-download even if file exists

    Returns:
        Dict containing metadata: file_hash, timestamp, size, url
    """
    # Interpolate environment variables in URL template
    api_url = config.openapi_url_template
    if "{ENDOR_API}" in api_url:
        endor_api = os.getenv("ENDOR_API", "https://api.endorlabs.com")
        api_url = api_url.replace("{ENDOR_API}", endor_api)

    output_path = Path(config.openapi_output)
    return download_openapi_spec(api_url, output_path, timeout, force)


def download_sitemap_with_config(
    config: ExternalDocsConfig, timeout: int = 30, force: bool = False
) -> List[str]:
    """
    Download and parse sitemap.xml using configuration.

    Args:
        config: ExternalDocsConfig instance
        timeout: Request timeout in seconds
        force: Force re-download even if file exists

    Returns:
        List of documentation page URLs
    """
    output_path = Path(config.sitemap_output)
    return download_sitemap(config.sitemap_url, output_path, timeout, force)


def download_user_docs_with_config(
    config: ExternalDocsConfig,
    sitemap_urls: List[str],
    max_pages: Optional[int] = None,
    timeout: int = 10,
    force: bool = False,
) -> int:
    """
    Download user documentation pages using configuration.

    Args:
        config: ExternalDocsConfig instance
        sitemap_urls: List of URLs to download
        max_pages: Optional limit on number of pages to download
        timeout: Request timeout in seconds per page
        force: Force re-download even if files exist

    Returns:
        Number of successfully downloaded pages
    """
    output_dir = Path(config.user_docs_output)
    return download_user_docs(sitemap_urls, output_dir, max_pages, timeout, force)


def download_openapi_spec(
    api_url: str, output_path: Path, timeout: int = 30, force: bool = False
) -> Dict[str, Any]:
    """
    Download OpenAPI specification from Endor API with intelligent caching.

    Args:
        api_url: Base URL of Endor API
        output_path: Path to save the spec file
        timeout: Request timeout in seconds
        force: Force re-download even if file exists

    Returns:
        Dict containing metadata: file_hash, timestamp, size, url
    """
    try:
        # Check if file exists and is recent
        if output_path.exists() and not force:
            file_age_days = (
                datetime.now() - datetime.fromtimestamp(output_path.stat().st_mtime)
            ).days

            if file_age_days < 7:  # Within staleness threshold
                logger.info(f"Using cached OpenAPI spec (age: {file_age_days} days)")
                with open(output_path, "rb") as f:
                    file_hash = hashlib.sha256(f.read()).hexdigest()
                file_size = output_path.stat().st_size
                return {
                    "file_hash": file_hash,
                    "timestamp": datetime.now().isoformat(),
                    "size": file_size,
                    "url": f"{api_url}/download/openapiv2.swagger.json",
                }
            else:
                logger.warning(
                    f"OpenAPI spec is {file_age_days} days old, checking for updates..."
                )
                # Continue to download and compare hash
        # Construct full URL
        spec_url = f"{api_url}/download/openapiv2.swagger.json"
        logger.info(f"Downloading OpenAPI spec from {spec_url}")

        # Make request with retry logic
        max_retries = 3
        response = None
        for attempt in range(max_retries):
            try:
                response = requests.get(
                    spec_url,
                    headers={"Accept": "application/json"},
                    timeout=timeout,
                )
                response.raise_for_status()
                break
            except requests.exceptions.RequestException as e:
                if attempt == max_retries - 1:
                    raise
                wait_time = 2**attempt  # Exponential backoff
                logger.warning(
                    f"Request failed (attempt {attempt + 1}/{max_retries}): {e}"
                )
                logger.info(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)

        # Parse and save JSON
        if response is None:
            raise requests.exceptions.RequestException(
                "Failed to get response after retries"
            )
        spec_data = response.json()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Calculate hash of new content before saving
        new_content = json.dumps(spec_data, indent=2, sort_keys=True)
        new_hash = hashlib.sha256(new_content.encode("utf-8")).hexdigest()

        # Check if content has changed
        if output_path.exists():
            with open(output_path, "rb") as f:
                old_hash = hashlib.sha256(f.read()).hexdigest()
            if new_hash == old_hash:
                logger.info("OpenAPI spec unchanged, no update needed")
                file_size = output_path.stat().st_size
                return {
                    "file_hash": old_hash,
                    "timestamp": datetime.now().isoformat(),
                    "size": file_size,
                    "url": spec_url,
                }

        # Save new content
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(new_content)

        # Get file size
        file_size = output_path.stat().st_size

        metadata = {
            "file_hash": new_hash,
            "timestamp": datetime.now().isoformat(),
            "size": file_size,
            "url": spec_url,
        }

        logger.info(f"OpenAPI spec downloaded successfully ({file_size} bytes)")
        return metadata

    except Exception as e:
        logger.error(f"Failed to download OpenAPI spec: {e}")
        raise


def _normalize_url(url: str) -> str:
    """Convert relative URLs to absolute URLs."""
    if url.startswith("/"):
        return f"https://docs.endorlabs.com{url}"
    elif url.startswith("http"):
        return url
    else:
        return f"https://docs.endorlabs.com/{url}"


def _extract_urls_from_xml(content: bytes) -> List[str]:
    """Extract URLs from XML sitemap content."""
    root = ET.fromstring(content)
    namespace = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}

    urls = []
    for loc in root.findall(".//ns:loc", namespace):
        if loc.text:
            urls.append(_normalize_url(loc.text))

    return urls


def _parse_existing_sitemap(output_path: Path) -> List[str]:
    """Parse existing sitemap file to extract URLs."""
    logger.info(f"Sitemap already exists at {output_path}, skipping download")

    with open(output_path, "rb") as f:
        content = f.read()

    urls = _extract_urls_from_xml(content)
    logger.info(f"Found {len(urls)} URLs in existing sitemap")
    return urls


def _download_and_save_sitemap(url: str, output_path: Path, timeout: int) -> bytes:
    """Download sitemap and save to file."""
    logger.info(f"Downloading sitemap from {url}")

    response = requests.get(url, timeout=timeout)
    response.raise_for_status()

    # Save sitemap
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(response.content)

    return response.content


def download_sitemap(
    url: str, output_path: Path, timeout: int = 30, force: bool = False
) -> List[str]:
    """
    Download and parse sitemap.xml to extract documentation URLs with intelligent
    caching.

    Args:
        url: URL of sitemap.xml
        output_path: Path to save the sitemap file
        timeout: Request timeout in seconds
        force: Force re-download even if file exists

    Returns:
        List of documentation page URLs
    """
    try:
        # Check if file exists and is recent
        if output_path.exists() and not force:
            file_age_days = (
                datetime.now() - datetime.fromtimestamp(output_path.stat().st_mtime)
            ).days

            if file_age_days < 7:  # Within staleness threshold
                logger.info(f"Using cached sitemap (age: {file_age_days} days)")
                return _parse_existing_sitemap(output_path)
            else:
                logger.warning(
                    f"Sitemap is {file_age_days} days old, checking for updates..."
                )
                # Continue to download and compare hash

        # Download and save sitemap
        content = _download_and_save_sitemap(url, output_path, timeout)

        # Check if content has changed
        new_hash = hashlib.sha256(content).hexdigest()
        if output_path.exists():
            with open(output_path, "rb") as f:
                old_hash = hashlib.sha256(f.read()).hexdigest()
            if new_hash == old_hash:
                logger.info("Sitemap unchanged, no update needed")
                return _parse_existing_sitemap(output_path)

        # Extract URLs from downloaded content
        urls = _extract_urls_from_xml(content)
        logger.info(f"Found {len(urls)} URLs in sitemap")
        return urls

    except Exception as e:
        logger.error(f"Failed to download sitemap: {e}")
        raise


def sanitize_filename(url: str) -> str:
    """
    Convert URL to safe filename.

    Args:
        url: URL to convert

    Returns:
        Safe filename string
    """
    parsed = urlparse(url)
    path = parsed.path.strip("/")

    # Replace slashes with hyphens
    filename = path.replace("/", "-")

    # Remove or replace unsafe characters
    safe_chars = set("abcdefghijklmnopqrstuvwxyz0123456789-_.")
    filename = "".join(c if c.lower() in safe_chars else "-" for c in filename)

    # Remove consecutive hyphens
    while "--" in filename:
        filename = filename.replace("--", "-")

    # Ensure it ends with .md
    if not filename.endswith(".md"):
        filename += ".md"

    return filename


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
        failed_count = 0
        skipped_count = 0

        urls_to_process = sitemap_urls[:max_pages] if max_pages else sitemap_urls

        logger.info(f"Processing {len(urls_to_process)} documentation pages")

        for i, url in enumerate(urls_to_process, 1):
            try:
                # Check if file already exists
                filename = sanitize_filename(url)
                output_path = output_dir / filename

                if output_path.exists() and not force:
                    logger.debug(f"File already exists: {filename}, skipping")
                    skipped_count += 1
                    continue

                # Download page
                response = requests.get(url, timeout=timeout)
                response.raise_for_status()

                # Parse HTML
                soup = BeautifulSoup(response.content, "html.parser")

                # Find main content (adjust selector based on site structure)
                # Try common content selectors
                main_content = (
                    soup.find("main")
                    or soup.find("article")
                    or soup.find("div", class_="content")
                    or soup.find("body")
                )

                if main_content:
                    # Convert to markdown
                    markdown_content = md(str(main_content))

                    # Add metadata header
                    header = f"<!-- Source: {url} -->\n"
                    header += f"<!-- Downloaded: {datetime.now().isoformat()} -->\n\n"
                    markdown_content = header + markdown_content

                    # Save to file
                    filename = sanitize_filename(url)
                    output_path = output_dir / filename

                    with open(output_path, "w", encoding="utf-8") as f:
                        f.write(markdown_content)

                    downloaded_count += 1

                    # Progress logging every 10 pages
                    if i % 10 == 0:
                        logger.info(
                            f"Progress: {i}/{len(urls_to_process)} pages processed"
                        )
                else:
                    logger.warning(f"No main content found in {url}")
                    failed_count += 1

            except Exception as e:
                logger.warning(f"Failed to download {url}: {e}")
                failed_count += 1
                continue

        logger.info(
            f"Downloaded {downloaded_count} pages successfully, "
            f"{skipped_count} skipped, {failed_count} failed"
        )
        return downloaded_count

    except Exception as e:
        logger.error(f"Failed to download user docs: {e}")
        raise


def check_download_freshness(
    manifest_path: Path, max_age_days: int = 7
) -> Tuple[bool, Dict[str, int]]:
    """
    Check if external downloads need refreshing based on age.

    Args:
        manifest_path: Path to vector DB manifest file
        max_age_days: Maximum age in days before refresh needed

    Returns:
        Tuple of (needs_refresh, ages_dict) where ages_dict contains
        ages in days for each external resource
    """
    try:
        if not manifest_path.exists():
            return True, {}

        with open(manifest_path, "r") as f:
            manifest = json.load(f)

        external = manifest.get("external_docs", {})
        if not external:
            return True, {}

        now = datetime.now()
        ages = {}
        needs_refresh = False

        # Check OpenAPI spec age
        openapi_last = external.get("openapi_spec", {}).get("last_downloaded")
        if openapi_last:
            last_dl = datetime.fromisoformat(openapi_last)
            age_days = (now - last_dl).days
            ages["openapi_spec"] = age_days
            if age_days > max_age_days:
                needs_refresh = True

        # Check user docs age
        userdocs_last = external.get("user_docs", {}).get("last_downloaded")
        if userdocs_last:
            last_dl = datetime.fromisoformat(userdocs_last)
            age_days = (now - last_dl).days
            ages["user_docs"] = age_days
            if age_days > max_age_days:
                needs_refresh = True

        return needs_refresh, ages

    except Exception as e:
        logger.error(f"Failed to check download freshness: {e}")
        return True, {}
