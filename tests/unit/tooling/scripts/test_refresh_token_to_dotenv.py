"""Unit tests for devtools/refresh_token_to_dotenv.py helpers."""

from __future__ import annotations

import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType

import pytest


def _load_refresh_module() -> ModuleType:
    repo_root = Path(__file__).resolve().parents[4]
    script_path = repo_root / "devtools" / "refresh_token_to_dotenv.py"
    spec = spec_from_file_location("refresh_token_to_dotenv", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_resolve_auth_tenant_prefers_namespace_flag() -> None:
    module = _load_refresh_module()
    tenant = module.resolve_auth_tenant(
        namespace="explicit-tenant",
        env_file=Path("/nonexistent/.env"),
    )
    assert tenant == "explicit-tenant"


def test_resolve_auth_tenant_from_namespace_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_refresh_module()
    monkeypatch.setenv("ENDOR_NAMESPACE", "root.child")
    tenant = module.resolve_auth_tenant(
        namespace=None, env_file=Path("/nonexistent/.env")
    )
    assert tenant == "root"


def test_resolve_auth_tenant_from_dotenv_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_refresh_module()
    for key in ("ENDOR_NAMESPACE",):
        monkeypatch.delenv(key, raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text("ENDOR_NAMESPACE=tenant.from.file\n", encoding="utf-8")
    tenant = module.resolve_auth_tenant(namespace=None, env_file=env_file)
    assert tenant == "tenant"


def test_resolve_auth_mode_defaults_to_sso(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_refresh_module()
    monkeypatch.delenv("ENDOR_AUTH_METHOD", raising=False)
    assert (
        module.resolve_auth_mode(admin=False, sso=False, env_file=Path(".env")) == "sso"
    )


def test_resolve_auth_mode_from_env_admin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_refresh_module()
    monkeypatch.setenv("ENDOR_AUTH_METHOD", "admin")
    assert (
        module.resolve_auth_mode(admin=False, sso=False, env_file=Path(".env"))
        == "admin"
    )


def test_resolve_auth_mode_mutually_exclusive_flags() -> None:
    module = _load_refresh_module()
    with pytest.raises(SystemExit, match="mutually exclusive"):
        module.resolve_auth_mode(admin=True, sso=True, env_file=Path(".env"))


def test_resolve_get_token_kwargs_admin() -> None:
    module = _load_refresh_module()
    kwargs = module.resolve_get_token_kwargs(
        admin=True,
        sso=False,
        namespace=None,
        env_file=Path(".env"),
        environment="endorlabs.com",
        timeout=90,
    )
    assert kwargs == {
        "timeout": 90,
        "environment": "endorlabs.com",
        "method": "admin",
    }


def test_resolve_get_token_kwargs_sso_flag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_refresh_module()
    monkeypatch.setenv("ENDOR_NAMESPACE", "my-tenant.child")
    kwargs = module.resolve_get_token_kwargs(
        admin=False,
        sso=True,
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


def test_resolve_get_token_kwargs_namespace_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_refresh_module()
    monkeypatch.setenv("ENDOR_NAMESPACE", "from-env.child")
    kwargs = module.resolve_get_token_kwargs(
        admin=False,
        sso=True,
        namespace="cli-tenant",
        env_file=Path(".env"),
        environment="endorlabs.com",
        timeout=120,
    )
    assert kwargs["auth_tenant"] == "cli-tenant"


def test_resolve_get_token_kwargs_missing_tenant_exits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_refresh_module()
    for key in ("ENDOR_NAMESPACE",):
        monkeypatch.delenv(key, raising=False)
    with pytest.raises(SystemExit, match="Tenant SSO requires"):
        module.resolve_get_token_kwargs(
            admin=False,
            sso=True,
            namespace=None,
            env_file=Path("/nonexistent/.env"),
            environment="endorlabs.com",
            timeout=120,
        )
