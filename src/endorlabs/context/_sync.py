"""Core sync logic for context bootstrap.

Downloads OpenAPI spec and user documentation from Endor Labs.
Requires authentication via APIClient - no public URL fallback.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
import shutil
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, cast
from urllib.parse import urlparse

import defusedxml.ElementTree as DefusedElementTree
import httpx

if TYPE_CHECKING:
    from endorlabs.api_client import APIClient

from endorlabs.utils.logging_config import get_resource_logger

from .models import InitStatus
from .paths import (
    DEFAULT_CONTEXT_DIR,
    SDK_DIRNAME,
    context_json_path,
    platform_openapi_path,
    platform_user_docs_path,
    sdk_dir,
)

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
LLMS_INDEX_URL = "https://docs.endorlabs.com/llms.txt"
OPENAPI_PATH = "/download/openapiv2.swagger.json"

# Default output paths (single source of truth for context downloads)
DEFAULT_OPENAPI_FILENAME = "openapiv2.swagger.json"
DEFAULT_USER_DOCS_DIRNAME = "user-docs"
DOCS_HASH_MANIFEST_FILENAME = "_content-hashes.md"
SKILLS_TARGETS: tuple[str, ...] = ("cursor", "claude")
SkillSyncMode = Literal["none", "cursor", "claude", "both"]
CONTEXT_JSON_SCHEMA_VERSION = 1


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


def _canonicalize_doc_url(url: str) -> str:
    """Return canonical docs page URL without markdown/index suffix."""
    normalized = _normalize_url(url.strip())
    parsed = urlparse(normalized)
    path = parsed.path.rstrip("/")
    if path.endswith("/index.md"):
        path = path.removesuffix("/index.md")
    elif path.endswith(".md"):
        path = path.removesuffix(".md")
    if not path:
        path = "/"
    return f"https://docs.endorlabs.com{path}"


def _is_included_doc_url(url: str) -> bool:
    """Whether URL should be included in the local user-doc sync corpus."""
    parsed = urlparse(url)
    path = parsed.path.lower()
    if path.startswith("/api-reference/"):
        return False
    if path in {"/llms.txt", "/llms-full.txt"}:
        return False
    return not path.endswith(".json")


def _extract_urls_from_llms_index(content: str) -> list[str]:
    """Extract docs URLs from llms.txt markdown index."""
    matches = re.findall(r"\((https://docs\.endorlabs\.com/[^\s)]+)\)", content)
    extracted: list[str] = []
    seen: set[str] = set()
    for match in matches:
        canonical = _canonicalize_doc_url(match)
        if not _is_included_doc_url(canonical):
            continue
        if canonical in seen:
            continue
        seen.add(canonical)
        extracted.append(canonical)
    return extracted


def _safe_path_segment(part: str) -> str:
    """Make a URL segment filesystem-safe while preserving readability."""
    return re.sub(r"[^\w\-_.]", "_", part)


def _generate_relative_output_path(doc_url: str) -> Path:
    """Generate readable relative path from canonical docs URL."""
    parsed_url = urlparse(doc_url)
    raw_parts = [part for part in parsed_url.path.strip("/").split("/") if part]
    if not raw_parts:
        return Path("index.md")
    clean_parts = [_safe_path_segment(part) for part in raw_parts]
    return Path(*clean_parts).with_suffix(".md")


def _doc_markdown_source_url(doc_url: str) -> str:
    """Return source markdown URL for a canonical docs page URL."""
    path = urlparse(doc_url).path.rstrip("/")
    if not path:
        return "https://docs.endorlabs.com/index.md"
    return f"https://docs.endorlabs.com{path}/index.md"


# MDX inline component: export const Name = () => { ... return <code>...</code>; ... };
_MINTLIFY_INLINE_EXPORT_RE = re.compile(
    r"export const (\w+)\s*=\s*\(\)\s*=>\s*\{[\s\S]*?"
    r"return\s*<code>(.*?)</code>;[\s\S]*?\n\};",
    re.MULTILINE,
)

_MINTLIFY_FIELD_PREFIXES: tuple[str, ...] = (
    "    - Flag:",
    "    Environment_Variable:",
    "    Type:",
    "    Description:",
)


def _mintlify_replace_inline_components(text: str) -> str:
    """Replace MDX inline component exports with backtick literals."""
    inline_component_values: dict[str, str] = {}
    for match in _MINTLIFY_INLINE_EXPORT_RE.finditer(text):
        inline_component_values[match.group(1)] = match.group(2).strip()

    for name, value in inline_component_values.items():
        text = re.sub(rf"<{re.escape(name)}\s*/>", f"`{value}`", text)
    return text


def _mintlify_strip_mdx_noise(text: str) -> str:
    """Strip MDX component definitions/imports that are not user-doc content."""
    text = re.sub(
        r"^export const [\s\S]*?^\};\n?",
        "",
        text,
        flags=re.MULTILINE,
    )
    text = re.sub(r"^import .*$\n?", "", text, flags=re.MULTILINE)
    text = text.replace("\\`", "`")
    return re.sub(r"```(\w+)\s+theme=\{null\}", r"```\1", text)


def _mintlify_skip_documentation_index_block(lines: list[str]) -> list[str]:
    """Drop Mintlify index boilerplate blockquote after 'Documentation Index'."""
    skip_through = 0
    for i, line in enumerate(lines[:12]):
        if "Documentation Index" in line:
            skip_through = i + 1
            break
    while skip_through < len(lines) and lines[skip_through].strip():
        skip_through += 1
    if skip_through > 0:
        return lines[skip_through + 1 :]
    return lines


def _mintlify_normalize_body_line(line: str) -> str | None:
    """Normalize one body line; return None to drop the line."""
    stripped = line.strip()
    if stripped in {"{`", "`}", "{", "}"}:
        return None
    if re.fullmatch(r"</?[A-Za-z][A-Za-z0-9]*(\s+[^>]*)?>", stripped):
        return None
    if any(line.startswith(p) for p in _MINTLIFY_FIELD_PREFIXES):
        return line[4:]
    return line


def _mintlify_collapse_blank_runs(lines: list[str]) -> list[str]:
    """Collapse long blank runs; trim trailing whitespace-only lines."""
    compacted: list[str] = []
    blank_run = 0
    for line in lines:
        if line.strip():
            blank_run = 0
            compacted.append(line)
            continue
        blank_run += 1
        if blank_run <= 2:
            compacted.append(line)

    while compacted and not compacted[-1].strip():
        del compacted[-1]
    return compacted


def _normalize_mintlify_markdown(markdown: str) -> str:
    """Normalize Mintlify markdown for RAG-friendly local context."""
    text = markdown.replace("\r\n", "\n")
    text = _mintlify_replace_inline_components(text)
    text = _mintlify_strip_mdx_noise(text)
    lines = text.splitlines()
    lines = _mintlify_skip_documentation_index_block(lines)
    normalized: list[str] = []
    for line in lines:
        out = _mintlify_normalize_body_line(line)
        if out is not None:
            normalized.append(out)
    compacted = _mintlify_collapse_blank_runs(normalized)
    return "\n".join(compacted) + "\n"


def _extract_title_from_markdown(markdown: str, *, fallback_url: str) -> str:
    """Extract first H1 from markdown body; fallback to URL-derived title."""
    for line in markdown.splitlines():
        if line.startswith("# "):
            title = line[2:].strip()
            if title:
                return title
    tail = urlparse(fallback_url).path.strip("/").split("/")[-1]
    tail = tail.replace("-", " ").replace("_", " ").strip() or "Documentation"
    return tail.title()


def _compute_content_hash(content: str) -> str:
    """Return SHA-256 hash for normalized content."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _extract_markdown_body(markdown_file: Path) -> str | None:
    """Extract body content from markdown file with optional frontmatter."""
    try:
        text = markdown_file.read_text(encoding="utf-8")
    except Exception:
        return None
    if not text.startswith("---"):
        return text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return text
    return parts[2].lstrip("\r\n")


def _load_hash_manifest(manifest_path: Path) -> dict[str, str]:
    """Load markdown hash manifest into ``{relative_path: sha256}``."""
    if not manifest_path.exists():
        return {}
    mapping: dict[str, str] = {}
    for line in manifest_path.read_text(encoding="utf-8").splitlines():
        match = re.match(
            r"^\|\s*`([^`]+)`\s*\|\s*`([0-9a-f]{64})`\s*\|\s*.*\|\s*$",
            line,
        )
        if match:
            rel_path, hash_value = match.groups()
            mapping[rel_path] = hash_value
    return mapping


def _write_hash_manifest(
    manifest_path: Path,
    *,
    hashes_by_file: dict[str, str],
    urls_by_file: dict[str, str],
) -> None:
    """Write markdown hash manifest for synced docs."""
    from endorlabs.utils.path_safety import safe_write_text

    lines = [
        "# Docs Content Hash Manifest",
        "",
        f"Generated: {datetime.now(UTC).isoformat()}",
        "",
        "| File | SHA256 | URL |",
        "| --- | --- | --- |",
    ]
    for rel_path in sorted(hashes_by_file):
        hash_value = hashes_by_file[rel_path]
        url = urls_by_file.get(rel_path, "")
        lines.append(f"| `{rel_path}` | `{hash_value}` | {url} |")
    # Keep writes constrained to the selected docs directory.
    safe_write_text(
        manifest_path.parent,
        manifest_path,
        "\n".join(lines) + "\n",
    )


def _prune_stale_docs(
    output_dir: Path,
    *,
    expected_rel_paths: set[str],
    existing_hashes: dict[str, str],
) -> int:
    """Remove stale generated markdown files no longer part of current corpus."""
    removed = 0
    base_resolved = output_dir.resolve()
    stale_rel_paths = set(existing_hashes).difference(expected_rel_paths)
    for rel_path in sorted(stale_rel_paths):
        target = (output_dir / rel_path).resolve()
        if not target.is_relative_to(base_resolved):
            continue
        if target.exists() and target.is_file():
            target.unlink()
            removed += 1
        parent = target.parent
        while parent != base_resolved and parent.exists():
            try:
                parent.rmdir()
            except OSError:
                break
            parent = parent.parent
    return removed


def _normalize_skill_sync_mode(target: str) -> SkillSyncMode:
    """Validate and normalize a skill sync mode string."""
    normalized = target.strip().lower()
    valid_targets = {"none", "cursor", "claude", "both"}
    if normalized not in valid_targets:
        raise ValueError(
            f"Unsupported sync_skills value {target!r}. "
            "Expected one of: none, cursor, claude, both."
        )
    return cast("SkillSyncMode", normalized)


def _skill_target_dir(repo_root: Path, target: str) -> Path:
    """Return the runtime skills directory for a target host."""
    return repo_root / f".{target}" / "skills"


def _resolve_skill_sync_targets(
    *,
    target: SkillSyncMode,
) -> tuple[str, ...]:
    """Resolve a sync mode to concrete runtime target names."""
    if target == "none":
        return ()
    if target == "both":
        return SKILLS_TARGETS
    if target in SKILLS_TARGETS:
        return (target,)
    return ()


def _prune_stale_skill_files(
    *,
    target_dir: Path,
    expected_rel_paths: set[str],
) -> None:
    """Remove mirrored files that no longer exist in the source tree."""
    if not target_dir.exists():
        return
    base_resolved = target_dir.resolve()
    stale_files = [
        path
        for path in target_dir.rglob("*")
        if path.is_file()
        and path.relative_to(target_dir).as_posix() not in expected_rel_paths
    ]
    for path in stale_files:
        resolved = path.resolve()
        if not resolved.is_relative_to(base_resolved):
            continue
        resolved.unlink()
        parent = resolved.parent
        while parent != base_resolved and parent.exists():
            try:
                parent.rmdir()
            except OSError:
                break
            parent = parent.parent


def _mirror_skill_tree(source_dir: Path, target_dir: Path) -> int:
    """Mirror the source skill tree to a runtime directory."""
    if not source_dir.exists():
        raise FileNotFoundError(f"Skills source directory does not exist: {source_dir}")
    target_dir.mkdir(parents=True, exist_ok=True)
    base_resolved = target_dir.resolve()
    expected_rel_paths: set[str] = set()
    mirrored_files = 0

    for source_path in source_dir.rglob("*"):
        if not source_path.is_file():
            continue
        rel_path = source_path.relative_to(source_dir)
        expected_rel_paths.add(rel_path.as_posix())
        dest_path = target_dir / rel_path
        resolved_dest = dest_path.resolve()
        if not resolved_dest.is_relative_to(base_resolved):
            raise ValueError(
                "Skill mirror target "
                f"{resolved_dest} escapes base directory {base_resolved}"
            )
        resolved_dest.parent.mkdir(parents=True, exist_ok=True)
        _ = shutil.copy2(source_path, resolved_dest)
        mirrored_files += 1

    _prune_stale_skill_files(
        target_dir=target_dir,
        expected_rel_paths=expected_rel_paths,
    )
    return mirrored_files


def sync_agent_skills(
    *,
    repo_root: str | Path = ".",
    target: SkillSyncMode = "none",
    source_dir: str | Path | None = None,
) -> dict[str, Path]:
    """Sync repo skill sources into runtime discovery directories."""
    repo_root_path = Path(repo_root)
    normalized_target = _normalize_skill_sync_mode(target)
    resolved_targets = _resolve_skill_sync_targets(
        target=normalized_target,
    )
    if not resolved_targets:
        logger.info(
            "Skill sync skipped for target=%s (no runtime target resolved).", target
        )
        return {}

    source_root = (
        Path(source_dir)
        if source_dir is not None
        else _resolve_skill_source_root(repo_root_path)
    )
    if not source_root.is_absolute():
        source_root = repo_root_path / source_root

    synced_paths: dict[str, Path] = {}
    for resolved_target in resolved_targets:
        target_dir = _skill_target_dir(repo_root_path, resolved_target)
        mirrored_files = _mirror_skill_tree(source_root, target_dir)
        logger.info(
            "Synced %d skill files to %s runtime path %s",
            mirrored_files,
            resolved_target,
            target_dir,
        )
        synced_paths[resolved_target] = target_dir
    return synced_paths


def _resolve_skill_source_root(repo_root_path: Path) -> Path:
    """Resolve skill mirror source from materialized sdk/skills or wheel bundle."""
    materialized = repo_root_path / DEFAULT_CONTEXT_DIR / SDK_DIRNAME / "skills"
    if materialized.is_dir():
        return materialized
    from endorlabs.agent_knowledge import agent_knowledge_dir

    return agent_knowledge_dir() / "skills"


def materialize_agent_knowledge(
    output_dir: str | Path,
    *,
    force: bool = False,
) -> Path:
    """Copy the wheel-shipped agent knowledge package into context sdk/."""
    from endorlabs.agent_knowledge import agent_knowledge_dir

    output_path = Path(output_dir)
    dest = sdk_dir(output_path)
    source = agent_knowledge_dir()
    if dest.exists() and not force:
        logger.info(
            "Agent knowledge already materialized: %s (use force=True to refresh)",
            dest,
        )
        return dest
    if dest.exists():
        shutil.rmtree(dest)
    _ = shutil.copytree(source, dest)
    logger.info("Materialized agent knowledge to %s", dest)
    return dest


def write_context_json(
    *,
    output_dir: Path,
    sdk_version: str,
    agent_knowledge_path: Path | None,
    platform_openapi: Path | None,
    platform_user_docs: Path | None,
    include_openapi: bool,
    include_user_docs: bool,
    sync_skills: SkillSyncMode,
) -> Path:
    """Write or update context.json init manifest."""
    manifest_path = context_json_path(output_dir)
    payload = {
        "schema_version": CONTEXT_JSON_SCHEMA_VERSION,
        "sdk_version": sdk_version,
        "materialized_at": datetime.now(UTC).isoformat(),
        "agent_knowledge_path": (
            str(agent_knowledge_path) if agent_knowledge_path else None
        ),
        "context_json_path": str(manifest_path),
        "platform_openapi_path": str(platform_openapi) if platform_openapi else None,
        "platform_user_docs_path": str(platform_user_docs)
        if platform_user_docs
        else None,
        "flags": {
            "include_openapi": include_openapi,
            "include_user_docs": include_user_docs,
            "sync_skills": sync_skills,
        },
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(manifest_path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        _ = handle.write("\n")
    return manifest_path


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
        root = DefusedElementTree.fromstring(response.content)
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


async def _download_llms_index(timeout: int = 10) -> list[str]:
    """Download llms.txt index and extract docs URLs."""
    try:
        logger.info("Downloading docs index from: %s", LLMS_INDEX_URL)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(LLMS_INDEX_URL)
            _ = response.raise_for_status()
        extracted = _extract_urls_from_llms_index(response.text)
        logger.info("Found %d docs URLs in llms index", len(extracted))
        return extracted
    except Exception as e:
        logger.warning("Unable to download llms index: %s", e)
        return []


async def _download_single_page(
    client: httpx.AsyncClient,
    doc_url: str,
    output_file: Path,
    base_dir: Path,
    previous_hash: str | None,
    force: bool,
) -> tuple[int, str | None]:
    """Download and convert single page to markdown."""
    from endorlabs.utils.path_safety import safe_write_text

    try:
        source_url = _doc_markdown_source_url(doc_url)
        response = await client.get(source_url)
        _ = response.raise_for_status()
        markdown_content = _normalize_mintlify_markdown(response.text)
        content_hash = _compute_content_hash(markdown_content)

        if not force:
            existing_hash = previous_hash
            if existing_hash is None and output_file.exists():
                existing_body = _extract_markdown_body(output_file)
                if existing_body is not None:
                    existing_hash = _compute_content_hash(existing_body)
            if existing_hash == content_hash:
                return (0, content_hash)

        # Add metadata header
        title = _extract_title_from_markdown(markdown_content, fallback_url=doc_url)
        metadata = f"""---
url: {doc_url}
title: {title}
downloaded: {time.strftime("%Y-%m-%d %H:%M:%S")}
---

{markdown_content}
"""
        safe_write_text(base_dir, output_file, metadata)
        return (1, content_hash)

    except Exception as e:
        logger.warning("Unable to download %s: %s", doc_url, e)
        return (0, None)


async def _download_one(
    client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
    doc_url: str,
    rel_path: str,
    output_file: Path,
    base_dir: Path,
    previous_hash: str | None,
    force: bool,
) -> tuple[str, int, str | None, str]:
    """Download one page and return sync stats tuple."""
    async with semaphore:
        try:
            changed_count, content_hash = await _download_single_page(
                client,
                doc_url,
                output_file,
                base_dir,
                previous_hash,
                force,
            )
            return (rel_path, changed_count, content_hash, doc_url)
        except Exception as e:
            logger.warning("Unable to process %s: %s", doc_url, e)
            return (rel_path, 0, None, doc_url)


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
    output_dir.mkdir(parents=True, exist_ok=True)

    # Discover docs pages from Mintlify llms index first.
    doc_urls = await _download_llms_index(timeout)
    if not doc_urls:
        # Fallback for legacy docs hosts if llms index is unavailable.
        sitemap_urls = await _download_sitemap(timeout)
        doc_urls = [_canonicalize_doc_url(url) for url in sitemap_urls]
        doc_urls = [url for url in doc_urls if _is_included_doc_url(url)]
    if not doc_urls:
        logger.error("No documentation URLs found")
        return 0

    urls = doc_urls[:max_pages] if max_pages else doc_urls
    work_list: list[tuple[str, str, Path, str | None]] = []
    manifest_path = output_dir / DOCS_HASH_MANIFEST_FILENAME
    existing_hashes = _load_hash_manifest(manifest_path)

    for url in urls:
        canonical_url = _canonicalize_doc_url(url)
        rel_path = _generate_relative_output_path(canonical_url).as_posix()
        output_file = output_dir / rel_path
        previous_hash = existing_hashes.get(rel_path)
        work_list.append((canonical_url, rel_path, output_file, previous_hash))

    expected_rel_paths = {rel_path for _, rel_path, _, _ in work_list}
    if max_pages is None:
        removed_stale = _prune_stale_docs(
            output_dir,
            expected_rel_paths=expected_rel_paths,
            existing_hashes=existing_hashes,
        )
        if removed_stale:
            logger.info("Pruned %d stale docs from previous sync runs", removed_stale)

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
            _download_one(
                client,
                semaphore,
                doc_url,
                rel_path,
                output_file,
                output_dir,
                previous_hash,
                force,
            )
            for doc_url, rel_path, output_file, previous_hash in work_list
        ]
        results = await asyncio.gather(*tasks)

    changed_count = 0
    updated_hashes = {
        rel_path: existing_hashes[rel_path]
        for rel_path in expected_rel_paths
        if rel_path in existing_hashes
    }
    urls_by_file: dict[str, str] = {}
    for rel_path, changed, content_hash, full_url in results:
        urls_by_file[rel_path] = full_url
        if content_hash is not None:
            updated_hashes[rel_path] = content_hash
        changed_count += changed

    _write_hash_manifest(
        manifest_path,
        hashes_by_file=updated_hashes,
        urls_by_file=urls_by_file,
    )
    logger.info(
        "Docs sync complete: %d changed, %d unchanged",
        changed_count,
        len(results) - changed_count,
    )
    return changed_count


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
    include_agent_knowledge: bool = True,
    max_pages: int | None = None,
    force: bool = False,
    sync_skills: SkillSyncMode = "none",
    client: APIClient | None = None,
) -> InitStatus:
    """Bootstrap Endor Labs context for agentic workflows.

    Always materializes the shipped agent knowledge package under ``sdk/`` (no auth).
    Optionally downloads OpenAPI spec and user docs under ``platform/``, and
    mirrors materialized skills into IDE discovery directories.

    Args:
        output_dir: Directory to save context files (default: .endorlabs-context).
        include_openapi: Download OpenAPI spec (default: True).
        include_user_docs: Download user documentation (default: True).
        include_agent_knowledge: Materialize agent knowledge to sdk/ (default: True).
        max_pages: Maximum number of user doc pages to download (default: all).
        force: Force re-download / refresh even if files exist (default: False).
        sync_skills: Mirror materialized ``sdk/skills/`` into runtime dirs
            (``none``, ``cursor``, ``claude``, or ``both``; default ``none``).
        client: Optional APIClient instance. If not provided, one is created
            when ``include_openapi=True`` (requires ENDOR_API_CREDENTIALS_KEY/
            SECRET or ENDOR_TOKEN env vars).

    Returns:
        InitStatus with paths to materialized and downloaded files.

    Raises:
        endorlabs.UnauthorizedError: If OpenAPI authentication fails.
        ImportError: If context dependencies are not installed (for user docs).

    Example::

        >>> import endorlabs
        >>> status = endorlabs.init()
        >>> print(status.agent_knowledge_path)
        .endorlabs-context/sdk

    """
    from endorlabs import __version__
    from endorlabs.api_client import APIClient as APIClientClass

    output_path = Path(output_dir)
    normalized_sync_target = _normalize_skill_sync_mode(sync_skills)
    needs_context_dir = (
        include_agent_knowledge
        or include_openapi
        or include_user_docs
        or normalized_sync_target != "none"
    )
    if needs_context_dir:
        output_path.mkdir(parents=True, exist_ok=True)

    agent_knowledge_dest: Path | None = None
    if include_agent_knowledge:
        agent_knowledge_dest = materialize_agent_knowledge(output_path, force=force)

    platform_openapi: Path | None = None
    platform_user_docs: Path | None = None
    user_docs_count = 0
    synced_skill_paths: dict[str, Path] = {}

    if include_openapi:
        api_client = client or APIClientClass()
        platform_openapi = sync_openapi(
            output_path=platform_openapi_path(output_path),
            force=force,
            client=api_client,
        )

    if include_user_docs:
        docs_dir = platform_user_docs_path(output_path)
        user_docs_count = sync_user_docs(
            output_dir=docs_dir,
            max_pages=max_pages,
            force=force,
        )
        platform_user_docs = docs_dir

    if normalized_sync_target != "none":
        skill_source = sdk_dir(output_path) / "skills"
        if not skill_source.is_dir():
            if include_agent_knowledge:
                skill_source = (
                    agent_knowledge_dest / "skills"
                    if agent_knowledge_dest
                    else skill_source
                )
            else:
                from endorlabs.agent_knowledge import agent_knowledge_dir

                skill_source = agent_knowledge_dir() / "skills"
        synced_skill_paths = sync_agent_skills(
            repo_root=output_path.resolve().parent,
            target=normalized_sync_target,
            source_dir=skill_source,
        )

    manifest_path = write_context_json(
        output_dir=output_path,
        sdk_version=__version__,
        agent_knowledge_path=agent_knowledge_dest,
        platform_openapi=platform_openapi,
        platform_user_docs=platform_user_docs,
        include_openapi=include_openapi,
        include_user_docs=include_user_docs,
        sync_skills=normalized_sync_target,
    )

    return InitStatus(
        agent_knowledge_path=agent_knowledge_dest,
        context_json_path=manifest_path,
        platform_openapi_path=platform_openapi,
        platform_user_docs_path=platform_user_docs,
        user_docs_count=user_docs_count,
        downloaded_at=datetime.now(UTC),
        synced_skill_paths=synced_skill_paths,
    )
