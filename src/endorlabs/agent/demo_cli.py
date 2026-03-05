"""Endor Labs SDK Demo — agent-first CLI.

Zero-prompt startup: auto-authenticates from environment, loads tenant
catalog eagerly, pulls per-project context in the background, spawns
appsec sub-agents for threat modelling, and presents an always-available
input prompt while status updates stream above a divider.

Run with::

    uv run endor-demo
    uv run endor-demo "what is my riskiest project?"

Env:
    ENDOR_API_CREDENTIALS_KEY, ENDOR_API_CREDENTIALS_SECRET — API key auth
    ENDOR_NAMESPACE — default tenant namespace
    GEMINI_API_KEY — Google Gemini API key for the LLM agent

Experimental: API may change without the same stability guarantees
as the rest of the SDK.
"""

from __future__ import annotations

import argparse
from collections import Counter
import contextlib
import logging
import os
import queue
import re
import shutil
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import endorlabs
from endorlabs import F
from endorlabs.tools.dependency_explorer import (
    process_project,
    slugify,
)
from endorlabs.utils.logging_config import get_resource_logger
from endorlabs.utils.path_safety import safe_write_text
from endorlabs.workflows.session_context import (
    build_project_session_key,
    create_session,
)

logger = get_resource_logger(__name__)

DEFAULT_CONTEXT_DIR = ".endorlabs-context"
UUID_PATTERN = re.compile(r"^[0-9a-f]{24}$", re.IGNORECASE)

# ---------------------------------------------------------------------------
# Rich console (lazy import — optional dependency)
# ---------------------------------------------------------------------------

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
    """Print a styled message via Rich, falling back to plain ``print``."""
    con = _get_console()
    if con and style:
        con.print(msg, style=style)
    elif con:
        con.print(msg)
    else:
        print(msg)


# ---------------------------------------------------------------------------
# .env loader (no third-party dependency)
# ---------------------------------------------------------------------------


def _load_dotenv() -> None:
    """Load ``.env`` from the working directory if present."""
    env_file = Path(".env")
    if not env_file.exists():
        return
    with open(env_file, encoding="utf-8") as fh:
        for raw_line in fh:
            stripped = raw_line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if "=" not in stripped:
                continue
            k, v = stripped.split("=", 1)
            k, v = k.strip(), v.strip()
            if (v.startswith('"') and v.endswith('"')) or (
                v.startswith("'") and v.endswith("'")
            ):
                v = v[1:-1]
            if k and not os.getenv(k):
                os.environ[k] = v


# ---------------------------------------------------------------------------
# Banner
# ---------------------------------------------------------------------------


def _print_banner(tenant: str, user: str) -> None:
    """Print a terminal-width-aware ASCII banner."""
    con = _get_console()
    if con:
        try:
            from rich.panel import Panel
            from rich.text import Text

            body = Text()
            body.append("Endor Labs SDK Demo\n", style="bold")
            body.append(f"Tenant: {tenant}\n", style="dim")
            body.append(f"User:   {user}", style="dim")
            con.print(Panel(body, expand=False, border_style="cyan"))
            return
        except ImportError:
            pass

    # Fallback: plain ASCII
    width = min(shutil.get_terminal_size().columns, 60)
    border = "=" * width
    print(f"\n{border}")
    print("  Endor Labs SDK Demo")
    print(f"  Tenant: {tenant}")
    print(f"  User:   {user}")
    print(f"{border}\n")


# ---------------------------------------------------------------------------
# Auto-auth (zero prompts)
# ---------------------------------------------------------------------------


def _auto_authenticate() -> endorlabs.Client:
    """Authenticate without any interactive prompts.

    Priority: API key > bearer token > browser (silent open).
    """
    key = os.getenv("ENDOR_API_CREDENTIALS_KEY")
    secret = os.getenv("ENDOR_API_CREDENTIALS_SECRET")
    token = os.getenv("ENDOR_TOKEN")
    tenant = os.getenv("ENDOR_NAMESPACE", "")

    if not tenant:
        _log(
            "  ENDOR_NAMESPACE not set — cannot auto-authenticate.",
            style="bold red",
        )
        sys.exit(1)

    if key and secret:
        return endorlabs.Client(
            tenant=tenant, logging_level="ERROR", auth_method="api-key"
        )

    if token and token != "browser":
        return endorlabs.Client(tenant=tenant, logging_level="ERROR")

    # Silent browser auth
    return endorlabs.Client(tenant=tenant, logging_level="ERROR", auth_method="browser")


def _build_client(
    tenant: str,
    auth_method: str,
    *,
    email: str | None = None,
    auth_tenant: str | None = None,
) -> endorlabs.Client:
    """Create an authenticated SDK client for the wizard flow."""
    return endorlabs.Client(
        tenant=tenant,
        logging_level="ERROR",
        auth_method=auth_method,
        email=email,
        auth_tenant=auth_tenant,
    )


def _normalize_wizard_auth_method(raw: str, *, default: str) -> str:
    """Normalize wizard auth input to the SDK's canonical auth methods."""
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
    """Prompt for a yes/no response with Enter honoring the default."""
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
    """Parse ``y/n/<uuid>`` style input into a normalized action."""
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
    """Resolve a project UUID across namespaces transparently."""
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
    return needle == uuid or needle in uuid or needle == name or needle in name


def _select_auto_project_candidate(eligible: list[Any], query: str) -> Any:
    """Select a project candidate automatically from eligible results."""
    if query:
        query_matches = [
            project for project in eligible if _project_matches_identifier(project, query)
        ]
        if query_matches:
            return query_matches[0]
    return eligible[0]


def _print_main_style_section(section_num: str, title: str) -> None:
    """Print section output in the same style as the legacy walkthrough."""
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
        categories = getattr(spec, "finding_categories", None) or []
        tags = getattr(spec, "finding_tags", None) or []
        for category in categories:
            category_value = getattr(category, "value", category)
            category_counts[str(category_value)] += 1
        for tag in tags:
            tag_counts[str(tag)] += 1
    return category_counts, tag_counts


def _project_has_scan_results(client: endorlabs.Client, project: Any) -> bool:
    """Return ``True`` when the project has at least one scan result."""
    try:
        scans = client.scan_result.list(parent=project, max_pages=1, page_size=1)
    except Exception:
        return False
    return bool(scans)


def _project_has_call_graph(client: endorlabs.Client, project: Any) -> bool:
    """Return ``True`` when the project has at least one call graph package version."""
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
        _log(f"  No projects in this scope currently support {capability_label}.", style="yellow")
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


# ---------------------------------------------------------------------------
# Tenant catalog
# ---------------------------------------------------------------------------


class TenantCatalog:
    """Eagerly-loaded tenant-wide index of projects and namespaces."""

    def __init__(self) -> None:
        self.projects: list[Any] = []
        self.namespaces: list[Any] = []
        self.project_index: dict[str, Any] = {}
        self.projects_by_uuid: dict[str, Any] = {}
        self.projects_by_name: dict[str, list[Any]] = {}

    def load(self, client: endorlabs.Client) -> None:
        """Pull all projects and namespaces (traverse)."""
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
        """Resolve a project from uuid, exact name, or display key."""
        if identifier in self.projects_by_uuid:
            return self.projects_by_uuid[identifier]
        if identifier in self.project_index:
            return self.project_index[identifier]
        by_name = self.projects_by_name.get(identifier)
        if by_name and len(by_name) == 1:
            return by_name[0]
        return None


# ---------------------------------------------------------------------------
# Background context loader
# ---------------------------------------------------------------------------


class BackgroundContextLoader:
    """Loads per-project context in a background thread.

    Status messages are collected in a thread-safe list and drained
    by the main loop for display.
    """

    def __init__(
        self,
        client: endorlabs.Client,
        catalog: TenantCatalog,
        session_dir: Path,
        llm: Any | None = None,
    ) -> None:
        self.client = client
        self.catalog = catalog
        self.session_dir = session_dir
        self.llm = llm

        self._status_messages: list[str] = []
        self._lock = threading.Lock()
        self._context_cache: dict[str, str] = {}
        self._done = threading.Event()
        self._thread: threading.Thread | None = None

    # -- status helpers --

    def _emit(self, msg: str) -> None:
        with self._lock:
            self._status_messages.append(msg)

    def drain_messages(self) -> list[str]:
        """Return and clear pending status messages (thread-safe)."""
        with self._lock:
            msgs = list(self._status_messages)
            self._status_messages.clear()
        return msgs

    @property
    def is_done(self) -> bool:
        """Return ``True`` when background loading has finished."""
        return self._done.is_set()

    def get_context(self, project_name: str) -> str | None:
        """Return cached context for a project, or ``None``."""
        project = self.catalog.resolve_identifier(project_name)
        if project is not None:
            project_uuid = str(getattr(project, "uuid", "")).strip()
            if project_uuid:
                with self._lock:
                    return self._context_cache.get(project_uuid)
        with self._lock:
            return self._context_cache.get(project_name)

    # -- loading logic --

    def start(self) -> None:
        """Start background loading in a daemon thread."""
        self._thread = threading.Thread(
            target=self._run, daemon=True, name="context-loader"
        )
        self._thread.start()

    def _run(self) -> None:
        try:
            self._load_all()
        except Exception as exc:
            self._emit(f"  [red]Background loading error: {exc}[/red]")
            logger.exception("Background context loading failed")
        finally:
            self._done.set()

    def _load_all(self) -> None:
        projects = list(self.catalog.projects_by_uuid.values())
        max_workers = min(4, len(projects) or 1)
        with ThreadPoolExecutor(
            max_workers=max_workers, thread_name_prefix="ctx"
        ) as pool:
            futures = {pool.submit(self._load_one, proj): proj for proj in projects}
            for future in as_completed(futures):
                # Surface exceptions via _emit (already handled inside
                # _load_one), but guard against unexpected blow-ups.
                try:
                    future.result()
                except Exception as exc:
                    proj = futures[future]
                    name = proj.meta.name if proj.meta else proj.uuid
                    self._emit(f"  {name}: unexpected error — {exc}")

        self._emit("  [bold green]Ready[/bold green]")

    def _load_one(self, proj: Any) -> None:
        """Load context for a single project (runs in a worker thread)."""
        name = proj.meta.name if proj.meta else proj.uuid
        short = name.split("/")[-1].replace(".git", "")
        project_key = build_project_session_key(proj)

        # Session context (findings, policies, versions)
        self._emit(f"  Pulling context for {short}...")
        try:
            session = create_session(self.client, proj, self.session_dir)
            self._emit(f"  {short}: {session.message.split(': ', 1)[-1]}")
        except Exception as exc:
            self._emit(f"  {short}: session failed — {exc}")
            return

        # Dependencies + call graphs
        dep_out = str(self.session_dir / project_key / "dependencies")
        try:
            api_client = self.client._client  # noqa: SLF001
            pns = (
                proj.tenant_meta.namespace
                if proj.tenant_meta and proj.tenant_meta.namespace
                else ""
            )
            dep_result = process_project(
                self.client,
                api_client,
                pns,
                proj,
                dep_out,
                pv_limit=5,
                dep_metadata_max_pages=10,
            )
            sp = Path(dep_out) / "dependency-callgraph-summary.md"
            safe_write_text(self.session_dir, sp, dep_result.report)
            self._emit(f"  Dependencies and call graphs loaded for {short}")
        except Exception as exc:
            self._emit(f"  {short}: deps failed — {exc}")

        # Collect combined summary
        combined = self._collect_summaries(project_key)
        with self._lock:
            self._context_cache[proj.uuid] = combined

        # Threat model sub-agent (if LLM available)
        if self.llm and combined:
            self._emit(f"  Generating threat model for {short}...")
            try:
                from endorlabs.workflows.threat_analysis import (
                    analyze_project_threat_model,
                )

                tm = analyze_project_threat_model(self.llm, name, combined)
                if tm.ok:
                    tm_path = self.session_dir / project_key / "threat-model.md"
                    safe_write_text(self.session_dir, tm_path, tm.report)
                    self._emit(
                        f"  Threat model complete for {short}"
                        f" ({tm.risk_count} risks identified)"
                    )
                    with self._lock:
                        self._context_cache[proj.uuid] += "\n\n---\n\n" + tm.report
                else:
                    self._emit(f"  {short}: threat model — {tm.message}")
            except Exception as exc:
                self._emit(f"  {short}: threat model failed — {exc}")

    def _collect_summaries(self, project_key: str) -> str:
        """Read written summary files and concatenate them."""
        proj_dir = self.session_dir / project_key
        parts: list[str] = []
        for rel in [
            "project-summary.md",
            "findings/findings-summary.md",
            "policies/policies-summary.md",
            "repository-versions/versions-summary.md",
            "dependencies/dependency-callgraph-summary.md",
        ]:
            fp = proj_dir / rel
            if fp.exists():
                text = fp.read_text(encoding="utf-8")
                if len(text) > 50_000:
                    text = text[:50_000] + "\n\n... (truncated)"
                parts.append(text)
        return "\n\n---\n\n".join(parts)


# ---------------------------------------------------------------------------
# Dynamic LangGraph tools
# ---------------------------------------------------------------------------


def _make_load_project_context_tool(
    loader: BackgroundContextLoader,
    catalog: TenantCatalog,
) -> Any:
    """Create a ``load_project_context`` tool for the agent."""
    from langchain_core.tools import StructuredTool

    def load_project_context(project_name: str) -> str:
        """Load detailed security context for a project.

        Searches the tenant catalog for a matching project and returns
        the pre-loaded context including findings, policies, dependencies,
        call graphs, and threat model.

        Args:
            project_name: Full or partial project name to search for.

        Returns:
            Combined Markdown summary, or an error message.
        """
        exact_project = catalog.resolve_identifier(project_name)
        if exact_project is not None:
            ctx = loader.get_context(exact_project.uuid)
            if ctx:
                return ctx

        # Try direct cache lookup (uuid/display key)
        ctx = loader.get_context(project_name)
        if ctx:
            return ctx

        # Fuzzy match
        matches = catalog.fuzzy_match(project_name)
        if not matches:
            return (
                f"No project matching '{project_name}' found. "
                f"Available: {', '.join(list(catalog.project_index)[:10])}"
            )
        match = matches[0]
        name = match.meta.name if match.meta else match.uuid
        ctx = loader.get_context(match.uuid)
        if ctx:
            return ctx

        return f"Context for '{name}' is still loading. Try again in a moment."

    return StructuredTool.from_function(
        func=load_project_context,
        name="load_project_context",
        description=(
            "Load detailed security context for a project including "
            "findings, policies, dependencies, call graphs, and "
            "threat model. Use for deep-dive analysis."
        ),
    )


def _make_compare_projects_tool(
    loader: BackgroundContextLoader,
    catalog: TenantCatalog,
) -> Any:
    """Create a ``compare_projects`` tool for the agent."""
    from langchain_core.tools import StructuredTool

    def compare_projects(project_names: str) -> str:
        """Compare security posture across multiple projects.

        Args:
            project_names: Comma-separated list of project names
                (full or partial).

        Returns:
            Combined context for all matched projects, or an error.
        """
        names = [n.strip() for n in project_names.split(",") if n.strip()]
        parts: list[str] = []
        for name in names:
            matches = catalog.fuzzy_match(name)
            if not matches:
                parts.append(f"## {name}\n\nNot found.")
                continue
            match = matches[0]
            pname = match.meta.name if match.meta else match.uuid
            ctx = loader.get_context(match.uuid)
            short = pname.split("/")[-1].replace(".git", "")
            if ctx:
                parts.append(f"## {short}\n\n{ctx}")
            else:
                parts.append(f"## {short}\n\nContext still loading.")
        return "\n\n---\n\n".join(parts) if parts else "No projects matched."

    return StructuredTool.from_function(
        func=compare_projects,
        name="compare_projects",
        description=(
            "Compare security posture across multiple projects. "
            "Pass a comma-separated list of project names."
        ),
    )


# ---------------------------------------------------------------------------
# Chat loop
# ---------------------------------------------------------------------------


def _chat_loop(
    client: endorlabs.Client,
    catalog: TenantCatalog,
    loader: BackgroundContextLoader,
    *,
    first_message: str | None = None,
) -> None:
    """Agent-first chat loop with Rich status updates above input."""
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI

        from endorlabs.agent.langgraph_agent import (
            create_endor_graph,
        )
    except ImportError:
        _log(
            "\n  LangGraph dependencies not installed."
            "\n  Install with: pip install endorlabs-sdk[agent]"
            "\n  Exiting.",
            style="bold red",
        )
        return

    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        _log(
            "\n  GEMINI_API_KEY not set. The agent requires a Gemini key.\n  Exiting.",
            style="bold red",
        )
        return

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        api_key=gemini_key,
    )

    extra_tools = [
        _make_load_project_context_tool(loader, catalog),
        _make_compare_projects_tool(loader, catalog),
    ]

    # Build system prompt with tenant catalog
    catalog_lines = [f"- {name}" for name in list(catalog.project_index)[:50]]
    system_prompt = (
        "You are the Endor Labs security assistant. You have access to "
        "a tenant with the following projects:\n"
        + "\n".join(catalog_lines)
        + "\n\nUse load_project_context to get detailed analysis for any "
        "project. Use compare_projects for cross-project comparison.\n"
        "When asked about security posture, risks, or recommendations, "
        "load context first, then reason over it."
    )

    graph = create_endor_graph(
        client,
        llm,
        extra_tools=extra_tools,
        system_prompt=system_prompt,
    )

    con = _get_console()
    if con:
        from rich.rule import Rule

        con.print(Rule(style="dim"))
    else:
        print("-" * 40)

    _log("  Type 'quit' to exit.", style="dim")
    print()

    messages: list[Any] = []

    # ---- threaded input reader --------------------------------
    # ``input()`` blocks, so we read it in a background thread and
    # poll for both new user input *and* background status messages
    # on the main thread.

    input_q: queue.Queue[str | None] = queue.Queue()

    def _read_input(prompt: str) -> None:
        """Read one line from stdin and put it on the queue."""
        try:
            line = input(prompt)
            input_q.put(line.strip())
        except (EOFError, KeyboardInterrupt):
            input_q.put(None)  # sentinel: user wants to quit

    def _drain_status() -> None:
        """Print any pending background status messages."""
        for msg in loader.drain_messages():
            # Overwrite the "You: " prompt before printing status,
            # then re-issue the prompt on the next iteration.
            _log(msg)

    # If there's a first message from CLI args, inject it
    pending_input = first_message

    while True:
        _drain_status()

        if pending_input is not None:
            user_input: str | None = pending_input
            pending_input = None
            _log(f"You: {user_input}", style="bold")
        else:
            # Start the input reader thread so we can keep draining
            # status messages while waiting for user input.
            input_thread = threading.Thread(
                target=_read_input, args=("You: ",), daemon=True
            )
            input_thread.start()

            # Poll: drain messages every 250 ms until the user submits
            user_input = None
            while True:
                try:
                    user_input = input_q.get(timeout=0.25)
                    break
                except queue.Empty:
                    _drain_status()

        if user_input is None:
            print("\nGoodbye!")
            break

        if not user_input:
            continue

        if user_input.lower() in ("quit", "exit", "q"):
            print("Goodbye!")
            break

        if user_input.lower() == "summary":
            user_input = (
                "Give me a security posture overview: for each project, "
                "load its context and summarize the dependency tree, "
                "call graph patterns, security findings by category, "
                "active policies, and highlight notable risks."
            )

        messages.append(("user", user_input))

        try:
            if con:
                with con.status("Thinking...", spinner="dots"):
                    result = graph.invoke({"messages": messages})
            else:
                result = graph.invoke({"messages": messages})
            response = result["messages"][-1].content
            _log(f"\nAssistant: {response}\n")
            messages = result["messages"]
        except Exception as exc:
            _log(f"\n  Agent error: {exc}\n", style="bold red")


def _wizard_bootstrap_context() -> None:
    """Run local context bootstrap for agentic IDE indexing."""
    _log(
        "  Pulling local context files for IDE indexing"
        " (OpenAPI + docs + project context)...",
        style="dim",
    )
    status = endorlabs.init(force=False)
    _log(f"  OpenAPI spec: {status.openapi_path}", style="green")
    _log(
        f"  User docs: {status.user_docs_path} ({status.user_docs_count} pages)",
        style="green",
    )


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

    def _section_10() -> None:
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

        _log(
            "  Automation use: feed these distributions into triage/tagging policies."
        )

    _run_section("1", "Discovery -- Namespaces & Projects", _section_1)
    _run_section("2", "Lookup by Identity Kwargs", _section_2)
    _run_section("3", "F() Filter Builder", _section_3)
    _run_section("4", "Cross-Resource Join", _section_4)
    _run_section("5", "Streaming Iteration", _section_5)
    _run_section("6", "Pydantic Model Serialization", _section_6)
    _run_section("7", "Error Handling", _section_7)
    _run_section("8", "Field Masking", _section_8)
    _run_section("9", "Workflow: Tags and Category Summary", _section_10)


def _stream_scan_logs_for_project(
    client: endorlabs.Client,
    project: Any,
    *,
    trigger_scan: bool,
) -> None:
    """Stream recent scan logs for a selected project."""
    from datetime import datetime, timedelta

    namespace = (
        project.tenant_meta.namespace
        if project.tenant_meta and project.tenant_meta.namespace
        else ""
    )
    if not namespace:
        _log("  Could not resolve project namespace for scan logs.", style="yellow")
        return

    ns_client = endorlabs.Client(
        api_client=client._client,  # noqa: SLF001
        tenant=namespace,
    )
    if trigger_scan:
        _log("  Triggering full rescan...", style="dim")
        _ = ns_client.project.update(project, scan_state="SCAN_STATE_REQUEST_FULL_RESCAN")
        time.sleep(3)

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
        _log(f"  Scan log retrieval failed: {exc}", style="yellow")


def _run_call_graph_for_project(client: endorlabs.Client, project: Any) -> None:
    """Retrieve and print a concise call-graph summary for a project."""
    from endorlabs.tools.dependency_explorer import (
        _build_call_tree,  # pyright: ignore[reportPrivateUsage]
        decode_callgraph,
        retrieve_call_graph_full,
    )

    namespace = (
        project.tenant_meta.namespace
        if project.tenant_meta and project.tenant_meta.namespace
        else ""
    )
    if not namespace:
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
    """Prompt for y/n/uuid and return the selected project, or ``None``."""
    choice = _parse_project_target_choice(
        _prompt_input(
            f"{label} target (project UUID, or Enter to auto-select; type skip to skip): ",
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
        project = _resolve_project_by_uuid(client, choice.uuid)
        if project is None:
            _log("  UUID not found in tenant scope.", style="yellow")
            return None
        if not capability_check(client, project):
            _log(
                f"  Project found, but it does not currently support {capability_label}.",
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


def _run_wizard_mode() -> None:
    """Run the interactive demo wizard flow."""
    _load_dotenv()
    _log("\nEndor Demo Wizard", style="bold cyan")
    _log(
        "  This guided flow configures auth, optional local context indexing, "
        "and scoped project demos.",
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
        "Authentication method "
        "[api-key/browser-auth/sso/google/github/gitlab/email] "
        "(alias: browser -> browser-auth): ",
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
            default=os.getenv("ENDOR_AUTH_TENANT", os.getenv("ENDOR_INIT_AUTH_TENANT", "")),
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
        email=auth_email,
        auth_tenant=auth_tenant,
    )
    user_identity = "anonymous"
    with contextlib.suppress(Exception):
        user_identity = client.whoami() or "anonymous"
    _print_banner(namespace, user_identity)
    _wizard_discovery(client)

    if _prompt_yes_no(
        "In an agentic IDE (e.g. Cursor) and want local context files indexed? "
        "[Y/n, Enter=yes]: ",
        default_yes=True,
    ):
        _wizard_bootstrap_context()

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
    """Parse CLI arguments for wizard and agent modes."""
    parser = argparse.ArgumentParser(description="Endor Labs demo CLI")
    parser.add_argument(
        "--agent",
        action="store_true",
        default=False,
        help="Run the agent chat experience (requires agent dependencies).",
    )
    parser.add_argument(
        "message",
        nargs="*",
        help="Optional initial user message for --agent mode.",
    )
    return parser.parse_args(argv)


def _run_agent_mode(first_message: str | None = None) -> None:
    """Run the existing agent-first demo mode."""
    _load_dotenv()

    logging.basicConfig(
        level=logging.ERROR,
        format="%(asctime)s %(levelname)-8s %(message)s",
        datefmt="%H:%M:%S",
    )

    # ---- Auto-auth (zero prompts) ----
    _log("\n  Authenticating...", style="dim")
    client = _auto_authenticate()

    user_identity = "anonymous"
    with contextlib.suppress(Exception):
        user_identity = client.whoami() or "anonymous"
    tenant = os.getenv("ENDOR_NAMESPACE", "unknown")

    _print_banner(tenant, user_identity)

    # ---- Eager tenant catalog ----
    _log("  Retrieving context...", style="dim")
    catalog = TenantCatalog()
    try:
        catalog.load(client)
    except Exception as exc:
        _log(f"  Failed to load catalog: {exc}", style="bold red")
        sys.exit(1)
    _log(f"  [{len(catalog.project_index)}] Projects pulled", style="green")

    # ---- Session directory ----
    session_dir = Path(DEFAULT_CONTEXT_DIR) / f"session-{slugify(user_identity)}"

    # ---- Resolve LLM for sub-agents (optional) ----
    llm: Any = None
    gemini_key = os.getenv("GEMINI_API_KEY")
    if gemini_key:
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI

            llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", api_key=gemini_key)
        except ImportError:
            pass

    # ---- Start background loading ----
    loader = BackgroundContextLoader(client, catalog, session_dir, llm=llm)
    loader.start()

    # Give background a head-start, drain initial messages
    time.sleep(0.5)
    for msg in loader.drain_messages():
        _log(msg)

    # ---- Chat loop ----
    _chat_loop(client, catalog, loader, first_message=first_message)

    client.close()


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Endor Labs SDK demo entry point."""
    args = _parse_args()
    if args.agent:
        first_message = " ".join(args.message).strip() or None
        _run_agent_mode(first_message)
        return
    _run_wizard_mode()


if __name__ == "__main__":
    main()
