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

import os
import queue
import shutil
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import endorlabs
from endorlabs.tools.dependency_explorer import (
    process_project,
    slugify,
)
from endorlabs.utils.logging_config import get_resource_logger
from endorlabs.utils.path_safety import safe_write_text
from endorlabs.workflows.session_context import (
    create_session,
)

logger = get_resource_logger(__name__)

DEFAULT_CONTEXT_DIR = ".endorlabs-context"

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


# ---------------------------------------------------------------------------
# Tenant catalog
# ---------------------------------------------------------------------------


class TenantCatalog:
    """Eagerly-loaded tenant-wide index of projects and namespaces."""

    def __init__(self) -> None:
        self.projects: list[Any] = []
        self.namespaces: list[Any] = []
        self.project_index: dict[str, Any] = {}

    def load(self, client: endorlabs.Client) -> None:
        """Pull all projects and namespaces (traverse)."""
        self.projects = client.project.list(traverse=True, max_pages=50, page_size=100)
        self.namespaces = client.namespace.list(traverse=True)

        # De-dup index by meta.name
        for p in self.projects:
            name = p.meta.name if p.meta else p.uuid
            if name not in self.project_index:
                self.project_index[name] = p

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
        projects = list(self.catalog.project_index.values())
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
        proj_slug = slugify(name)

        # Session context (findings, policies, versions)
        self._emit(f"  Pulling context for {short}...")
        try:
            session = create_session(self.client, proj, self.session_dir)
            self._emit(f"  {short}: {session.message.split(': ', 1)[-1]}")
        except Exception as exc:
            self._emit(f"  {short}: session failed — {exc}")
            return

        # Dependencies + call graphs
        dep_out = str(self.session_dir / proj_slug / "dependencies")
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
        combined = self._collect_summaries(proj_slug)
        with self._lock:
            self._context_cache[name] = combined

        # Threat model sub-agent (if LLM available)
        if self.llm and combined:
            self._emit(f"  Generating threat model for {short}...")
            try:
                from endorlabs.workflows.threat_analysis import (
                    analyze_project_threat_model,
                )

                tm = analyze_project_threat_model(self.llm, name, combined)
                if tm.ok:
                    tm_path = self.session_dir / proj_slug / "threat-model.md"
                    safe_write_text(self.session_dir, tm_path, tm.report)
                    self._emit(
                        f"  Threat model complete for {short}"
                        f" ({tm.risk_count} risks identified)"
                    )
                    with self._lock:
                        self._context_cache[name] += "\n\n---\n\n" + tm.report
                else:
                    self._emit(f"  {short}: threat model — {tm.message}")
            except Exception as exc:
                self._emit(f"  {short}: threat model failed — {exc}")

    def _collect_summaries(self, proj_slug: str) -> str:
        """Read written summary files and concatenate them."""
        proj_dir = self.session_dir / proj_slug
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
        # Try exact match first
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
        name = matches[0].meta.name if matches[0].meta else matches[0].uuid
        ctx = loader.get_context(name)
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
            pname = matches[0].meta.name if matches[0].meta else matches[0].uuid
            ctx = loader.get_context(pname)
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


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Endor Labs SDK Demo entry point."""
    _load_dotenv()

    logging.basicConfig(
        level=logging.ERROR,
        format="%(asctime)s %(levelname)-8s %(message)s",
        datefmt="%H:%M:%S",
    )

    # ---- Auto-auth (zero prompts) ----
    _log("\n  Authenticating...", style="dim")
    client = _auto_authenticate()

    import contextlib

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

    # ---- Check for CLI argument (one-shot mode) ----
    first_message = " ".join(sys.argv[1:]).strip() or None

    # ---- Chat loop ----
    _chat_loop(client, catalog, loader, first_message=first_message)

    client.close()


if __name__ == "__main__":
    main()
