#!/usr/bin/env python3
"""
Download User Documentation Maneuver

A repeatable script for downloading user documentation from the Endor Labs sitemap.
This script downloads all documentation pages from the sitemap.xml and converts them to markdown.

Example:

uv run python maneuvers/download_user_docs.py \
  --sitemap-url "https://docs.endorlabs.com/sitemap.xml" \
  --output-dir "external_docs/user-docs" \
  --max-pages 50 \
  --timeout 10 \
  --force

## Note: This downloads all user documentation pages and converts them to markdown
## for use in AI agent context and documentation analysis.
"""

import argparse
import hashlib
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
from bs4 import BeautifulSoup
from markdownify import markdownify as md

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
            'sitemap': 'http://www.sitemaps.org/schemas/sitemap/0.9'
        }
        
        urls = []
        for url_elem in root.findall('.//sitemap:url', namespaces):
            loc_elem = url_elem.find('sitemap:loc', namespaces)
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
        
        for i, url in enumerate(sitemap_urls[:max_pages] if max_pages else sitemap_urls):
            try:
                # Handle relative URLs by prepending the base domain
                if url.startswith('/'):
                    full_url = f"https://docs.endorlabs.com{url}"
                elif not url.startswith('http'):
                    full_url = f"https://docs.endorlabs.com/{url}"
                else:
                    full_url = url
                
                # Generate filename from URL
                parsed_url = urlparse(full_url)
                path_parts = parsed_url.path.strip('/').split('/')
                if not path_parts or path_parts == ['']:
                    filename = 'index.md'
                else:
                    # Clean path parts and create filename
                    clean_parts = [re.sub(r'[^\w\-_.]', '_', part) for part in path_parts if part]
                    if clean_parts:
                        filename = f"{'-'.join(clean_parts)}.md"
                    else:
                        filename = 'index.md'
                
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
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Remove unwanted elements
                for element in soup(['script', 'style', 'nav', 'footer', 'header']):
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
                output_file.write_text(metadata, encoding='utf-8')
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


def main():
    """Main function to download user documentation with command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Download user documentation from Endor Labs sitemap",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download all user docs from sitemap
  python download_user_docs.py \\
    --sitemap-url "https://docs.endorlabs.com/sitemap.xml" \\
    --output-dir "external_docs/user-docs" \\
    --max-pages 100

  # Download with custom timeout and force refresh
  python download_user_docs.py \\
    --sitemap-url "https://docs.endorlabs.com/sitemap.xml" \\
    --output-dir "external_docs/user-docs" \\
    --max-pages 50 \\
    --timeout 15 \\
    --force

  # Download specific URLs only
  python download_user_docs.py \\
    --urls "https://docs.endorlabs.com/getting-started,https://docs.endorlabs.com/api-reference" \\
    --output-dir "external_docs/user-docs" \\
    --timeout 10
        """
    )
    
    # Input source arguments (mutually exclusive)
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        "--sitemap-url",
        help="Sitemap URL to parse for documentation URLs (e.g., https://docs.endorlabs.com/sitemap.xml)"
    )
    input_group.add_argument(
        "--urls",
        help="Comma-separated list of specific URLs to download"
    )
    
    # Required arguments
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Output directory for downloaded markdown files"
    )
    
    # Optional arguments
    parser.add_argument(
        "--max-pages",
        type=int,
        help="Maximum number of pages to download (default: no limit)"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=10,
        help="Request timeout in seconds per page (default: 10)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-download even if files already exist"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        # Create output directory
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Determine URLs to download
        if args.sitemap_url:
            logger.info(f"Downloading sitemap URLs from: {args.sitemap_url}")
            sitemap_urls = download_sitemap_urls(args.sitemap_url, args.timeout)
            if not sitemap_urls:
                logger.error("No URLs found in sitemap")
                sys.exit(1)
            logger.info(f"Found {len(sitemap_urls)} URLs in sitemap")
        else:
            # Parse comma-separated URLs
            sitemap_urls = [url.strip() for url in args.urls.split(',') if url.strip()]
            logger.info(f"Using {len(sitemap_urls)} specified URLs")
        
        # Download user documentation
        logger.info(f"Starting download to: {output_dir}")
        logger.info(f"Max pages: {args.max_pages or 'unlimited'}")
        logger.info(f"Timeout: {args.timeout}s per page")
        logger.info(f"Force refresh: {args.force}")
        
        downloaded_count = download_user_docs(
            sitemap_urls=sitemap_urls,
            output_dir=output_dir,
            max_pages=args.max_pages,
            timeout=args.timeout,
            force=args.force
        )
        
        print("=" * 80)
        print("USER DOCUMENTATION DOWNLOAD COMPLETE")
        print("=" * 80)
        print(f"Successfully downloaded: {downloaded_count} pages")
        print(f"Output directory: {output_dir}")
        print(f"Total URLs processed: {len(sitemap_urls)}")
        
        if downloaded_count < len(sitemap_urls):
            print(f"Note: {len(sitemap_urls) - downloaded_count} URLs were skipped or failed")
        
        print("=" * 80)
        
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
