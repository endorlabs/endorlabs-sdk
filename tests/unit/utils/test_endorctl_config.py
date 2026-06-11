"""Tests for endorctl config namespace resolution."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pytest

from endorlabs.utils.endorctl_config import (
    endorctl_config_path,
    read_endorctl_namespace,
    resolve_client_default_namespace,
)


def test_endorctl_config_path_default_uses_home(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("ENDOR_CONFIG_PATH", raising=False)
    monkeypatch.setattr("endorlabs.utils.endorctl_config.Path.home", lambda: tmp_path)
    assert endorctl_config_path() == tmp_path / ".endorctl" / "config.yaml"


def test_endorctl_config_path_honors_endor_config_path(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    custom = tmp_path / "custom-config.yaml"
    monkeypatch.setenv("ENDOR_CONFIG_PATH", str(custom))
    assert endorctl_config_path() == custom


def test_read_endorctl_namespace_from_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config_dir = tmp_path / ".endorctl"
    config_dir.mkdir()
    config_file = config_dir / "config.yaml"
    config_file.write_text("ENDOR_NAMESPACE: config.tenant\n", encoding="utf-8")
    monkeypatch.setattr("endorlabs.utils.endorctl_config.Path.home", lambda: tmp_path)
    assert read_endorctl_namespace() == "config.tenant"


def test_read_endorctl_namespace_missing_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr("endorlabs.utils.endorctl_config.Path.home", lambda: tmp_path)
    assert read_endorctl_namespace() is None


def test_resolve_client_default_namespace_precedence(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config_dir = tmp_path / ".endorctl"
    config_dir.mkdir()
    (config_dir / "config.yaml").write_text(
        "ENDOR_NAMESPACE: config.tenant\n", encoding="utf-8"
    )
    monkeypatch.setattr("endorlabs.utils.endorctl_config.Path.home", lambda: tmp_path)
    monkeypatch.delenv("ENDOR_NAMESPACE", raising=False)

    assert resolve_client_default_namespace("explicit.tenant") == (
        "explicit.tenant",
        "tenant",
    )

    monkeypatch.setenv("ENDOR_NAMESPACE", "env.tenant")
    assert resolve_client_default_namespace(None) == ("env.tenant", "env")

    monkeypatch.delenv("ENDOR_NAMESPACE", raising=False)
    assert resolve_client_default_namespace(None) == (
        "config.tenant",
        "endorctl_config",
    )

    (config_dir / "config.yaml").write_text("other: value\n", encoding="utf-8")
    assert resolve_client_default_namespace(None) == (None, None)
