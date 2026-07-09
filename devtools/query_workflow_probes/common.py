"""Shared helpers for Query workflow replacement probes."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import endorlabs
from endorlabs.core.exceptions import UnauthorizedError
from endorlabs.query import (
    extract_group_response,
    extract_query_objects,
    next_page_token,
    parse_group_bucket_counts,
    query_create,
    reference_count,
    reference_total,
)
from endorlabs.query.parse import wire_dict

_REFRESH_HINT = (
    "Refresh once (browser): "
    "uv run endor-auth refresh --env-file .env-admin --method sso -n endor-admin"
)


def resolve_tenant(namespace: str) -> str:
    """Return tenant root from a namespace path."""
    return namespace.split(".")[0] if "." in namespace else namespace


def _strip_env(key: str) -> str | None:
    value = os.environ.get(key)
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def require_dotenv_token() -> str:
    """Return ``ENDOR_TOKEN`` from the environment or exit with refresh guidance."""
    token = _strip_env("ENDOR_TOKEN")
    if not token:
        raise SystemExit(f"ENDOR_TOKEN not set. {_REFRESH_HINT}")
    return token


def make_client(namespace: str) -> endorlabs.Client:
    """Open one SDK client using ``ENDOR_TOKEN`` only (no browser OAuth in probes).

    Call once per probe run. Browser auth belongs in ``endor-auth refresh``.
    """
    token = require_dotenv_token()
    for key in ("ENDOR_API_CREDENTIALS_KEY", "ENDOR_API_CREDENTIALS_SECRET"):
        os.environ.pop(key, None)

    tenant = resolve_tenant(namespace)
    client = endorlabs.Client(tenant=tenant, token=token)
    try:
        client.whoami()
    except UnauthorizedError as exc:
        client.close()
        raise SystemExit(
            f"ENDOR_TOKEN rejected by API ({exc}). {_REFRESH_HINT}"
        ) from exc
    return client


def discover_projects(
    client: endorlabs.Client,
    namespace: str,
    *,
    traverse: bool = True,
    max_pages: int | None = 1,
    cap: int = 10,
) -> list[dict[str, Any]]:
    """List masked Project rows for probe samples."""
    kwargs: dict[str, Any] = {
        "namespace": namespace,
        "traverse": traverse,
        "mask": "uuid,meta.name,tenant_meta.namespace",
    }
    if max_pages is not None:
        kwargs["max_pages"] = max_pages
    rows = client.Project.list(**kwargs)
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        item = wire_dict(row)
        uid = str(item.get("uuid") or "")
        if not uid or uid in seen:
            continue
        seen.add(uid)
        out.append(item)
        if len(out) >= cap:
            break
    return out


def project_wire_namespace(project: dict[str, Any]) -> str:
    """Read leaf namespace from a masked Project dict."""
    tm = project.get("tenant_meta") or {}
    if isinstance(tm, dict):
        ns = tm.get("namespace")
        if ns:
            return str(ns)
    raise ValueError(f"project {project.get('uuid')} missing tenant_meta.namespace")


def reference_list_total(project_obj: dict[str, Any], ref_key: str) -> int | None:
    """SDK parity: prefer count ref, then list.response.total."""
    from endorlabs.query import reference_list_total as _sdk_total

    total = _sdk_total(project_obj, ref_key)
    if total is not None:
        return total
    count = reference_count(project_obj, ref_key)
    return count if count else None


@dataclass(frozen=True, slots=True)
class ProbeResult:
    """One probe arm outcome."""

    name: str
    elapsed_s: float
    ok: bool
    detail: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "elapsed_s": round(self.elapsed_s, 3),
            "ok": self.ok,
            "detail": self.detail,
        }


def write_report(path: Path, payload: dict[str, Any]) -> None:
    """Write JSON probe report."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def env_namespace() -> str | None:
    """Read ENDOR_NAMESPACE when set."""
    return _strip_env("ENDOR_NAMESPACE")


__all__ = [
    "ProbeResult",
    "discover_projects",
    "extract_group_response",
    "extract_query_objects",
    "make_client",
    "next_page_token",
    "parse_group_bucket_counts",
    "project_wire_namespace",
    "query_create",
    "reference_count",
    "reference_list_total",
    "reference_total",
    "require_dotenv_token",
    "resolve_tenant",
    "wire_dict",
    "write_report",
]
