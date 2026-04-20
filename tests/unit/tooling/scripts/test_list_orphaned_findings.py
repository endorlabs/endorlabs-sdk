"""Unit tests for scripts/list_orphaned_findings.py."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from scripts import list_orphaned_findings as orphaned


def test_delete_orphaned_findings_hides_exception_details() -> None:
    client = MagicMock()
    client.Finding.delete.side_effect = RuntimeError("sensitive backend detail")
    client.close.return_value = None
    orphan = MagicMock()
    orphan.uuid = "finding-1"
    with patch.object(orphaned.endorlabs, "Client", return_value=client):
        result = orphaned._delete_orphaned_findings(
            tenant="tenant.ns",
            findings=[orphan],
            auto_approve=True,
        )

    assert result["failed"] == 1
    assert result["deleted"] == 0
    errors = result["errors"]
    assert isinstance(errors, list)
    assert errors == [{"uuid": "finding-1", "error": "delete_failed"}]
