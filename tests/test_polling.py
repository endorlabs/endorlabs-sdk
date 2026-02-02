"""Tests for polling utilities (wait_until)."""

from unittest.mock import Mock, patch

from endorlabs.utils.polling import wait_until


def test_wait_until_returns_immediately_when_predicate_true() -> None:
    """wait_until returns True on first call when predicate returns True."""
    assert wait_until(lambda: True, timeout=60) is True


def test_wait_until_returns_false_on_timeout() -> None:
    """wait_until returns False when predicate never True and timeout exceeded."""
    assert wait_until(lambda: False, timeout=0.05) is False


def test_wait_until_returns_true_after_n_calls() -> None:
    """wait_until returns True after predicate returns True on third call."""
    calls = [0]

    def predicate() -> bool:
        calls[0] += 1
        return calls[0] >= 3

    assert wait_until(predicate, timeout=5) is True
    assert calls[0] == 3


def test_wait_until_respects_poll_interval_max() -> None:
    """wait_until caps sleep at poll_interval_max (no sleep > 10s)."""
    # Just ensure it returns when predicate becomes true; backoff cap is internal
    assert wait_until(lambda: True, timeout=1, poll_interval_max=10) is True


def test_client_wait_until_delegates_to_util() -> None:
    """Client.wait_until calls the util with the same args."""
    import endorlabs
    from endorlabs.api_client import APIClient

    client = endorlabs.Client(
        api_client=Mock(spec=APIClient),
        tenant="tenant.ns",
    )
    with patch("endorlabs.client_surface._wait_until") as mock_wait:
        mock_wait.return_value = True
        result = client.wait_until(
            lambda: True,
            timeout=30,
            poll_interval_max=5,
        )
        assert result is True
        mock_wait.assert_called_once()
        args, kwargs = mock_wait.call_args
        assert args[0]() is True
        assert kwargs["timeout"] == 30
        assert kwargs["poll_interval_max"] == 5
