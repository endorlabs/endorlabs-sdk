"""Tests for Client.whoami() method.

Verifies identity resolution via AuthorizationPolicy filtering
by spec.clause containing the API key.
"""

from unittest.mock import Mock

import pytest

import endorlabs
from endorlabs.api_client import APIClient
from endorlabs.client_surface import Client
from tests.conftest import TEST_NAMESPACE_DEFAULT


@pytest.fixture
def mock_api_client() -> Mock:
    """Create a mock APIClient with api-key auth attributes."""
    mock = Mock(spec=APIClient)
    mock._auth_type = "api-key"
    mock.key = "endr+TestKey123"
    return mock


@pytest.fixture
def client_with_api_key(mock_api_client: Mock) -> Client:
    """Client with mock api-key transport."""
    return endorlabs.Client(
        api_client=mock_api_client,
        tenant=TEST_NAMESPACE_DEFAULT,
    )


class TestWhoAmI:
    """Tests for Client.whoami()."""

    def test_whoami_returns_meta_name_on_match(
        self,
        client_with_api_key: Client,
    ) -> None:
        """whoami returns meta.name from matching AuthorizationPolicy."""
        mock_policy = Mock()
        mock_policy.meta.name = "tgowan@endor.ai"

        client_with_api_key.authorization_policy._list_fn = Mock(
            return_value=[mock_policy],
        )

        result = client_with_api_key.whoami()
        assert result == "tgowan@endor.ai"

    def test_whoami_returns_none_when_no_match(
        self,
        client_with_api_key: Client,
    ) -> None:
        """whoami returns None when no AuthorizationPolicy matches."""
        client_with_api_key.authorization_policy._list_fn = Mock(
            return_value=[],
        )

        result = client_with_api_key.whoami()
        assert result is None

    def test_whoami_returns_none_for_browser_auth(self) -> None:
        """whoami returns None when auth type is browser (no key)."""
        mock = Mock(spec=APIClient)
        mock._auth_type = "browser"
        mock.key = None
        client = endorlabs.Client(
            api_client=mock,
            tenant=TEST_NAMESPACE_DEFAULT,
        )
        result = client.whoami()
        assert result is None

    def test_whoami_returns_none_when_meta_is_none(
        self,
        client_with_api_key: Client,
    ) -> None:
        """whoami returns None when matching policy has no meta."""
        mock_policy = Mock()
        mock_policy.meta = None

        client_with_api_key.authorization_policy._list_fn = Mock(
            return_value=[mock_policy],
        )

        result = client_with_api_key.whoami()
        assert result is None

    def test_whoami_raises_on_closed_client(self) -> None:
        """whoami raises RuntimeError on a closed client."""
        mock = Mock(spec=APIClient)
        mock._auth_type = "api-key"
        mock.key = "endr+TestKey"
        client = endorlabs.Client(
            api_client=mock,
            tenant=TEST_NAMESPACE_DEFAULT,
        )
        # Simulate closed client
        client._client = None

        with pytest.raises(RuntimeError, match="closed"):
            client.whoami()

    def test_whoami_filter_contains_key(
        self,
        client_with_api_key: Client,
        mock_api_client: Mock,
    ) -> None:
        """whoami passes filter with spec.clause contains the API key."""
        mock_list = Mock(return_value=[])
        client_with_api_key.authorization_policy._list_fn = mock_list

        client_with_api_key.whoami()

        mock_list.assert_called_once()
        _args, _kwargs = mock_list.call_args
        # The list_fn is called with (client, namespace, list_params, ...)
        # Check that filter contains the key
        assert "endr+TestKey123" in str(mock_list.call_args)
