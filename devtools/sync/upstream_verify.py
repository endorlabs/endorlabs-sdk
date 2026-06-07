"""Committed model-sync provenance vs live OpenAPI + endorctl meta."""

from __future__ import annotations

import hashlib
import json
import logging
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

_PROVENANCE_LINE_PREFIX = "# model_sync_provenance:"
_SEMVER_RE = re.compile(r"\bv?(\d+(?:\.\d+)+)\b")
DEFAULT_API_ORIGIN = "https://api.endorlabs.com"
DEFAULT_META_VERSION_URL = f"{DEFAULT_API_ORIGIN}/meta/version"


def parse_committed_provenance(registry_contract_text: str) -> dict[str, str]:
    """Extract spec_sha256 and endorctl_version from registry_contract.py header."""
    for raw_line in registry_contract_text.splitlines():
        line = raw_line.strip()
        if not line.startswith(_PROVENANCE_LINE_PREFIX):
            continue
        payload = line[len(_PROVENANCE_LINE_PREFIX) :].strip()
        data: dict[str, Any] = json.loads(payload)
        spec_sha256 = data.get("spec_sha256")
        endorctl_version = data.get("endorctl_version")
        if not isinstance(spec_sha256, str) or not spec_sha256:
            raise ValueError("Committed provenance missing spec_sha256")
        if not isinstance(endorctl_version, str):
            endorctl_version = "unknown"
        return {
            "spec_sha256": spec_sha256,
            "endorctl_version": endorctl_version,
        }
    raise ValueError(
        "Could not find model_sync_provenance line in registry contract module"
    )


def load_committed_provenance(registry_contract_path: Path) -> dict[str, str]:
    """Load provenance from the generated registry contract file."""
    text = registry_contract_path.read_text(encoding="utf-8")
    return parse_committed_provenance(text)


def fetch_openapi_sha256(spec_url: str, *, timeout_seconds: float = 120.0) -> str:
    """Download OpenAPI JSON from ``spec_url`` and return SHA-256 hex digest."""
    digest = hashlib.sha256()
    request = urllib.request.Request(  # noqa: S310
        spec_url,
        headers={"User-Agent": "endorlabs-model-sync-verify"},
    )
    with urllib.request.urlopen(  # noqa: S310
        request,
        timeout=timeout_seconds,
    ) as resp:
        while True:
            chunk = resp.read(65536)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def meta_version_url_from_openapi_url(openapi_url: str) -> str:
    """Derive ``/meta/version`` URL from an OpenAPI download URL (same API host)."""
    parsed = urlparse(openapi_url)
    if not parsed.scheme or not parsed.netloc:
        return DEFAULT_META_VERSION_URL
    return f"{parsed.scheme}://{parsed.netloc}/meta/version"


def format_endorctl_version_banner(semver: str) -> str:
    """Build the canonical model-sync ``# endorctl_version`` banner string."""
    cleaned = semver.strip()
    if not cleaned or cleaned.lower() == "unknown":
        return "unknown"
    numeric = cleaned.lstrip("v")
    if not numeric:
        return "unknown"
    return f"endorctl version v{numeric}"


def fetch_latest_endorctl_semver(
    *,
    meta_version_url: str = DEFAULT_META_VERSION_URL,
    timeout_seconds: float = 15.0,
) -> str | None:
    """Return latest endorctl semver string from public ``/meta/version`` (no auth)."""
    request = urllib.request.Request(  # noqa: S310
        meta_version_url,
        headers={"User-Agent": "endorlabs-model-sync"},
    )
    try:
        with urllib.request.urlopen(  # noqa: S310
            request,
            timeout=timeout_seconds,
        ) as resp:
            raw = resp.read()
    except (OSError, urllib.error.URLError) as exc:
        logger.warning("Could not query endorctl meta/version: %s", exc)
        return None
    try:
        data: dict[str, Any] = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError:
        return None
    version = data.get("ClientVersion") or data.get("Version")
    if not isinstance(version, str) or not version:
        return None
    extracted = extract_semver_from_banner(version)
    return extracted


def extract_semver_from_banner(text: str) -> str | None:
    """Pull dotted semver from an endorctl banner or plain ``vX.Y.Z`` string."""
    cleaned = text.strip()
    if cleaned.lower() == "unknown":
        return None
    match = _SEMVER_RE.search(cleaned)
    return match.group(1) if match else None


def _semver_tuple(version: str) -> tuple[int, ...]:
    parts = version.split(".")
    result: list[int] = []
    for part in parts:
        if part.isdigit():
            result.append(int(part))
        else:
            head = "".join(ch for ch in part if ch.isdigit())
            result.append(int(head) if head else 0)
    return tuple(result)


def semver_less(left: str, right: str) -> bool:
    """True if ``left`` sorts strictly before ``right`` (numeric tuple compare)."""
    a = _semver_tuple(left)
    b = _semver_tuple(right)
    maxlen = max(len(a), len(b))
    aa = a + (0,) * (maxlen - len(a))
    bb = b + (0,) * (maxlen - len(b))
    return aa < bb


def verify_upstream_matches_committed(
    *,
    registry_contract_path: Path,
    spec_url: str,
    openapi_timeout_seconds: float = 120.0,
    meta_timeout_seconds: float = 15.0,
) -> list[str]:
    """Return human-readable mismatch reasons; empty list means OK.

    Checks:
    - Live OpenAPI SHA-256 vs committed ``spec_sha256`` (failure when mismatched)
    - Published endorctl from ``meta/version`` vs watermark semver (warning only)
    """
    reasons: list[str] = []
    path = registry_contract_path.expanduser().resolve()
    try:
        committed = load_committed_provenance(path)
    except (OSError, ValueError) as exc:
        return [f"Could not read committed provenance from {path}: {exc}"]

    try:
        live_sha = fetch_openapi_sha256(
            spec_url,
            timeout_seconds=openapi_timeout_seconds,
        )
    except (OSError, urllib.error.URLError) as exc:
        return [f"Could not download OpenAPI spec from {spec_url}: {exc}"]

    if live_sha != committed["spec_sha256"]:
        reasons.append(
            "OpenAPI spec SHA256 differs from committed model-sync provenance "
            f"(upstream {live_sha} vs committed {committed['spec_sha256']}). "
            "Run: uv run python devtools/model_sync.py --fetch-spec "
            "--generate-stubs --generate-reference-docs"
        )

    meta_url = meta_version_url_from_openapi_url(spec_url)
    api_semver = fetch_latest_endorctl_semver(
        meta_version_url=meta_url,
        timeout_seconds=meta_timeout_seconds,
    )
    banner_semver = extract_semver_from_banner(committed["endorctl_version"])
    if api_semver and banner_semver and semver_less(banner_semver, api_semver):
        logger.warning(
            "Published endorctl %s is newer than the committed model-sync watermark "
            "(%s). Re-run model_sync to refresh generated artifacts: "
            "uv run python devtools/model_sync.py --fetch-spec "
            "--generate-stubs --generate-reference-docs",
            api_semver,
            banner_semver,
        )

    return reasons
