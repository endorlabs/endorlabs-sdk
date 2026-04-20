"""Unit tests for Mintlify docs sync helpers."""

from pathlib import Path

from endorlabs.context import _sync


def test_extract_urls_from_llms_index_filters_api_reference() -> None:
    """llms index parsing excludes API reference and preserves docs pages."""
    llms_text = """
- [CreateAPIKey](https://docs.endorlabs.com/api-reference/apikeyservice/createapikey.md)
- [scan](https://docs.endorlabs.com/developers-api/cli/commands/scan/index.md)
- [Best practices](https://docs.endorlabs.com/best-practices/index.md)
"""
    urls = _sync._extract_urls_from_llms_index(llms_text)
    api_ref = "https://docs.endorlabs.com/api-reference/apikeyservice/createapikey"
    assert api_ref not in urls
    assert "https://docs.endorlabs.com/developers-api/cli/commands/scan" in urls
    assert "https://docs.endorlabs.com/best-practices" in urls


def test_generate_relative_output_path_is_readable_and_stable() -> None:
    """URL path maps to nested readable markdown path."""
    rel = _sync._generate_relative_output_path(
        "https://docs.endorlabs.com/developers-api/cli/commands/scan"
    )
    assert rel == Path("developers-api/cli/commands/scan.md")


def test_doc_markdown_source_url_appends_index_md() -> None:
    """Canonical URL maps to Mintlify markdown source URL."""
    source_url = _sync._doc_markdown_source_url(
        "https://docs.endorlabs.com/setup-deployment/cli/scan-using-endorctl"
    )
    assert (
        source_url
        == "https://docs.endorlabs.com/setup-deployment/cli/scan-using-endorctl/index.md"
    )


def test_normalize_mintlify_markdown_removes_index_boilerplate_and_wrappers() -> None:
    """Mintlify wrapper artifacts are stripped while content remains."""
    raw = """# ignored
> ## Documentation Index
>
> Fetch the complete documentation index at: https://docs.endorlabs.com/llms.txt

# scan

### Bazel flags

{`
- Flag: `use-bazel`
`}
"""
    normalized = _sync._normalize_mintlify_markdown(raw)
    assert "Documentation Index" not in normalized
    assert "{`" not in normalized
    assert "`}" not in normalized
    assert "# scan" in normalized
    assert "- Flag: `use-bazel`" in normalized


def test_extract_title_from_markdown_prefers_h1() -> None:
    """Title helper reads first markdown H1."""
    title = _sync._extract_title_from_markdown(
        "# Best practices: Working with dependency filters\n\nBody\n",
        fallback_url="https://docs.endorlabs.com/best-practices/dependency-filters",
    )
    assert title == "Best practices: Working with dependency filters"


def test_extract_title_from_markdown_fallback_uses_url_tail() -> None:
    """Title helper falls back to readable URL tail."""
    title = _sync._extract_title_from_markdown(
        "No heading here",
        fallback_url="https://docs.endorlabs.com/setup-deployment/scm-integrations",
    )
    assert title == "Scm Integrations"


def test_prune_stale_docs_removes_old_files_and_empty_dirs(tmp_path: Path) -> None:
    """Stale files from previous sync generations should be removed."""
    docs_dir = tmp_path / "docs"
    stale_file = docs_dir / "api-reference" / "old.md"
    stale_file.parent.mkdir(parents=True, exist_ok=True)
    stale_file.write_text("stale", encoding="utf-8")
    keep_file = docs_dir / "best-practices" / "index.md"
    keep_file.parent.mkdir(parents=True, exist_ok=True)
    keep_file.write_text("keep", encoding="utf-8")

    removed = _sync._prune_stale_docs(
        docs_dir,
        expected_rel_paths={"best-practices/index.md"},
        existing_hashes={
            "api-reference/old.md": "a" * 64,
            "best-practices/index.md": "b" * 64,
        },
    )
    assert removed == 1
    assert not stale_file.exists()
    assert keep_file.exists()
