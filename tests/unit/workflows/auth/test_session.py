"""Unit tests for auth session setup workflows."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from endorlabs.workflows.auth.dotenv import read_dotenv_value, upsert_dotenv_key
from endorlabs.workflows.auth.env_resolution import sso_tenant_from_namespace
from endorlabs.workflows.auth.session import (
    build_browser_auth_kwargs,
    refresh_token_to_dotenv,
    resolve_sso_tenant,
    scan_auth_env,
    verify_auth,
)


def test_sso_tenant_from_namespace_uses_root_segment() -> None:
    assert sso_tenant_from_namespace("root.child") == "root"
    assert sso_tenant_from_namespace("solo") == "solo"


def test_read_dotenv_value_strips_quotes(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text('ENDOR_NAMESPACE="tenant.ns"\n', encoding="utf-8")
    assert read_dotenv_value(env_file, "ENDOR_NAMESPACE") == "tenant.ns"


def test_upsert_dotenv_key_updates_existing(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "ENDOR_NAMESPACE=old\nENDOR_TOKEN=old-token\n", encoding="utf-8"
    )
    upsert_dotenv_key(env_file, "ENDOR_TOKEN", "new-token")
    text = env_file.read_text(encoding="utf-8")
    assert "ENDOR_TOKEN=new-token" in text
    assert "ENDOR_NAMESPACE=old" in text
    assert "old-token" not in text


@pytest.mark.skipif(sys.platform == "win32", reason="Unix file mode semantics")
def test_upsert_dotenv_key_writes_private_mode(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    upsert_dotenv_key(env_file, "ENDOR_TOKEN", "secret-token")
    assert env_file.stat().st_mode & 0o777 == 0o600


def test_scan_auth_env_dual_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENDOR_TOKEN", "token")
    monkeypatch.setenv("ENDOR_API_CREDENTIALS_KEY", "key")
    monkeypatch.setenv("ENDOR_API_CREDENTIALS_SECRET", "secret")
    scan = scan_auth_env()
    assert scan.dual_mode_conflict is True
    assert scan.has_any_credentials is True


def test_resolve_sso_tenant_prefers_namespace_flag(tmp_path: Path) -> None:
    tenant = resolve_sso_tenant(
        namespace="explicit-tenant",
        env_file=tmp_path / ".env",
    )
    assert tenant == "explicit-tenant"


def test_resolve_sso_tenant_from_dotenv_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ENDOR_NAMESPACE", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text("ENDOR_NAMESPACE=tenant.from.file\n", encoding="utf-8")
    tenant = resolve_sso_tenant(namespace=None, env_file=env_file)
    assert tenant == "tenant"


def test_build_browser_auth_kwargs_sso(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENDOR_NAMESPACE", "my-tenant.child")
    kwargs = build_browser_auth_kwargs(
        method="sso",
        namespace=None,
        env_file=Path(".env"),
        environment="endorlabs.com",
        timeout=120,
    )
    assert kwargs == {
        "timeout": 120,
        "environment": "endorlabs.com",
        "method": "sso",
        "auth_tenant": "my-tenant",
    }


def test_build_browser_auth_kwargs_missing_tenant_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ENDOR_NAMESPACE", raising=False)
    monkeypatch.setattr(
        "endorlabs.workflows.auth.env_resolution.read_endorctl_namespace",
        lambda: None,
    )
    with pytest.raises(ValueError, match="Tenant SSO requires"):
        build_browser_auth_kwargs(
            method="sso",
            namespace=None,
            env_file=Path("/nonexistent/.env"),
            environment="endorlabs.com",
            timeout=120,
        )


def test_refresh_token_to_dotenv_writes_token(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    env_file = tmp_path / ".env"
    monkeypatch.setenv("ENDOR_NAMESPACE", "tenant-one")

    with patch(
        "endorlabs.auth_server.get_token",
        return_value="fresh-token",
    ):
        updated = refresh_token_to_dotenv(
            env_file,
            method="sso",
            environment="endorlabs.com",
        )

    assert updated == env_file.resolve()
    assert read_dotenv_value(env_file, "ENDOR_TOKEN") == "fresh-token"


def test_verify_auth_missing_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for key in (
        "ENDOR_TOKEN",
        "ENDOR_API_CREDENTIALS_KEY",
        "ENDOR_API_CREDENTIALS_SECRET",
    ):
        monkeypatch.delenv(key, raising=False)
    result = verify_auth()
    assert result.status == "missing_credentials"
    assert result.next_steps


def test_verify_auth_dual_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENDOR_TOKEN", "token")
    monkeypatch.setenv("ENDOR_API_CREDENTIALS_KEY", "key")
    monkeypatch.setenv("ENDOR_API_CREDENTIALS_SECRET", "secret")
    result = verify_auth()
    assert result.status == "dual_mode_conflict"


def test_auth_verification_json_omits_credential_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from endorlabs.core.whoami import WhoamiResult

    monkeypatch.setenv("ENDOR_TOKEN", "super-secret-bearer-token-value")
    monkeypatch.delenv("ENDOR_API_CREDENTIALS_KEY", raising=False)
    monkeypatch.delenv("ENDOR_API_CREDENTIALS_SECRET", raising=False)

    mock_client = MagicMock()
    mock_client.whoami.return_value = WhoamiResult(
        identity="user@example.com",
        auth_type="browser",
    )

    with patch("endorlabs.Client", return_value=mock_client):
        result = verify_auth(tenant="tenant.ns")

    payload = result.to_json()
    assert "super-secret-bearer-token-value" not in payload
    assert '"has_bearer_token": true' in payload
    assert result.status == "ready"


def test_redact_sensitive_text_scrubs_token_query() -> None:
    from endorlabs.workflows.auth.session import redact_sensitive_text

    token_fragment = "super-secret-query-token"
    raw = f"redirect failed: /?token={token_fragment}"
    redacted = redact_sensitive_text(raw)
    assert redacted is not None
    assert token_fragment not in redacted
    assert "token=***REDACTED***" in redacted


def test_resolve_sso_tenant_ignores_init_auth_tenant_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ENDOR_INIT_AUTH_TENANT is init-only and must not resolve refresh tenant."""
    monkeypatch.delenv("ENDOR_NAMESPACE", raising=False)
    monkeypatch.setenv("ENDOR_INIT_AUTH_TENANT", "init-only-tenant")
    monkeypatch.setattr(
        "endorlabs.workflows.auth.env_resolution.read_endorctl_namespace",
        lambda: None,
    )
    tenant = resolve_sso_tenant(namespace=None, env_file=Path("/nonexistent/.env"))
    assert tenant is None


def test_verify_auth_includes_resolved_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENDOR_TOKEN", "token")
    monkeypatch.setenv("ENDOR_NAMESPACE", "tenant.child")
    monkeypatch.delenv("ENDOR_API_CREDENTIALS_KEY", raising=False)
    monkeypatch.delenv("ENDOR_API_CREDENTIALS_SECRET", raising=False)

    from endorlabs.core.whoami import WhoamiResult

    mock_client = MagicMock()
    mock_client.whoami.return_value = WhoamiResult(
        identity="user@example.com",
        auth_type="browser",
        expires_in_seconds=3600.0,
    )

    with patch("endorlabs.Client", return_value=mock_client):
        result = verify_auth(tenant="tenant.child")

    payload = result.to_dict()
    assert payload["auth_mode_resolved"] == "bearer"
    assert payload["sso_tenant_resolved"] == "tenant"


def test_verify_auth_ready(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENDOR_TOKEN", "token")
    monkeypatch.delenv("ENDOR_API_CREDENTIALS_KEY", raising=False)
    monkeypatch.delenv("ENDOR_API_CREDENTIALS_SECRET", raising=False)

    mock_client = MagicMock()
    mock_whoami = MagicMock()
    mock_whoami.identity = "user@example.com"
    mock_client.whoami.return_value = mock_whoami

    with patch("endorlabs.Client", return_value=mock_client):
        result = verify_auth(tenant="tenant.ns")

    assert result.status == "ready"
    assert result.whoami is mock_whoami
    mock_client.close.assert_called_once()
