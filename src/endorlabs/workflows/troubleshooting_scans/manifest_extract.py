"""Extract discovered manifests from scan logs; select Analytics vs full SCA pairs."""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping, Sequence
from typing import Any, Literal, cast

from endorlabs.workflows.wire_access import dict_str, nested_dict, nested_str

ANALYTICS_TYPES = frozenset({"TYPE_ANALYTICS", "TYPE_ANALYTICS_CHECK"})
FULL_SCA_TYPE = "TYPE_ALL_SCANS"

ManifestKind = Literal[
    "language_walk",
    "analytics_walk",
    "manifest",
    "manifest_count",
    "lockfile",
]

_RE_LANGUAGE_WALK = re.compile(
    r"^Discovering (?P<lang>.+?) dependency files\s*\.\.\.\s*$",
    re.IGNORECASE,
)
_RE_ANALYTICS_PKG = re.compile(r"^Discovering package versions\s*$", re.IGNORECASE)
_RE_ANALYTICS_REPO = re.compile(r"^Discovering repository versions\s*$", re.IGNORECASE)
_RE_PACKAGE_JSON = re.compile(
    r"^Found package\.json file at:\s*(?P<path>.+?)\s*$",
    re.IGNORECASE,
)
_RE_MANIFEST_COUNT = re.compile(
    r"^Found (?P<count>\d+) '(?P<key>[^']+)' manifest files\s*$",
    re.IGNORECASE,
)
_RE_DISCOVERED_MAVEN = re.compile(
    r"^Discovered maven manifests to scan\s*$",
    re.IGNORECASE,
)
_RE_DISCOVERED_GRADLE = re.compile(
    r"^Discovered gradle manifests to scan\s*$",
    re.IGNORECASE,
)
_RE_DISCOVERED_GRADLE_SUB = re.compile(
    r"^Discovered gradle subprojects to scan further\s*$",
    re.IGNORECASE,
)
_RE_LOCKFILE = re.compile(
    r"^Using lock file for '(?P<coord>[^']+)' at path '(?P<path>[^']+)'\s*$",
    re.IGNORECASE,
)
_RE_REQUIREMENTS_PKG = re.compile(
    r"^Found requirements based package for\s+(?P<path>.+?)\s*$",
    re.IGNORECASE,
)
_RE_AUTODETECT_REQ = re.compile(
    r"^Auto-detected requirements file(?P<rest>.*)$",
    re.IGNORECASE,
)
_RE_GETTING_MANIFESTS = re.compile(
    r"^Getting manifest files for\s+(?P<scope>.+)$",
    re.IGNORECASE,
)
_RE_UNABLE_MANIFEST_PATH = re.compile(
    r"Unable to generate manifest path",
    re.IGNORECASE,
)

_MANIFEST_BASENAME = re.compile(
    r"(?P<path>(?:[^\s'\"]+/)*"
    r"(?:package\.json|package-lock\.json|yarn\.lock|pnpm-lock\.yaml|"
    r"npm-shrinkwrap\.json|pom\.xml|build\.gradle(?:\.kts)?|"
    r"settings\.gradle(?:\.kts)?|go\.mod|go\.sum|Cargo\.toml|Cargo\.lock|"
    r"Gemfile(?:\.lock)?|composer\.json|composer\.lock|pyproject\.toml|"
    r"Pipfile(?:\.lock)?|poetry\.lock|requirements[^/\s'\"]*\.txt|"
    r"setup\.py|setup\.cfg|Package\.swift|Package\.resolved|Podfile|"
    r"Podfile\.lock|mix\.exs|mix\.lock|pubspec\.yaml|pubspec\.lock|"
    r"build\.sbt|\.csproj|\.fsproj|\.vbproj|packages\.config|"
    r"Directory\.Packages\.props))"
)

_LANG_ECOSYSTEM: dict[str, str] = {
    "javascript": "javascript",
    "java": "java",
    "go": "go",
    "python": "python",
    "c#": "csharp",
    "csharp": "csharp",
    "githubaction": "githubaction",
    "ruby": "ruby",
    "php": "php",
    "rust": "rust",
    "swift": "swift",
    "kotlin": "kotlin",
    "scala": "scala",
}


def _normalize_lang(raw: str) -> str:
    key = raw.strip().lower()
    return _LANG_ECOSYSTEM.get(key, key)


def _msg_and_level(line: Any) -> tuple[str, str, dict[str, Any]]:  # noqa: C901
    """Return ``(level, msg, extra_fields)`` from a log line or message object."""
    extra: dict[str, Any] = {}
    if isinstance(line, Mapping):
        line_map = cast("Mapping[str, Any]", line)
        level = str(
            line_map.get("level")
            or line_map.get("log_level")
            or line_map.get("Level")
            or "UNKNOWN"
        )
        raw_payload: object = (
            line_map.get("json_payload") or line_map.get("payload") or {}
        )
        if isinstance(raw_payload, Mapping):
            payload_map = cast("Mapping[str, Any]", raw_payload)
            msg = str(payload_map.get("msg") or payload_map.get("message") or "")
            for key in ("poms", "build_file", "files", "path", "file"):
                if key in payload_map:
                    extra[key] = payload_map[key]
        else:
            msg = str(line_map.get("msg") or line_map.get("message") or "")
        if not msg and isinstance(line_map.get("text"), str):
            msg = cast("str", line_map["text"])
        return level, msg.strip(), extra

    if not isinstance(line, str):
        level = str(
            getattr(line, "level", None) or getattr(line, "log_level", "UNKNOWN")
        )
        payload = getattr(line, "json_payload", None)
        if isinstance(payload, Mapping):
            payload_map = cast("Mapping[str, Any]", payload)
            msg = str(payload_map.get("msg") or payload_map.get("message") or "")
            for key in ("poms", "build_file", "files", "path", "file"):
                if key in payload_map:
                    extra[key] = payload_map[key]
            return level, msg.strip(), extra
        msg = str(getattr(line, "message", None) or getattr(line, "msg", None) or "")
        return level, msg.strip(), extra

    stripped = line.strip()
    if stripped.startswith("{"):
        try:
            payload_obj = json.loads(stripped)
        except json.JSONDecodeError:
            return "UNKNOWN", stripped, extra
        if isinstance(payload_obj, dict):
            return _msg_and_level(payload_obj)

    if "]" in stripped and "[" in stripped:
        left, right = stripped.rsplit("]", 1)
        level = left.rsplit("[", 1)[-1]
        return level, right.strip(), extra
    return "UNKNOWN", stripped, extra


def _paths_from_extra(extra: Mapping[str, Any]) -> list[str]:
    out: list[str] = []
    for key in ("poms", "files"):
        raw = extra.get(key)
        if isinstance(raw, list):
            for item in cast("list[Any]", raw):
                text = str(item).strip()
                if text:
                    out.append(text)
    for key in ("build_file", "path", "file"):
        raw = extra.get(key)
        if isinstance(raw, str) and raw.strip():
            out.append(raw.strip())
    return out


def _entry(
    *,
    kind: ManifestKind,
    ecosystem: str | None,
    path: str | None,
    level: str,
    msg: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "kind": kind,
        "ecosystem": ecosystem,
        "path": path,
        "level": level,
        "msg": msg,
    }
    if extra:
        row["extra"] = extra
    return row


def extract_discovered_manifests(  # noqa: C901
    log_lines: Sequence[Any] | Iterable[Any],
) -> dict[str, Any]:
    """Parse endorctl discovery / lockfile messages into structured hits.

    Portable across ecosystems: language walks are INFO; path-bearing lines are
    often DEBUG. Returns unique path list plus ordered hit rows.
    """
    hits: list[dict[str, Any]] = []
    paths: list[str] = []
    seen_paths: set[str] = set()
    languages: list[str] = []
    seen_langs: set[str] = set()
    analytics_walks = 0

    def _add_path(path: str | None) -> None:
        if not path:
            return
        cleaned = path.strip().strip("'\"")
        if not cleaned or cleaned in seen_paths:
            return
        seen_paths.add(cleaned)
        paths.append(cleaned)

    for line in log_lines:
        level, msg, extra = _msg_and_level(line)
        if not msg:
            continue

        if m := _RE_LANGUAGE_WALK.match(msg):
            lang = _normalize_lang(m.group("lang"))
            if lang not in seen_langs:
                seen_langs.add(lang)
                languages.append(lang)
            hits.append(
                _entry(
                    kind="language_walk",
                    ecosystem=lang,
                    path=None,
                    level=level,
                    msg=msg,
                )
            )
            continue

        if _RE_ANALYTICS_PKG.match(msg) or _RE_ANALYTICS_REPO.match(msg):
            analytics_walks += 1
            hits.append(
                _entry(
                    kind="analytics_walk",
                    ecosystem=None,
                    path=None,
                    level=level,
                    msg=msg,
                )
            )
            continue

        if m := _RE_PACKAGE_JSON.match(msg):
            path = m.group("path").strip()
            _add_path(path)
            hits.append(
                _entry(
                    kind="manifest",
                    ecosystem="javascript",
                    path=path,
                    level=level,
                    msg=msg,
                )
            )
            continue

        if m := _RE_MANIFEST_COUNT.match(msg):
            key = m.group("key").strip().lower()
            eco = "java" if key in {"maven", "gradle", "pom", "pom.xml"} else key
            hits.append(
                _entry(
                    kind="manifest_count",
                    ecosystem=eco,
                    path=None,
                    level=level,
                    msg=msg,
                    extra={"count": int(m.group("count")), "key": m.group("key")},
                )
            )
            for path in _paths_from_extra(extra):
                _add_path(path)
            continue

        if _RE_DISCOVERED_MAVEN.match(msg):
            found = _paths_from_extra(extra)
            for path in found:
                _add_path(path)
                hits.append(
                    _entry(
                        kind="manifest",
                        ecosystem="maven",
                        path=path,
                        level=level,
                        msg=msg,
                    )
                )
            if not found:
                hits.append(
                    _entry(
                        kind="manifest",
                        ecosystem="maven",
                        path=None,
                        level=level,
                        msg=msg,
                    )
                )
            continue

        if _RE_DISCOVERED_GRADLE.match(msg) or _RE_DISCOVERED_GRADLE_SUB.match(msg):
            found = _paths_from_extra(extra)
            for path in found:
                _add_path(path)
                hits.append(
                    _entry(
                        kind="manifest",
                        ecosystem="gradle",
                        path=path,
                        level=level,
                        msg=msg,
                    )
                )
            if not found:
                hits.append(
                    _entry(
                        kind="manifest",
                        ecosystem="gradle",
                        path=None,
                        level=level,
                        msg=msg,
                    )
                )
            continue

        if m := _RE_LOCKFILE.match(msg):
            path = m.group("path").strip()
            coord = m.group("coord").strip()
            eco = coord.split("://", 1)[0] if "://" in coord else None
            _add_path(path)
            hits.append(
                _entry(
                    kind="lockfile",
                    ecosystem=eco,
                    path=path,
                    level=level,
                    msg=msg,
                    extra={"coordinate": coord},
                )
            )
            continue

        if m := _RE_REQUIREMENTS_PKG.match(msg):
            path = m.group("path").strip()
            _add_path(path)
            hits.append(
                _entry(
                    kind="manifest",
                    ecosystem="python",
                    path=path,
                    level=level,
                    msg=msg,
                )
            )
            continue

        if m := _RE_AUTODETECT_REQ.match(msg):
            found = _paths_from_extra(extra)
            for path in found:
                _add_path(path)
            for pm in _MANIFEST_BASENAME.finditer(msg):
                _add_path(pm.group("path"))
            hits.append(
                _entry(
                    kind="manifest",
                    ecosystem="python",
                    path=found[0] if found else None,
                    level=level,
                    msg=msg,
                    extra={"autodetect": m.group("rest").strip()},
                )
            )
            continue

        if m := _RE_GETTING_MANIFESTS.match(msg):
            hits.append(
                _entry(
                    kind="language_walk",
                    ecosystem=_normalize_lang(m.group("scope").split("/", 1)[0]),
                    path=None,
                    level=level,
                    msg=msg,
                )
            )
            continue

        if _RE_UNABLE_MANIFEST_PATH.search(msg):
            hits.append(
                _entry(
                    kind="manifest",
                    ecosystem=None,
                    path=None,
                    level=level,
                    msg=msg,
                    extra={"error": "unable_to_generate_manifest_path"},
                )
            )
            continue

        for pm in _MANIFEST_BASENAME.finditer(msg):
            path = pm.group("path")
            if path in seen_paths:
                continue
            _add_path(path)
            hits.append(
                _entry(
                    kind="manifest",
                    ecosystem=None,
                    path=path,
                    level=level,
                    msg=msg,
                    extra={"opportunistic": True},
                )
            )

    return {
        "hit_count": len(hits),
        "path_count": len(paths),
        "paths": paths,
        "languages": languages,
        "analytics_walk_count": analytics_walks,
        "hits": hits,
    }


def _scan_type(scan: Mapping[str, Any]) -> str:
    spec = scan.get("spec")
    if isinstance(spec, Mapping):
        return str(cast("Mapping[str, Any]", spec).get("type") or "")
    return str(scan.get("type") or "")


def _create_time(scan: Mapping[str, Any]) -> str:
    meta = scan.get("meta")
    if isinstance(meta, Mapping):
        return str(cast("Mapping[str, Any]", meta).get("create_time") or "")
    return str(scan.get("create_time") or "")


def select_latest_scan_pair_by_type(
    scans: Sequence[Mapping[str, Any] | dict[str, Any]],
) -> dict[str, Any]:
    """Pick latest Analytics and latest full SCA (``TYPE_ALL_SCANS``) rows.

    Cite Analytics first when both exist (``citation_priority``). Full SCA falls
    back to the newest non-analytics type when no ``TYPE_ALL_SCANS`` row exists.
    """
    rows: list[dict[str, Any]] = [dict(s) for s in scans]
    ordered = sorted(rows, key=_create_time, reverse=True)

    analytics: dict[str, Any] | None = None
    full_sca: dict[str, Any] | None = None
    fallback_non_analytics: dict[str, Any] | None = None

    for row in ordered:
        stype = _scan_type(row)
        if stype in ANALYTICS_TYPES and analytics is None:
            analytics = row
        elif stype == FULL_SCA_TYPE and full_sca is None:
            full_sca = row
        elif (
            stype
            and stype not in ANALYTICS_TYPES
            and fallback_non_analytics is None
            and full_sca is None
        ):
            fallback_non_analytics = row
        if analytics is not None and full_sca is not None:
            break

    if full_sca is None and fallback_non_analytics is not None:
        full_sca = fallback_non_analytics

    citation_priority: list[str] = []
    if analytics is not None:
        citation_priority.append("analytics")
    if full_sca is not None:
        citation_priority.append("full_sca")

    return {
        "analytics": analytics,
        "full_sca": full_sca,
        "citation_priority": citation_priority,
        "analytics_uuid": analytics.get("uuid") if analytics else None,
        "full_sca_uuid": full_sca.get("uuid") if full_sca else None,
        "analytics_type": _scan_type(analytics) if analytics else None,
        "full_sca_type": _scan_type(full_sca) if full_sca else None,
    }


def extract_project_profile_refs(project: Mapping[str, Any] | Any) -> dict[str, Any]:
    """Allowlisted Project scan/toolchain profile UUID fields (nullable)."""
    if hasattr(project, "model_dump"):
        project = cast("dict[str, Any]", project.model_dump(mode="json"))
    if not isinstance(project, Mapping):
        return {
            "scan_profile_uuid": None,
            "toolchain_profile_uuid": None,
            "project_uuid": None,
            "namespace": None,
        }
    proj = cast("Mapping[str, Any]", project)
    spec = nested_dict(dict(proj), "spec")
    return {
        "project_uuid": proj.get("uuid"),
        "namespace": nested_str(dict(proj), "tenant_meta", "namespace") or None,
        "scan_profile_uuid": dict_str(spec, "scan_profile_uuid") or None,
        "toolchain_profile_uuid": dict_str(spec, "toolchain_profile_uuid") or None,
    }


def app_scan_history_url(*, namespace: str, scan_result_uuid: str) -> str:
    """Structured Endor app scan-history URL."""
    return f"https://app.endorlabs.com/t/{namespace}/scan-history/{scan_result_uuid}"


def app_project_url(*, namespace: str, project_uuid: str) -> str:
    """Structured Endor app project URL."""
    return f"https://app.endorlabs.com/t/{namespace}/projects/{project_uuid}"


__all__ = [
    "ANALYTICS_TYPES",
    "FULL_SCA_TYPE",
    "app_project_url",
    "app_scan_history_url",
    "extract_discovered_manifests",
    "extract_project_profile_refs",
    "select_latest_scan_pair_by_type",
]
