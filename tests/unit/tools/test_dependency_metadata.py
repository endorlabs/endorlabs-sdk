"""Tests for tools.dependency_metadata summarization."""

from __future__ import annotations

from endorlabs.tools.dependency_metadata import summarize_dep_metadata


def test_summarize_dep_metadata_empty() -> None:
    stats = summarize_dep_metadata([])
    assert stats["total"] == 0
    assert stats["direct"] == 0


def test_summarize_dep_metadata_counts() -> None:
    rows = [
        {
            "spec": {
                "dependency_data": {
                    "direct": True,
                    "reachable": "REACHABLE_FUNCTION",
                    "ecosystem": "ECOSYSTEM_NPM",
                    "scope": "SCOPE_PRODUCTION",
                }
            }
        },
        {
            "spec": {
                "dependency_data": {
                    "direct": False,
                    "reachable": "UNREACHABLE",
                    "ecosystem": "ECOSYSTEM_NPM",
                    "scope": "SCOPE_TEST",
                }
            }
        },
    ]
    stats = summarize_dep_metadata(rows)
    assert stats["total"] == 2
    assert stats["direct"] == 1
    assert stats["transitive"] == 1
    assert stats["reachable"] == 1
    assert stats["unreachable"] == 1
    assert stats["by_ecosystem"]["ECOSYSTEM_NPM"] == 2
