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
    mock.auth_type = "api-key"
    mock.is_api_key_auth = True
    mock.key = "endr+TestKey123"
    mock.get_user_info.return_value = None
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

        client_with_api_key.AuthorizationPolicy._ops.list = Mock(
            return_value=[mock_policy],
        )

        result = client_with_api_key.whoami()
        assert result == "tgowan@endor.ai"

    def test_whoami_returns_none_when_no_match(
        self,
        client_with_api_key: Client,
    ) -> None:
        """whoami returns None when no AuthorizationPolicy matches."""
        client_with_api_key.AuthorizationPolicy._ops.list = Mock(
            return_value=[],
        )

        result = client_with_api_key.whoami()
        assert result is None

    def test_whoami_returns_none_for_browser_auth(self) -> None:
        """whoami returns None when auth type is browser (no key)."""
        mock = Mock(spec=APIClient)
        mock.auth_type = "browser"
        mock.is_api_key_auth = False
        mock.key = None
        mock.get_user_info.return_value = None
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

        client_with_api_key.AuthorizationPolicy._ops.list = Mock(
            return_value=[mock_policy],
        )

        result = client_with_api_key.whoami()
        assert result is None

    def test_whoami_raises_on_closed_client(self) -> None:
        """whoami raises RuntimeError on a closed client."""
        mock = Mock(spec=APIClient)
        mock.auth_type = "api-key"
        mock.is_api_key_auth = True
        mock.key = "endr+TestKey"
        mock.get_user_info.return_value = None
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
        client_with_api_key.AuthorizationPolicy._ops.list = mock_list

        client_with_api_key.whoami()

        mock_list.assert_called_once()
        args, _kwargs = mock_list.call_args
        # _ops.list is called with (namespace, list_params, max_pages)
        # Check that list_params.filter contains the key
        list_params = args[1]
        assert list_params is not None
        assert "endr+TestKey123" in (list_params.filter or "")
        assert list_params.page_size == 1
        assert args[2] == 1

    def test_whoami_returns_none_when_api_key_missing(
        self,
        mock_api_client: Mock,
    ) -> None:
        """whoami returns None when auth is api-key but key is missing."""
        mock_api_client.key = None
        client = endorlabs.Client(
            api_client=mock_api_client,
            tenant=TEST_NAMESPACE_DEFAULT,
        )
        assert client.whoami() is None

    def test_whoami_prefers_v1_auth_email(self, client_with_api_key: Client) -> None:
        """whoami returns canonical email from /v1/auth when available."""
        client_with_api_key._client.get_user_info.return_value = {
            "user": {"spec": {"email": "sdk-user@endor.ai"}}
        }
        result = client_with_api_key.whoami()
        assert result == "sdk-user@endor.ai"

    def test_whoami_falls_back_to_policy_lookup(
        self,
        client_with_api_key: Client,
    ) -> None:
        """whoami falls back to AuthorizationPolicy lookup when v1/auth is empty."""
        client_with_api_key._client.get_user_info.return_value = {}
        mock_policy = Mock()
        mock_policy.meta.name = "fallback@endor.ai"
        client_with_api_key.AuthorizationPolicy._ops.list = Mock(
            return_value=[mock_policy]
        )

        assert client_with_api_key.whoami() == "fallback@endor.ai"

    def test_whoami_returns_none_when_policy_lookup_fails(
        self,
        client_with_api_key: Client,
    ) -> None:
        """whoami does not raise when fallback AuthorizationPolicy lookup fails."""
        client_with_api_key._client.get_user_info.return_value = {}
        client_with_api_key.AuthorizationPolicy._ops.list = Mock(
            side_effect=RuntimeError("401 Unauthorized")
        )
        assert client_with_api_key.whoami() is None
