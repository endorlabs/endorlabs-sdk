"""Core sync logic for context bootstrap.

Downloads OpenAPI spec and user documentation from Endor Labs.
Requires authentication via APIClient - no public URL fallback.
"""

from __future__ import annotations

import asyncio
import json
import re
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

import defusedxml.ElementTree as ET  # noqa: N817
import httpx

if TYPE_CHECKING:
    from endorlabs.api_client import APIClient

from endorlabs.utils.logging_config import get_resource_logger

from .models import InitStatus

logger = get_resource_logger(__name__)


def _import_docs_deps() -> tuple[Any, Callable[..., str]]:
    """Import optional docs dependencies.

    Returns:
        Tuple of (BeautifulSoup class, markdownify function).

    Raises:
        ImportError: If dependencies are not installed.

    """
    try:
        from bs4 import BeautifulSoup
        from markdownify import markdownify as md

        return BeautifulSoup, md
    except ImportError as e:
        raise ImportError(
            "Context dependencies not installed. "
            "Install with: pip install endorlabs-sdk[context]"
        ) from e


# Constants
SITEMAP_URL = "https://docs.endorlabs.com/sitemap.xml"
OPENAPI_PATH = "/download/openapiv2.swagger.json"

# Default output paths (single source of truth for context downloads)
DEFAULT_CONTEXT_DIR = ".endorlabs-context"
DEFAULT_OPENAPI_FILENAME = "openapiv2.swagger.json"
DEFAULT_USER_DOCS_DIRNAME = "docs"


def _default_concurrency() -> int:
    """Heuristic for I/O-bound parallel downloads - async can handle more."""
    return 50


def _normalize_url(url: str) -> str:
    """Normalize URL (handle relative/absolute)."""
    if url.startswith("/"):
        return f"https://docs.endorlabs.com{url}"
    elif not url.startswith("http"):
        return f"https://docs.endorlabs.com/{url}"
    return url


def _generate_filename(full_url: str) -> str:
    """Generate filename from URL."""
    parsed_url = urlparse(full_url)
    path_parts = parsed_url.path.strip("/").split("/")
    if not path_parts or path_parts == [""]:
        return "index.md"
    # Clean path parts and create filename
    clean_parts = [re.sub(r"[^\w\-_.]", "_", part) for part in path_parts if part]
    if clean_parts:
        return f"{'-'.join(clean_parts)}.md"
    return "index.md"


async def _download_sitemap(timeout: int = 10) -> list[str]:
    """Download and parse sitemap.xml to extract URLs.

    Args:
        timeout: Request timeout in seconds.

    Returns:
        List of URLs found in the sitemap.

    """
    try:
        logger.info("Downloading sitemap from: %s", SITEMAP_URL)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(SITEMAP_URL)
            _ = response.raise_for_status()

        # Parse XML sitemap
        root = ET.fromstring(response.content)
        namespaces = {"sitemap": "http://www.sitemaps.org/schemas/sitemap/0.9"}

        urls: list[str] = []
        for url_elem in root.findall(".//sitemap:url", namespaces):
            loc_elem = url_elem.find("sitemap:loc", namespaces)
            if loc_elem is not None and loc_elem.text:
                urls.append(loc_elem.text)

        logger.info("Found %d URLs in sitemap", len(urls))
        return urls

    except Exception as e:
        logger.error("Error downloading sitemap: %s", e)
        return []


async def _download_single_page(
    client: httpx.AsyncClient,
    full_url: str,
    output_file: Path,
    base_dir: Path,
) -> bool:
    """Download and convert single page to markdown."""
    from endorlabs.utils.path_safety import safe_write_text

    beautiful_soup_cls, md = _import_docs_deps()
    try:
        response = await client.get(full_url)
        _ = response.raise_for_status()

        # Parse HTML and extract content
        soup = beautiful_soup_cls(response.content, "html.parser")

        # Remove unwanted elements
        for element in soup(["script", "style", "nav", "footer", "header"]):
            element.decompose()

        # Convert to markdown
        markdown_content = md(str(soup), heading_style="ATX")

        # Add metadata header
        title = soup.title.string if soup.title else "Untitled"
        metadata = f"""---
url: {full_url}
title: {title}
downloaded: {time.strftime("%Y-%m-%d %H:%M:%S")}
---

{markdown_content}
"""
        safe_write_text(base_dir, output_file, metadata)
        return True

    except Exception as e:
        logger.warning("Unable to download %s: %s", full_url, e)
        return False


async def _download_one(
    client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
    full_url: str,
    output_file: Path,
    base_dir: Path,
) -> int:
    """Download a single page with semaphore; returns 1 on success, 0 on failure."""
    async with semaphore:
        try:
            success = await _download_single_page(
                client, full_url, output_file, base_dir
            )
            return 1 if success else 0
        except Exception as e:
            logger.warning("Unable to process %s: %s", full_url, e)
            return 0


async def _download_user_docs_async(
    output_dir: Path,
    max_pages: int | None = None,
    timeout: int = 10,
    force: bool = False,
    max_concurrent: int | None = None,
) -> int:
    """Download user documentation pages and convert to markdown.

    Args:
        output_dir: Directory to save markdown files.
        max_pages: Optional limit on number of pages to download.
        timeout: Request timeout in seconds per page.
        force: Force re-download even if files exist.
        max_concurrent: Maximum concurrent downloads (default: 50).

    Returns:
        Number of successfully downloaded pages.

    """
    # Check deps early to fail fast
    _ = _import_docs_deps()
    output_dir.mkdir(parents=True, exist_ok=True)

    # Get URLs from sitemap
    sitemap_urls = await _download_sitemap(timeout)
    if not sitemap_urls:
        logger.error("No URLs found in sitemap")
        return 0

    urls = sitemap_urls[:max_pages] if max_pages else sitemap_urls
    work_list: list[tuple[str, Path]] = []

    for url in urls:
        full_url = _normalize_url(url)
        output_file = output_dir / _generate_filename(full_url)
        if force or not output_file.exists():
            work_list.append((full_url, output_file))

    if not work_list:
        logger.info("No new pages to download (all exist and not force=True)")
        return 0

    concurrency = max_concurrent or _default_concurrency()
    semaphore = asyncio.Semaphore(concurrency)

    logger.info(
        "Starting async download of %d pages to %s (%d concurrent)",
        len(work_list),
        output_dir,
        concurrency,
    )

    limits = httpx.Limits(max_connections=concurrency, max_keepalive_connections=20)
    async with httpx.AsyncClient(timeout=timeout, limits=limits) as client:
        tasks = [
            _download_one(client, semaphore, full_url, output_file, output_dir)
            for full_url, output_file in work_list
        ]
        results = await asyncio.gather(*tasks)

    downloaded_count = sum(results)
    logger.info("Successfully downloaded %d pages", downloaded_count)
    return downloaded_count


def sync_user_docs(
    output_dir: str | Path = f"{DEFAULT_CONTEXT_DIR}/{DEFAULT_USER_DOCS_DIRNAME}",
    max_pages: int | None = None,
    timeout: int = 10,
    force: bool = False,
    max_concurrent: int | None = None,
) -> int:
    """Download user documentation pages and convert to markdown.

    This is the synchronous wrapper for user docs download.
    Requires: pip install endorlabs-sdk[context]

    Args:
        output_dir: Directory to save markdown files.
        max_pages: Optional limit on number of pages to download.
        timeout: Request timeout in seconds per page.
        force: Force re-download even if files exist.
        max_concurrent: Maximum concurrent downloads (default: 50).

    Returns:
        Number of successfully downloaded pages.

    """
    # Check deps early to fail fast
    _ = _import_docs_deps()
    return asyncio.run(
        _download_user_docs_async(
            output_dir=Path(output_dir),
            max_pages=max_pages,
            timeout=timeout,
            force=force,
            max_concurrent=max_concurrent,
        )
    )


def sync_openapi(
    output_path: str | Path = f"{DEFAULT_CONTEXT_DIR}/{DEFAULT_OPENAPI_FILENAME}",
    force: bool = False,
    client: APIClient | None = None,
) -> Path:
    """Download OpenAPI specification from Endor Labs API.

    Requires authentication via APIClient - no public URL fallback.

    Args:
        output_path: Path to save the OpenAPI spec file.
        force: Force re-download even if file exists.
        client: Optional APIClient instance. If not provided, one is created
            (requires ENDOR_API_CREDENTIALS_KEY/SECRET or ENDOR_TOKEN env vars).

    Returns:
        Path to the downloaded OpenAPI spec file.

    Raises:
        endorlabs.UnauthorizedError: If authentication fails.
        ImportError: If context dependencies are not installed.

    """
    from endorlabs.api_client import APIClient as APIClientClass

    output_file = Path(output_path)

    # Skip if file exists and not forcing
    if output_file.exists() and not force:
        logger.info(
            "OpenAPI spec already exists: %s (use force=True to re-download)",
            output_path,
        )
        return output_file

    # Create client if not provided
    api_client = client or APIClientClass()

    logger.info("Downloading OpenAPI specification from Endor Labs API...")
    response = api_client.get(
        OPENAPI_PATH,
        headers={"Accept": "application/json"},
    )
    response_data = response.json()

    # Create directory if it doesn't exist
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(response_data, f, indent=2)

    logger.info("OpenAPI spec saved to: %s", output_path)
    return output_file


def init(
    output_dir: str | Path = DEFAULT_CONTEXT_DIR,
    include_openapi: bool = True,
    include_user_docs: bool = True,
    max_pages: int | None = None,
    force: bool = False,
    client: APIClient | None = None,
) -> InitStatus:
    """Bootstrap Endor Labs context for agentic workflows.

    Downloads API specification and user documentation to a local directory.
    Requires authentication via APIClient - no public URL fallback.

    Args:
        output_dir: Directory to save context files (default: .endorlabs-context).
        include_openapi: Download OpenAPI spec (default: True).
        include_user_docs: Download user documentation (default: True).
        max_pages: Maximum number of user doc pages to download (default: all).
        force: Force re-download even if files exist (default: False).
        client: Optional APIClient instance. If not provided, one is created
            (requires ENDOR_API_CREDENTIALS_KEY/SECRET or ENDOR_TOKEN env vars).

    Returns:
        InitStatus with paths to downloaded files and metadata.

    Raises:
        endorlabs.UnauthorizedError: If authentication fails.
        ImportError: If context dependencies are not installed (for user docs).

    Example::

        >>> import endorlabs
        >>> status = endorlabs.init()
        >>> print(status.openapi_path)
        .endorlabs-context/openapiv2.swagger.json

    """
    from endorlabs.api_client import APIClient as APIClientClass

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Create client once for auth validation and reuse
    api_client = client or APIClientClass()

    openapi_path: Path | None = None
    user_docs_path: Path | None = None
    user_docs_count = 0

    # Download OpenAPI spec (validates auth)
    if include_openapi:
        openapi_path = sync_openapi(
            output_path=output_path / DEFAULT_OPENAPI_FILENAME,
            force=force,
            client=api_client,
        )

    # Download user docs
    if include_user_docs:
        # sync_user_docs will check deps internally
        docs_dir = output_path / "docs"
        user_docs_count = sync_user_docs(
            output_dir=docs_dir,
            max_pages=max_pages,
            force=force,
        )
        user_docs_path = docs_dir

    return InitStatus(
        openapi_path=openapi_path,
        user_docs_path=user_docs_path,
        user_docs_count=user_docs_count,
        downloaded_at=datetime.now(UTC),
    )
