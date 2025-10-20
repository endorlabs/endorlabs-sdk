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
import time
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md

logger = logging.getLogger(__name__)


def download_openapi_spec(
    api_url: str, output_path: Path, timeout: int = 30, force: bool = False
) -> Dict[str, any]:
    """
    Download OpenAPI specification from Endor API.

    Args:
        api_url: Base URL of Endor API
        output_path: Path to save the spec file
        timeout: Request timeout in seconds
        force: Force re-download even if file exists

    Returns:
        Dict containing metadata: file_hash, timestamp, size, url
    """
    try:
        # Check if file exists and skip if not forcing
        if output_path.exists() and not force:
            logger.info(f"OpenAPI spec already exists at {output_path}, skipping download")
            with open(output_path, "rb") as f:
                file_hash = hashlib.sha256(f.read()).hexdigest()
            file_size = output_path.stat().st_size
            return {
                "file_hash": file_hash,
                "timestamp": datetime.now().isoformat(),
                "size": file_size,
                "url": f"{api_url}/download/openapiv2.swagger.json",
            }
        # Construct full URL
        spec_url = f"{api_url}/download/openapiv2.swagger.json"
        logger.info(f"Downloading OpenAPI spec from {spec_url}")

        # Make request with retry logic
        max_retries = 3
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
        spec_data = response.json()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(spec_data, f, indent=2)

        # Calculate file hash
        with open(output_path, "rb") as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()

        # Get file size
        file_size = output_path.stat().st_size

        metadata = {
            "file_hash": file_hash,
            "timestamp": datetime.now().isoformat(),
            "size": file_size,
            "url": spec_url,
        }

        logger.info(f"OpenAPI spec downloaded successfully ({file_size} bytes)")
        return metadata

    except Exception as e:
        logger.error(f"Failed to download OpenAPI spec: {e}")
        raise


def download_sitemap(url: str, output_path: Path, timeout: int = 30, force: bool = False) -> List[str]:
    """
    Download and parse sitemap.xml to extract documentation URLs.

    Args:
        url: URL of sitemap.xml
        output_path: Path to save the sitemap file
        timeout: Request timeout in seconds
        force: Force re-download even if file exists

    Returns:
        List of documentation page URLs
    """
    try:
        # Check if file exists and skip if not forcing
        if output_path.exists() and not force:
            logger.info(f"Sitemap already exists at {output_path}, skipping download")
            # Parse existing sitemap to extract URLs
            with open(output_path, "rb") as f:
                content = f.read()
            root = ET.fromstring(content)
            namespace = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}
            urls = []
            for loc in root.findall(".//ns:loc", namespace):
                if loc.text:
                    # Convert relative URLs to absolute URLs
                    if loc.text.startswith('/'):
                        urls.append(f"https://docs.endorlabs.com{loc.text}")
                    elif loc.text.startswith('http'):
                        urls.append(loc.text)
                    else:
                        urls.append(f"https://docs.endorlabs.com/{loc.text}")
            logger.info(f"Found {len(urls)} URLs in existing sitemap")
            return urls
        logger.info(f"Downloading sitemap from {url}")

        # Download sitemap
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()

        # Save sitemap
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(response.content)

        # Parse XML to extract URLs
        root = ET.fromstring(response.content)

        # Handle XML namespace
        namespace = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        urls = []

        for loc in root.findall(".//ns:loc", namespace):
            if loc.text:
                # Convert relative URLs to absolute URLs
                if loc.text.startswith('/'):
                    urls.append(f"https://docs.endorlabs.com{loc.text}")
                elif loc.text.startswith('http'):
                    urls.append(loc.text)
                else:
                    urls.append(f"https://docs.endorlabs.com/{loc.text}")

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
            f"Downloaded {downloaded_count} pages successfully, {skipped_count} skipped, {failed_count} failed"
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
