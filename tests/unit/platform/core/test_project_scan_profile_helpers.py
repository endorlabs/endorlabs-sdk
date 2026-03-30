"""Unit tests for project scan profile helper functions."""

from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from endorlabs.core.exceptions import NotFoundError, ServerError
from endorlabs.resources.project import verify_scan_profile_association


def _project_with_scan_profile(scan_profile_uuid: str) -> SimpleNamespace:
    return SimpleNamespace(spec=SimpleNamespace(scan_profile_uuid=scan_profile_uuid))


def test_verify_scan_profile_association_returns_false_on_not_found() -> None:
    """NotFound should map to a simple 'not associated' result."""
    client = Mock()

    with patch("endorlabs.resources.project.BaseResourceOperations") as mock_ops_cls:
        mock_ops = mock_ops_cls.return_value
        mock_ops.get.side_effect = NotFoundError("missing")
        result = verify_scan_profile_association(
            client, "tenant.ns", "proj-1", "scan-prof-1"
        )

    assert result is False


def test_verify_scan_profile_association_propagates_server_error() -> None:
    """Operational failures should not be collapsed into False."""
    client = Mock()

    with patch("endorlabs.resources.project.BaseResourceOperations") as mock_ops_cls:
        mock_ops = mock_ops_cls.return_value
        mock_ops.get.side_effect = ServerError("backend unavailable")
        with pytest.raises(ServerError):
            verify_scan_profile_association(
                client, "tenant.ns", "proj-1", "scan-prof-1"
            )


def test_verify_scan_profile_association_true_when_matching() -> None:
    """Matching profile UUID should return True."""
    client = Mock()

    with patch("endorlabs.resources.project.BaseResourceOperations") as mock_ops_cls:
        mock_ops = mock_ops_cls.return_value
        mock_ops.get.return_value = _project_with_scan_profile("scan-prof-1")
        result = verify_scan_profile_association(
            client, "tenant.ns", "proj-1", "scan-prof-1"
        )

    assert result is True
