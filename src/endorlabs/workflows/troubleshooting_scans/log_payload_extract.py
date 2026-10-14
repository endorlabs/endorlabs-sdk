"""Extract selected toolchain versions and underlying error fields from scan logs.

Wrong grain for triage: status percentages or error-*code* histograms alone.
Right grain: ``toolchains`` on ``Endorctl toolchains selected`` (protobuf-text)
plus full error payload fields (``msg``, ``resolution_error``, ``stderr``,
``command``, ``package_name``, ``caller``).
"""

from __future__ import annotations

import json
import re
from typing import Any, cast

from endorlabs.workflows.wire_access import as_dict, dict_str

CHAIN_TYPES = (
    "golang_tool_chain",
    "python_tool_chain",
    "javascript_tool_chain",
    "java_tool_chain",
    "dotnet_tool_chain",
    "csharp_tool_chain",
    "ruby_tool_chain",
    "php_tool_chain",
    "rust_tool_chain",
    "kotlin_tool_chain",
    "scala_tool_chain",
    "c_tool_chain",
    "android_tool_chain",
    "swift_tool_chain",
)

SUB_VERSION_KEYS = (
    "nodejs_version",
    "yarn_version",
    "pnpm_version",
    "npm_version",
    "maven_version",
    "gradle_version",
    "jdk_version",
)

KNOWN_FAILURE_CODES = frozenset(
    {
        "dependency-scanning-error",
        "dependency-resolution-error",
        "toolchain-error",
        "sandbox-error",
        "scan-cancelled",
        "baseline-not-found",
        "call-graph-error",
        "invalid-args",
        "internal",
    }
)

_ERROR_LEVELS = frozenset(
    {
        "error",
        "warn",
        "warning",
        "fatal",
        "critical",
        "log_level_error",
        "log_level_warning",
        "log_level_critical",
        "log_level_fatal",
    }
)


def _first_line(text: str | None, *, max_len: int = 240) -> str:
    if not text:
        return ""
    line = text.splitlines()[0].strip()
    if len(line) <= max_len:
        return line
    return line[: max_len - 3] + "..."


def _clip(text: str | None, *, max_len: int = 400) -> str:
    if not text:
        return ""
    compact = " ".join(str(text).split())
    if len(compact) <= max_len:
        return compact
    return compact[: max_len - 3] + "..."


def parse_toolchains_blob(blob: str) -> dict[str, str]:
    """Parse endorctl protobuf-text ``toolchains=`` string into name→version."""
    if not blob:
        return {}
    out: dict[str, str] = {}
    for chain in CHAIN_TYPES:
        idx = blob.find(chain)
        if idx < 0:
            continue
        window = blob[idx : idx + 600]
        match = re.search(r"version:\s*\{\s*name:\s*\{\s*value:\s*\"([^\"]+)\"", window)
        if match:
            key = chain.replace("_tool_chain", "")
            out[key] = match.group(1)
        for sub in SUB_VERSION_KEYS:
            sub_match = re.search(
                rf"{sub}:\s*\{{[^}}]*name:\s*\{{\s*value:\s*\"([^\"]+)\"",
                window,
            )
            if sub_match:
                out[sub.replace("_version", "")] = sub_match.group(1)
    for sub in SUB_VERSION_KEYS:
        short = sub.replace("_version", "")
        if short in out:
            continue
        sub_match = re.search(
            rf"{sub}:\s*\{{[^}}]*name:\s*\{{\s*value:\s*\"([^\"]+)\"",
            blob,
        )
        if sub_match:
            out[short] = sub_match.group(1)
    for pkg in ("uv", "poetry", "pdm", "semgrep", "typescript"):
        pkg_match = re.search(
            rf'(?:pip_packages|npm_packages):\{{key:"{pkg}"\s+'
            rf'value:\{{name:\{{value:"([^"]+)"\}}',
            blob,
        )
        if pkg_match:
            out[f"pkg:{pkg}"] = pkg_match.group(1)
    return out


def detect_toolchain_fails(msg: str) -> list[str]:
    """Return detect-fail / unsupported-version tokens from a log message."""
    lower = (msg or "").lower()
    fails: list[str] = []
    mapping = [
        ("python", "no python versions detected"),
        ("nodejs", "no nodejs versions detected"),
        ("nodejs", "no nodejs versions found"),
        ("yarn", "no yarn versions detected"),
        ("pnpm", "no pnpm versions detected"),
        ("java", "no java versions detected"),
        ("java", "no java versions found"),
        ("maven", "no maven versions detected"),
        ("gradle", "no gradle versions detected"),
        ("dotnet", "no dotnet versions detected"),
    ]
    for name, needle in mapping:
        if needle in lower and name not in fails:
            fails.append(name)
    unsupported = re.search(
        r'unable to find "([^"]+)" toolchain version "([^"]+)"',
        msg or "",
        re.IGNORECASE,
    )
    if unsupported:
        fails.append(f"unsupported:{unsupported.group(1)}@{unsupported.group(2)}")
    return fails


def message_payload(message: Any) -> dict[str, Any]:
    """Normalize a log message (dict, model, or JSON line) to a payload dict."""
    if message is None:
        return {}
    if isinstance(message, str):
        text = message.strip()
        if text.startswith("{"):
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError:
                return {"msg": text}
            if isinstance(parsed, dict):
                nested = as_dict(parsed.get("json_payload"))
                if nested:
                    return nested
                return cast("dict[str, Any]", parsed)
        return {"msg": text}

    if hasattr(message, "model_dump"):
        data = as_dict(message.model_dump(mode="python"))
    elif isinstance(message, dict):
        data = cast("dict[str, Any]", message)
    else:
        payload_attr = getattr(message, "json_payload", None)
        if payload_attr is not None:
            return as_dict(payload_attr) or {"msg": str(payload_attr)}
        return {}

    payload = as_dict(data.get("json_payload") or data.get("payload"))
    if payload:
        return payload
    if "msg" in data or "code" in data or "toolchains" in data:
        return data
    return {}


def _message_level(message: Any, payload: dict[str, Any]) -> str:
    if isinstance(message, dict):
        level = dict_str(message, "level")
    else:
        level = str(getattr(message, "level", "") or "")
    payload_level = dict_str(payload, "level")
    return (payload_level or level).lower()


def _message_timestamp(message: Any, payload: dict[str, Any]) -> str:
    if isinstance(message, dict):
        ts = dict_str(message, "timestamp")
    else:
        ts = str(getattr(message, "timestamp", "") or "")
    return ts or dict_str(payload, "timestamp")


def extract_selected_toolchains(
    messages: list[Any] | None,
) -> dict[str, Any]:
    """Extract selected toolchain versions from scan log messages.

    Returns:
        ``versions``, ``raw_blobs`` (bounded), ``source``, ``detect_fails``.
    """
    versions: dict[str, str] = {}
    raw_blobs: list[str] = []
    detect_fails: list[str] = []
    source: str | None = None

    for message in messages or []:
        payload = message_payload(message)
        if not payload:
            continue
        msg = dict_str(payload, "msg") or dict_str(payload, "message")
        toolchains_raw = payload.get("toolchains")
        if toolchains_raw is not None or "toolchains selected" in msg.lower():
            blob = str(toolchains_raw) if toolchains_raw is not None else ""
            if blob:
                raw_blobs.append(_clip(blob, max_len=1200))
                parsed = parse_toolchains_blob(blob)
                versions.update(parsed)
                source = "toolchains_selected_log"
        for fail in detect_toolchain_fails(msg):
            if fail not in detect_fails:
                detect_fails.append(fail)
        err_text = dict_str(payload, "error")
        for fail in detect_toolchain_fails(err_text):
            if fail not in detect_fails:
                detect_fails.append(fail)

    return {
        "versions": versions,
        "raw_blobs": raw_blobs[:3],
        "source": source,
        "detect_fails": detect_fails,
    }


def _error_fingerprint(row: dict[str, str]) -> str:
    return "|".join(
        [
            row.get("code", ""),
            row.get("msg", "")[:160],
            row.get("package_name", ""),
            row.get("command", "")[:160],
        ]
    )


def extract_underlying_errors(
    messages: list[Any] | None,
    *,
    max_errors: int = 50,
) -> list[dict[str, str]]:
    """Extract underlying error rows (not code-only tallies).

    Includes error/warn levels and known failure codes even when level is unset.
    """
    out: list[dict[str, str]] = []
    seen: set[str] = set()

    for message in messages or []:
        payload = message_payload(message)
        if not payload:
            continue
        level = _message_level(message, payload)
        code = dict_str(payload, "code")
        is_level_error = level in _ERROR_LEVELS
        is_known_code = code in KNOWN_FAILURE_CODES
        if not is_level_error and not is_known_code:
            continue

        msg = _clip(
            dict_str(payload, "msg") or dict_str(payload, "message"), max_len=320
        )
        row = {
            "timestamp": _message_timestamp(message, payload),
            "level": level or "",
            "code": code,
            "msg": msg,
            "resolution_error": _first_line(
                dict_str(payload, "resolution_error"), max_len=320
            ),
            "stderr": _first_line(dict_str(payload, "stderr"), max_len=320),
            "command": _clip(dict_str(payload, "command"), max_len=320),
            "package_name": _clip(dict_str(payload, "package_name"), max_len=200),
            "caller": _clip(dict_str(payload, "caller"), max_len=160),
        }
        # Skip empty shells / code-only tallies (no narrative fields).
        if not any(
            row[k]
            for k in (
                "msg",
                "resolution_error",
                "stderr",
                "command",
                "package_name",
            )
        ):
            continue
        fingerprint = _error_fingerprint(row)
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        out.append(row)
        if len(out) >= max_errors:
            break
    return out


def enrich_log_artifact(payload: dict[str, Any]) -> dict[str, Any]:
    """Attach ``selected_toolchains`` and ``underlying_errors`` onto a log artifact."""
    messages_raw = payload.get("messages")
    messages: list[Any] = (
        cast("list[Any]", messages_raw) if isinstance(messages_raw, list) else []
    )
    # Also accept plain text entry lists under common keys
    if not messages:
        for key in ("entries", "log_messages", "lines"):
            alt = payload.get(key)
            if isinstance(alt, list):
                messages = cast("list[Any]", alt)
                break
    payload["selected_toolchains"] = extract_selected_toolchains(messages)
    payload["underlying_errors"] = extract_underlying_errors(messages)
    return payload


def diff_selected_toolchain_versions(
    prev: dict[str, Any] | None,
    new: dict[str, Any] | None,
) -> dict[str, Any]:
    """Diff ``selected_toolchains.versions`` maps (or bare version dicts)."""

    def _versions(block: dict[str, Any] | None) -> dict[str, str]:
        if not block:
            return {}
        nested = as_dict(block.get("versions")) if "versions" in block else None
        if nested:
            return {str(k): str(v) for k, v in nested.items() if v is not None}
        # bare map
        if all(isinstance(v, str) for v in block.values()):
            return {str(k): str(v) for k, v in block.items()}
        return {}

    prev_v = _versions(prev)
    new_v = _versions(new)
    keys = sorted(set(prev_v) | set(new_v))
    changed: dict[str, dict[str, str | None]] = {}
    unchanged: dict[str, str] = {}
    for key in keys:
        a, b = prev_v.get(key), new_v.get(key)
        if a != b:
            changed[key] = {"prev": a, "new": b}
        elif a is not None:
            unchanged[key] = a
    return {
        "changed": changed,
        "unchanged": unchanged,
        "only_prev": {k: prev_v[k] for k in prev_v if k not in new_v},
        "only_new": {k: new_v[k] for k in new_v if k not in prev_v},
        "prev_missing_selected_log": not bool(prev_v)
        and not bool((prev or {}).get("source")),
        "new_missing_selected_log": not bool(new_v)
        and not bool((new or {}).get("source")),
    }


__all__ = [
    "CHAIN_TYPES",
    "KNOWN_FAILURE_CODES",
    "detect_toolchain_fails",
    "diff_selected_toolchain_versions",
    "enrich_log_artifact",
    "extract_selected_toolchains",
    "extract_underlying_errors",
    "message_payload",
    "parse_toolchains_blob",
]
