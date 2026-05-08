"""Additional edge-case tests for session_artifacts helpers."""

from __future__ import annotations

from endorlabs.workflows.agent_context import session_artifacts


def test_apply_generated_timestamp_replaces_header_once() -> None:
    markdown = "# Project Session Summary\n\n*Generated at old-ts*\nbody"
    updated = session_artifacts._apply_generated_timestamp(
        markdown, "2026-05-08T10:00:00Z"
    )
    assert updated.startswith("# Project Session Summary")
    assert "*Generated at 2026-05-08T10:00:00Z*" in updated


def test_sort_findings_raw_orders_by_severity_then_uuid() -> None:
    findings = [
        {"level": "FINDING_LEVEL_MEDIUM", "uuid": "c"},
        {"level": "FINDING_LEVEL_CRITICAL", "uuid": "b"},
        {"level": "FINDING_LEVEL_CRITICAL", "uuid": "a"},
    ]
    sorted_findings = session_artifacts._sort_findings_raw(findings)
    assert [f["uuid"] for f in sorted_findings] == ["a", "b", "c"]
