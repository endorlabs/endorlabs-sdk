"""Endor Labs SDK demo CLI.

This module intentionally focuses on a readable, single-file walkthrough that
shows both:
- SDK syntax patterns (`list`, `lookup`, `filter`, `mask`, `update`)
- Practical demo logic for discovery, findings, scan logs, and call graphs

Run with:
    uv run endor-demo
    uv run endor-demo --verbose
"""

from __future__ import annotations

import argparse
import contextlib
import logging
import os
import re
import shutil
import time
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, cast

import endorlabs
from endorlabs import F
from endorlabs.exceptions import PermissionDeniedError
from endorlabs.utils.logging_config import get_resource_logger

logger = get_resource_logger(__name__)
UUID_PATTERN = re.compile(r"^[0-9a-f]{24}$", re.IGNORECASE)

# Rich console is optional; plain print fallback keeps the demo lightweight.
_console: Any = None


def _get_console() -> Any:
    """Return a shared ``rich.console.Console``, or ``None``."""
    global _console
    if _console is not None:
        return _console
    try:
        from rich.console import Console

        _console = Console(highlight=False)
    except ImportError:
        pass
    return _console


def _log(msg: str, *, style: str = "") -> None:
    """Print a message, using Rich when available."""
    con = _get_console()
    if con and style:
        con.print(msg, style=style)
    elif con:
        con.print(msg)
    else:
        print(msg)


def _load_dotenv() -> None:
    """Load local ``.env`` file into process environment if present."""
    env_file = Path(".env")
    if not env_file.exists():
        return
    with open(env_file, encoding="utf-8") as fh:
        for raw_line in fh:
            stripped = raw_line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            key = key.strip()
            value = value.strip()
            if (value.startswith('"') and value.endswith('"')) or (
                value.startswith("'") and value.endswith("'")
            ):
                value = value[1:-1]
            if key and not os.getenv(key):
                os.environ[key] = value


def _resolve_logging_level(*, verbose: bool) -> str:
    """Resolve logging level from CLI verbosity and env fallback."""
    if verbose:
        return "DEBUG"
    configured = os.getenv("ENDOR_LOG_LEVEL", "").strip().upper()
    supported = {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"}
    if configured in supported:
        return configured
    return "ERROR"


def _configure_logging(level_name: str) -> None:
    """Configure logging for both demo flow and SDK internals."""
    level = getattr(logging, level_name, logging.ERROR)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-8s %(message)s",
        datefmt="%H:%M:%S",
        force=True,
    )
    logger.debug("Logging configured at %s", level_name)


def _print_banner(tenant: str, user: str) -> None:
    """Print terminal banner with tenant/user context."""
    con = _get_console()
    if con:
        try:
            from rich.panel import Panel
            from rich.text import Text

            body = Text()
            _ = body.append("Endor Labs SDK Demo\n", style="bold")
            _ = body.append(f"Tenant: {tenant}\n", style="dim")
            _ = body.append(f"User:   {user}", style="dim")
            con.print(Panel(body, expand=False, border_style="cyan"))
            return
        except ImportError:
            pass

    width = min(shutil.get_terminal_size().columns, 60)
    border = "=" * width
    print(f"\n{border}")
    print("  Endor Labs SDK Demo")
    print(f"  Tenant: {tenant}")
    print(f"  User:   {user}")
    print(f"{border}\n")


def _build_client(
    tenant: str,
    auth_method: str,
    *,
    logging_level: str,
    email: str | None = None,
    auth_tenant: str | None = None,
) -> endorlabs.Client:
    """Create an authenticated SDK client for the wizard flow."""
    return endorlabs.Client(
        tenant=tenant,
        logging_level=logging_level,
        auth_method=auth_method,
        email=email,
        auth_tenant=auth_tenant,
    )


def _normalize_wizard_auth_method(raw: str, *, default: str) -> str:
    """Normalize wizard auth input to SDK-supported values."""
    cleaned = raw.strip().lower()
    value = cleaned or default
    aliases = {
        "browser": "browser-auth",
        "admin": "browser-auth",
    }
    normalized = aliases.get(value, value)
    supported = {
        "api-key",
        "browser-auth",
        "sso",
        "google",
        "github",
        "gitlab",
        "email",
    }
    if normalized in supported:
        return normalized
    _log(
        f"  Unsupported auth mode '{value}'. Falling back to '{default}'.",
        style="yellow",
    )
    return default


def _prompt_input(prompt: str, *, default: str | None = None) -> str:
    """Prompt for input and optionally apply a default value."""
    raw = input(prompt).strip()
    if raw:
        return raw
    return default or ""


def _prompt_yes_no(prompt: str, *, default_yes: bool = True) -> bool:
    """Prompt for yes/no with Enter honoring the default."""
    default_value = "y" if default_yes else "n"
    raw = _prompt_input(prompt, default=default_value).strip().lower()
    if raw in {"y", "yes"}:
        return True
    if raw in {"n", "no"}:
        return False
    return default_yes


@dataclass(frozen=True)
class ProjectTargetChoice:
    """User's project targeting selection for optional demo steps."""

    action: str
    uuid: str | None = None


def _parse_project_target_choice(raw: str) -> ProjectTargetChoice:
    """Parse ``y/n/<uuid>`` input into a normalized project action."""
    value = raw.strip()
    lower = value.lower()
    if lower in {"", "y", "yes"}:
        return ProjectTargetChoice(action="search")
    if lower in {"n", "no", "skip"}:
        return ProjectTargetChoice(action="skip")
    if UUID_PATTERN.fullmatch(value):
        return ProjectTargetChoice(action="uuid", uuid=value.lower())
    return ProjectTargetChoice(action="invalid")


def _resolve_project_by_uuid(client: endorlabs.Client, project_uuid: str) -> Any | None:
    """Resolve a project UUID across namespaces using traverse search."""
    projects = client.project.list(
        filter=F("uuid") == project_uuid,
        traverse=True,
        max_pages=3,
        page_size=100,
    )
    return projects[0] if projects else None


def _project_name(project: Any) -> str:
    """Return a display-safe project name."""
    if project.meta and project.meta.name:
        return project.meta.name
    return str(project.uuid)


def _project_namespace(project: Any) -> str:
    """Return a display-safe project namespace."""
    if project.tenant_meta and project.tenant_meta.namespace:
        return project.tenant_meta.namespace
    return "unknown-namespace"


def _project_matches_identifier(project: Any, identifier: str) -> bool:
    """Return ``True`` when identifier matches project UUID or name fragment."""
    needle = identifier.strip().lower()
    if not needle:
        return False
    uuid = str(getattr(project, "uuid", "")).lower()
    name = _project_name(project).lower()
    return needle in (uuid, name) or needle in uuid or needle in name


def _select_auto_project_candidate(eligible: list[Any], query: str) -> Any:
    """Select project candidate automatically from eligible results."""
    if query:
        query_matches = [
            project
            for project in eligible
            if _project_matches_identifier(project, query)
        ]
        if query_matches:
            return query_matches[0]
    return eligible[0]


def _print_main_style_section(section_num: str, title: str) -> None:
    """Print section output in the legacy walkthrough style."""
    border = "=" * 60
    _log(f"\n{border}")
    _log(f" [{section_num}] {title}")
    _log(border)


def _summarize_findings(findings: list[Any]) -> tuple[Counter[str], Counter[str]]:
    """Return category and tag counters from a finding sample."""
    category_counts: Counter[str] = Counter()
    tag_counts: Counter[str] = Counter()
    for finding in findings:
        spec = getattr(finding, "spec", None)
        categories = cast("list[Any]", getattr(spec, "finding_categories", None) or [])
        tags = cast("list[Any]", getattr(spec, "finding_tags", None) or [])
        for category in categories:
            category_value = getattr(category, "value", category)
            category_counts[str(category_value)] += 1
        for tag in tags:
            tag_counts[str(tag)] += 1
    return category_counts, tag_counts


def _project_has_scan_results(client: endorlabs.Client, project: Any) -> bool:
    """Return ``True`` when project has at least one scan result."""
    try:
        scans = client.scan_result.list(parent=project, max_pages=1, page_size=1)
    except Exception:
        return False
    return bool(scans)


def _project_has_call_graph(client: endorlabs.Client, project: Any) -> bool:
    """Return ``True`` when project has at least one call graph package version."""
    namespace = _project_namespace(project)
    try:
        pvs = client.package_version.list(
            namespace=namespace,
            filter=(
                f'spec.project_uuid=="{project.uuid}"'
                " AND spec.call_graph_available==true"
            ),
            max_pages=1,
            page_size=1,
        )
    except Exception:
        return False
    return bool(pvs)


def _choose_project_from_search(
    client: endorlabs.Client,
    namespace: str,
    *,
    capability_label: str,
    capability_check: Any,
) -> Any | None:
    """Search projects and return a selected capability-eligible project."""
    query = _prompt_input(
        "Project search text (repo/name; blank lists first results): ",
        default="",
    ).lower()
    projects = client.project.list(
        namespace=namespace,
        traverse=True,
        max_pages=5,
        page_size=100,
    )
    filtered: list[Any] = []
    for project in projects:
        name = project.meta.name if project.meta and project.meta.name else ""
        if not query or query in name.lower():
            filtered.append(project)
    if not filtered:
        _log("  No projects matched in this namespace.", style="yellow")
        return None

    _log(f"  Checking projects that support {capability_label}...", style="dim")
    eligible: list[Any] = []
    for project in filtered[:40]:
        if capability_check(client, project):
            eligible.append(project)
        if len(eligible) >= 15:
            break

    if not eligible:
        _log(
            f"  No projects in this scope currently support {capability_label}.",
            style="yellow",
        )
        return None

    _log(f"  Eligible projects for {capability_label}:")
    for project in eligible:
        _log(
            f"    - {_project_name(project)} "
            f"({project.uuid}) [{_project_namespace(project)}]"
        )

    selected = _select_auto_project_candidate(eligible, query)
    _log(
        "  Auto-selected project: "
        f"{_project_name(selected)} ({selected.uuid}) [{_project_namespace(selected)}]",
        style="green",
    )
    return selected


class TenantCatalog:
    """Eagerly-loaded tenant-wide index of projects and namespaces."""

    def __init__(self) -> None:
        super().__init__()
        self.projects: list[Any] = []
        self.namespaces: list[Any] = []
        self.project_index: dict[str, Any] = {}
        self.projects_by_uuid: dict[str, Any] = {}
        self.projects_by_name: dict[str, list[Any]] = {}

    def load(self, client: endorlabs.Client) -> None:
        """Pull all projects and namespaces using traverse mode."""
        self.projects = client.project.list(traverse=True, max_pages=50, page_size=100)
        self.namespaces = client.namespace.list(traverse=True)
        self.project_index.clear()
        self.projects_by_uuid.clear()
        self.projects_by_name.clear()

        for project in self.projects:
            project_uuid = str(getattr(project, "uuid", "")).strip()
            if project_uuid:
                self.projects_by_uuid[project_uuid] = project

            name = project.meta.name if project.meta else project_uuid
            self.projects_by_name.setdefault(name, []).append(project)

        for name, projects in self.projects_by_name.items():
            if len(projects) == 1:
                self.project_index[name] = projects[0]
                continue
            for project in projects:
                namespace = (
                    project.tenant_meta.namespace
                    if project.tenant_meta and project.tenant_meta.namespace
                    else "unknown-namespace"
                )
                self.project_index[f"{name} [{namespace}]"] = project

    @property
    def summary(self) -> str:
        """Human-readable one-line tenant summary."""
        ns_count = len(self.namespaces)
        proj_count = len(self.project_index)
        return f"{proj_count} projects across {ns_count} namespaces"

    def fuzzy_match(self, query: str) -> list[Any]:
        """Return projects whose name contains *query* (case-insensitive)."""
        q = query.lower()
        return [p for name, p in self.project_index.items() if q in name.lower()]

    def resolve_identifier(self, identifier: str) -> Any | None:
        """Resolve a project from UUID, exact name, or display key."""
        if identifier in self.projects_by_uuid:
            return self.projects_by_uuid[identifier]
        if identifier in self.project_index:
            return self.project_index[identifier]
        by_name = self.projects_by_name.get(identifier)
        if by_name and len(by_name) == 1:
            return by_name[0]
        return None


def _wizard_discovery(client: endorlabs.Client) -> None:
    """Show lightweight namespace/project discovery summary."""
    namespaces = client.namespace.list(traverse=True)
    projects = client.project.list(max_pages=1, page_size=25)
    _log(f"  Namespaces discovered: {len(namespaces)}", style="green")
    _log(f"  Projects on first page: {len(projects)}", style="green")


def _find_anchor_project(client: endorlabs.Client, namespace: str) -> Any | None:
    """Pick a stable project anchor for walkthrough sections."""
    projects = client.project.list(
        namespace=namespace,
        traverse=True,
        max_pages=3,
        page_size=100,
    )
    if not projects:
        return None
    for project in projects:
        name = _project_name(project).lower()
        if "github.com" in name:
            return project
    return projects[0]


def _run_showcase_sections(client: endorlabs.Client, namespace: str) -> None:
    """Run a namespace-agnostic walkthrough of core SDK capabilities."""
    anchor = _find_anchor_project(client, namespace)

    def _run_section(section_num: str, title: str, func: Any) -> None:
        _print_main_style_section(section_num, title)
        try:
            func()
        except Exception as exc:
            _log(f"  ERROR: {exc}")
            _log("  (continuing to next section)", style="dim")

    def _section_1() -> None:
        namespaces = client.namespace.list(traverse=True)
        _log(f"  Namespaces found: {len(namespaces)}")
        for ns in namespaces[:5]:
            full = ns.spec.full_name if ns.spec else ns.meta.name
            _log(f"    - {full}")
        projects = client.project.list(namespace=namespace, max_pages=1, page_size=25)
        _log(f"  Projects (first page): {len(projects)}")
        for proj in projects[:3]:
            _log(f"    - {_project_name(proj)}")

    def _section_2() -> None:
        if anchor is None:
            _log("  No project found for lookup demo.")
            return
        looked_up = client.project.lookup(name=_project_name(anchor), traverse=True)
        _log(f"  Found project: {_project_name(looked_up)}")
        _log(f"  UUID:          {looked_up.uuid}")

    def _section_3() -> None:
        critical = client.finding.list(
            filter=F("spec.level") == "FINDING_LEVEL_CRITICAL",
            traverse=True,
            max_pages=1,
        )
        _log(f"  Critical findings (first page): {len(critical)}")
        high_reachable = client.finding.list(
            filter=(
                F("spec.level").is_in("FINDING_LEVEL_CRITICAL", "FINDING_LEVEL_HIGH")
                & F("spec.finding_tags").contains("FINDING_TAGS_REACHABLE_FUNCTION")
            ),
            traverse=True,
            max_pages=1,
        )
        _log(f"  High+ reachable findings: {len(high_reachable)}")

    def _section_4() -> None:
        if anchor is None:
            _log("  No project found for cross-resource join demo.")
            return
        findings = client.finding.list(
            filter=(F("spec.project_uuid") == anchor.uuid),
            max_pages=1,
        )
        _log(f"  Findings for project: {len(findings)}")
        scans = client.scan_result.list(parent=anchor, max_pages=1, page_size=1)
        _log(f"  Scan results for project: {len(scans)}")
        if scans:
            _log(f"    Latest scan UUID: {scans[0].uuid}")

    def _section_5() -> None:
        count = 0
        for finding in client.finding.list_iter(traverse=True, max_pages=1):
            count += 1
            if count <= 3:
                _log(f"    - [{finding.spec.level}] {finding.spec.summary}")
        _log(f"  Streamed {count} findings (list_iter, 1 page)")

    def _section_6() -> None:
        if anchor is None:
            _log("  No project found for serialization demo.")
            return
        json_str = anchor.model_dump_json(indent=2)
        _log(f"  JSON preview ({len(json_str)} chars total):")
        _log(f"    {json_str[:250]}...")
        compact = anchor.model_dump(exclude_none=True)
        _log(f"  Dict keys (exclude_none): {list(compact.keys())}")

    def _section_7() -> None:
        try:
            _ = client.project.lookup(name="nonexistent-repo-that-does-not-exist")
        except Exception as exc:
            _log(f"  Caught expected lookup error: {type(exc).__name__}")
        try:
            _ = client.project.list(filter='meta.name matches "["')
        except Exception as exc:
            _log(f"  Caught expected validation error: {type(exc).__name__}")

    def _section_8() -> None:
        projects = client.project.list(
            namespace=namespace,
            mask="meta.name,uuid",
            max_pages=1,
            page_size=25,
        )
        _log(f"  Masked projects (first page): {len(projects)}")
        for proj in projects[:3]:
            _log(f"    - {_project_name(proj)} ({proj.uuid})")

    def _section_9() -> None:
        if anchor is None:
            _log("  No project found for workflow demo.")
            return
        findings = client.finding.list(
            filter=(F("spec.project_uuid") == anchor.uuid),
            max_pages=2,
            page_size=100,
        )
        scope_label = f"project {_project_name(anchor)}"
        if not findings:
            findings = client.finding.list(traverse=True, max_pages=1, page_size=100)
            scope_label = "tenant sample"

        if not findings:
            _log("  No findings available to summarize in this tenant scope.")
            return

        category_counts, tag_counts = _summarize_findings(findings)

        _log(f"  Findings sampled: {len(findings)} ({scope_label})")
        if category_counts:
            top_categories = ", ".join(
                f"{name} ({count})" for name, count in category_counts.most_common(5)
            )
            _log(f"  Top categories: {top_categories}")
        else:
            _log("  Top categories: none observed in sample")

        if tag_counts:
            top_tags = ", ".join(
                f"{name} ({count})" for name, count in tag_counts.most_common(5)
            )
            _log(f"  Top tags: {top_tags}")
        else:
            _log("  Top tags: none observed in sample")

        _log("  Automation use: feed these distributions into triage policies.")

    _run_section("1", "Discovery -- Namespaces & Projects", _section_1)
    _run_section("2", "Lookup by Identity Kwargs", _section_2)
    _run_section("3", "F() Filter Builder", _section_3)
    _run_section("4", "Cross-Resource Join", _section_4)
    _run_section("5", "Streaming Iteration", _section_5)
    _run_section("6", "Pydantic Model Serialization", _section_6)
    _run_section("7", "Error Handling", _section_7)
    _run_section("8", "Field Masking", _section_8)
    _run_section("9", "Workflow: Tags and Category Summary", _section_9)


def _stream_scan_logs_for_project(
    client: endorlabs.Client,
    project: Any,
    *,
    trigger_scan: bool,
) -> None:
    """Stream recent scan logs for a selected project."""
    namespace = _project_namespace(project)
    if namespace == "unknown-namespace":
        _log("  Could not resolve project namespace for scan logs.", style="yellow")
        return

    logger.debug(
        "scan_log_flow start namespace=%s project_uuid=%s project_name=%s",
        namespace,
        project.uuid,
        _project_name(project),
    )
    ns_client = endorlabs.Client(
        api_client=client._client,  # noqa: SLF001
        tenant=namespace,
        logging_level=getattr(client._client, "logging_level", "ERROR"),  # noqa: SLF001
    )
    if trigger_scan:
        _log("  Triggering full rescan...", style="dim")
        logger.debug(
            "scan_trigger update namespace=%s project_uuid=%s",
            namespace,
            project.uuid,
        )
        try:
            _ = ns_client.project.update(
                project,
                scan_state="SCAN_STATE_REQUEST_FULL_RESCAN",
            )
            time.sleep(3)
        except PermissionDeniedError as exc:
            logger.debug("scan_trigger denied: %s", exc, exc_info=True)
            _log(
                "  Scan trigger denied (403). You can still inspect existing scan logs "
                "for this project; verify role scope in this namespace.",
                style="yellow",
            )
        except Exception as exc:
            logger.debug("scan_trigger failed: %s", exc, exc_info=True)
            _log(f"  Scan trigger failed: {exc}", style="yellow")

    scans = ns_client.scan_result.list(
        parent=project,
        sort_by="meta.create_time",
        desc=True,
        max_pages=1,
    )
    if not scans:
        _log("  No scan results found for this project.", style="yellow")
        return
    scan = scans[0]
    scan_uuid = scan.uuid
    status = scan.spec.status if scan.spec else "UNKNOWN"
    _log(f"  Scan result: {scan_uuid}")
    _log(f"  Current status: {status}")

    start_time: str | None = None
    if scan.spec and scan.spec.start_time:
        start_dt = datetime.fromisoformat(scan.spec.start_time)
        start_time = (start_dt - timedelta(hours=1)).isoformat()

    log_client = endorlabs.Client(
        api_client=client._client,  # noqa: SLF001
        tenant=namespace,
        logging_level=getattr(client._client, "logging_level", "ERROR"),  # noqa: SLF001
    )
    seen: set[tuple[str | None, str]] = set()
    try:
        from endorlabs.resources.scan_log_request import (
            CreateScanLogRequestPayload,
            ScanLogRequestMetaCreate,
            ScanLogRequestSpecCreate,
        )

        payload = CreateScanLogRequestPayload(
            meta=ScanLogRequestMetaCreate(name=f"stream-{scan_uuid[:8]}"),
            spec=ScanLogRequestSpecCreate(
                max_entries=500,
                scan_result_uuid=scan_uuid,
                start_time=start_time,
                newest_first=False,
                end_time=None,
                log_levels=None,
                execution_id=None,
                project_uuid=None,
                installation_uuid=None,
                scan_request_uuid=None,
                onprem_scheduler_uuid=None,
                admin_filter=None,
            ),
        )
        result = log_client.scan_log_request.create(payload)
        lines: list[str] = []
        messages = result.spec.log_messages if result.spec else None
        for msg in messages or []:
            key = (msg.timestamp, str(msg.json_payload))
            if key in seen:
                continue
            seen.add(key)
            level = (msg.level.value if msg.level else "?").replace("LOG_LEVEL_", "")
            ts = msg.timestamp[:19] if msg.timestamp else ""
            text = ""
            if msg.json_payload:
                text = msg.json_payload.get("message", str(msg.json_payload))
            lines.append(f"  {ts} [{level:>8s}] {text}")
        _log(f"  Retrieved {len(lines)} log messages.", style="green")
        for line in lines[:12]:
            _log(line)
        if len(lines) > 12:
            _log(f"  ... and {len(lines) - 12} more", style="dim")
    except Exception as exc:
        logger.debug("scan_log_request failed: %s", exc, exc_info=True)
        _log(f"  Scan log retrieval failed: {exc}", style="yellow")


def _run_call_graph_for_project(client: endorlabs.Client, project: Any) -> None:
    """Retrieve and print a concise call-graph summary for a project."""
    from endorlabs.tools.dependency_explorer import (
        _build_call_tree,  # pyright: ignore[reportPrivateUsage]
        decode_callgraph,
        retrieve_call_graph_full,
    )

    namespace = _project_namespace(project)
    if namespace == "unknown-namespace":
        _log("  Could not resolve project namespace for call graph.", style="yellow")
        return

    pvs = client.package_version.list(
        namespace=namespace,
        filter=(
            f'spec.project_uuid=="{project.uuid}"'
            " AND spec.call_graph_available==true"
        ),
        max_pages=1,
        page_size=1,
    )
    if not pvs:
        _log("  No package version with call graph data found.", style="yellow")
        return

    pv = pvs[0]
    api_client = client._client  # noqa: SLF001
    if api_client is None:
        _log("  Client is closed; cannot retrieve call graph.", style="yellow")
        return

    cg_data = retrieve_call_graph_full(api_client, namespace, pv.uuid)
    if not cg_data or "zstd_bytes" not in cg_data:
        _log("  No decodable call graph data returned.", style="yellow")
        return

    info = decode_callgraph(cg_data)
    total_fp = sum(len(node.methods) for node in info.internal_types)
    total_tp = sum(len(node.methods) for node in info.external_types)
    _log(f"  Language: {info.language}", style="green")
    _log(
        f"  Functions: {total_fp} first-party, {total_tp} third-party stubs",
        style="green",
    )
    _log(f"  Call edges: {len(info.call_edges)}", style="green")
    tree = _build_call_tree(info)
    lines = tree.splitlines()
    _log("  Call tree preview:")
    for line in lines[:10]:
        _log(f"    {line}")
    if len(lines) > 10:
        _log(f"  ... and {len(lines) - 10} more lines", style="dim")


def _prompt_and_resolve_project(
    client: endorlabs.Client,
    namespace: str,
    label: str,
    *,
    capability_label: str,
    capability_check: Any,
) -> Any | None:
    """Prompt for y/n/uuid and return selected project, or ``None``."""
    choice = _parse_project_target_choice(
        _prompt_input(
            (
                f"{label} target (project UUID, or Enter to auto-select; "
                "type skip to skip): "
            ),
            default="",
        )
    )
    if choice.action == "skip":
        _log(f"  Skipping {label.lower()} step.", style="dim")
        return None
    if choice.action == "invalid":
        _log("  Input not understood. Use y/n/<uuid>. Skipping.", style="yellow")
        return None
    if choice.action == "uuid" and choice.uuid:
        _log(f"  Resolving UUID {choice.uuid} across namespaces...", style="dim")
        logger.debug("resolve_project_by_uuid=%s", choice.uuid)
        project = _resolve_project_by_uuid(client, choice.uuid)
        if project is None:
            _log("  UUID not found in tenant scope.", style="yellow")
            return None
        if not capability_check(client, project):
            _log(
                (
                    "  Project found, but it does not currently support "
                    f"{capability_label}."
                ),
                style="yellow",
            )
            return None
        return project
    return _choose_project_from_search(
        client,
        namespace,
        capability_label=capability_label,
        capability_check=capability_check,
    )


def _run_wizard_mode(*, verbose: bool) -> None:
    """Run the interactive demo wizard flow."""
    _load_dotenv()
    logging_level = _resolve_logging_level(verbose=verbose)
    _configure_logging(logging_level)

    _log("\nEndor Demo Wizard", style="bold cyan")
    _log(
        "  Guided flow for SDK syntax and real-world workflow examples.",
        style="dim",
    )

    auth_default = _normalize_wizard_auth_method(
        os.getenv("ENDOR_AUTH_METHOD", ""),
        default=(
            "api-key"
            if (
                os.getenv("ENDOR_API_CREDENTIALS_KEY")
                and os.getenv("ENDOR_API_CREDENTIALS_SECRET")
            )
            else "browser-auth"
        ),
    )
    auth_choice = _prompt_input(
        "Authentication method [api-key/browser-auth/sso/google/github/gitlab/email] ",
        default=auth_default,
    )
    auth_method = _normalize_wizard_auth_method(auth_choice, default=auth_default)
    auth_email: str | None = None
    auth_tenant: str | None = None
    if auth_method == "email":
        auth_email = _prompt_input(
            "Auth email (ENDOR_AUTH_EMAIL): ",
            default=os.getenv("ENDOR_AUTH_EMAIL", ""),
        )
        if not auth_email:
            _log("  Email auth requires an email address.", style="bold red")
            return
    if auth_method == "sso":
        auth_tenant = _prompt_input(
            "SSO auth tenant (ENDOR_AUTH_TENANT or ENDOR_INIT_AUTH_TENANT): ",
            default=os.getenv(
                "ENDOR_AUTH_TENANT",
                os.getenv("ENDOR_INIT_AUTH_TENANT", ""),
            ),
        )
        if not auth_tenant:
            _log("  SSO auth requires an auth tenant.", style="bold red")
            return

    namespace_default = os.getenv("ENDOR_NAMESPACE", "")
    namespace = _prompt_input(
        "Tenant namespace (ENDOR_NAMESPACE): ",
        default=namespace_default,
    )
    if not namespace:
        _log("  Namespace is required to continue.", style="bold red")
        return

    client = _build_client(
        namespace,
        auth_method,
        logging_level=logging_level,
        email=auth_email,
        auth_tenant=auth_tenant,
    )
    user_identity = "anonymous"
    with contextlib.suppress(Exception):
        user_identity = client.whoami() or "anonymous"
    _print_banner(namespace, user_identity)
    _wizard_discovery(client)

    _run_showcase_sections(client, namespace)

    _print_main_style_section("10", "Scan Trigger & Log Streaming")
    scan_project = _prompt_and_resolve_project(
        client,
        namespace,
        "Scan",
        capability_label="scan log retrieval",
        capability_check=_project_has_scan_results,
    )
    if scan_project is not None:
        _stream_scan_logs_for_project(
            client,
            scan_project,
            trigger_scan=_prompt_yes_no(
                "Trigger a fresh scan before log retrieval? [Y/n, Enter=yes]: ",
                default_yes=True,
            ),
        )

    _print_main_style_section("11", "Call Graph Exploration")
    call_graph_project = _prompt_and_resolve_project(
        client,
        namespace,
        "Call graph",
        capability_label="call graph retrieval",
        capability_check=_project_has_call_graph,
    )
    if call_graph_project is not None:
        _run_call_graph_for_project(client, call_graph_project)

    _log("\nWizard complete.", style="bold green")
    client.close()


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments for demo wizard mode."""
    parser = argparse.ArgumentParser(description="Endor Labs demo CLI")
    _ = parser.add_argument(
        "--verbose",
        action="store_true",
        default=False,
        help="Enable verbose debug logging for troubleshooting.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """Endor Labs SDK demo entrypoint."""
    args = _parse_args(argv)
    _run_wizard_mode(verbose=args.verbose)


if __name__ == "__main__":
    main()
