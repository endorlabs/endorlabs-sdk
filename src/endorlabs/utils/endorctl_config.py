"""Read namespace defaults from the endorctl CLI config file."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

import yaml

from .logging_config import get_resource_logger

_logger = get_resource_logger(__name__)

NamespaceSource = Literal["tenant", "env", "endorctl_config"]


def endorctl_config_path() -> Path:
    """Return the endorctl config file path.

    Uses ``ENDOR_CONFIG_PATH`` when set; otherwise ``~/.endorctl/config.yaml``.
    """
    override = os.environ.get("ENDOR_CONFIG_PATH", "").strip()
    if override:
        return Path(override)
    return Path.home() / ".endorctl" / "config.yaml"


def read_endorctl_namespace() -> str | None:
    """Return ``ENDOR_NAMESPACE`` from the endorctl config file, if present."""
    path = endorctl_config_path()
    try:
        if not path.is_file():
            return None
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        _logger.debug("Could not read endorctl config at %s: %s", path, exc)
        return None
    if not isinstance(raw, dict):
        return None
    value = raw.get("ENDOR_NAMESPACE")
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def resolve_client_default_namespace(
    tenant: str | None,
) -> tuple[str | None, NamespaceSource | None]:
    """Resolve Client default namespace with endorctl-aligned precedence."""
    if tenant:
        return tenant, "tenant"
    env_ns = os.environ.get("ENDOR_NAMESPACE", "").strip()
    if env_ns:
        return env_ns, "env"
    config_ns = read_endorctl_namespace()
    if config_ns:
        return config_ns, "endorctl_config"
    return None, None
