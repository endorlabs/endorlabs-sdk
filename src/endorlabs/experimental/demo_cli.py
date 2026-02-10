# ruff: noqa: T201, S105
"""Interactive Endor Labs Explorer CLI demo.

Provides an interactive entrypoint that authenticates, resolves the
current user, dynamically searches for repositories, pulls per-project
context (findings, policies, dependencies, call graphs), and launches
a LangGraph chat agent pre-loaded with that context.

Run with::

    uv run endor-demo
    uv run python -m endorlabs.experimental.demo_cli

Env:
    ENDOR_API_CREDENTIALS_KEY, ENDOR_API_CREDENTIALS_SECRET — API key auth
    ENDOR_NAMESPACE — default tenant namespace
    GEMINI_API_KEY — Google Gemini API key for the LLM agent

Experimental: API may change without the same stability guarantees
as the rest of the SDK.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Any

import endorlabs
from endorlabs.experimental.dependency_explorer import (
    process_project,
    slugify,
)
from endorlabs.experimental.workflows.session_context import (
    create_session,
)

logger = logging.getLogger(__name__)

DEFAULT_CONTEXT_DIR = ".endorlabs-context"


# ---------------------------------------------------------------------------
# Phase 1: Authentication
# ---------------------------------------------------------------------------


def _get_tenant() -> str:
    """Resolve tenant namespace from env or interactive prompt."""
    ns = os.getenv("ENDOR_NAMESPACE", "").strip()
    if ns:
        return ns
    try:
        ns = input("  Tenant namespace: ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        sys.exit(0)
    if not ns:
        print("  Error: namespace is required.")
        sys.exit(1)
    return ns


def authenticate() -> endorlabs.Client:
    """Interactive authentication: detect env vars or fall back to browser.

    Returns:
        Authenticated :class:`endorlabs.Client` with logging set to ERROR.
    """
    key = os.getenv("ENDOR_API_CREDENTIALS_KEY")
    secret = os.getenv("ENDOR_API_CREDENTIALS_SECRET")
    token = os.getenv("ENDOR_TOKEN")

    if key and secret:
        print("  Found API key credentials in environment.")
        try:
            use_env = input("  Use these credentials? [Y/n]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            sys.exit(0)
        if use_env != "n":
            tenant = _get_tenant()
            return endorlabs.Client(
                tenant=tenant,
                logging_level="ERROR",
                auth_method="api-key",
            )

    if token and token != "browser":
        print("  Found bearer token in environment.")
        try:
            use_token = input("  Use this token? [Y/n]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            sys.exit(0)
        if use_token != "n":
            tenant = _get_tenant()
            return endorlabs.Client(tenant=tenant, logging_level="ERROR")

    # Fall back to browser auth
    print("  No credentials found. Opening browser for authentication...")
    tenant = _get_tenant()
    return endorlabs.Client(
        tenant=tenant,
        logging_level="ERROR",
        auth_method="browser",
    )


# ---------------------------------------------------------------------------
# Phase 2: whoami
# ---------------------------------------------------------------------------


def resolve_user(client: endorlabs.Client) -> str:
    """Resolve the current user identity.

    Returns:
        User identity string, or ``"anonymous"`` if resolution fails.
    """
    try:
        user = client.whoami()
    except Exception:
        user = None
    if user:
        print(f"  Authenticated as: {user}")
    else:
        print("  Could not resolve user identity.")
        user = "anonymous"
    return user


# ---------------------------------------------------------------------------
# Phase 3: Interactive repo search
# ---------------------------------------------------------------------------


def search_repo(client: endorlabs.Client) -> Any:
    """Interactive project search with fuzzy matching.

    Returns:
        Selected project resource object.
    """
    while True:
        try:
            query = input(
                "\nSearch for a project (e.g. 'juice-shop', 'endor-cockpit'): "
            ).strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            sys.exit(0)

        if not query:
            continue

        print(f"  Searching for '{query}' ...")
        try:
            projects = client.project.list(
                filter=f'meta.name matches "{query}"',
                traverse=True,
                max_pages=1,
                page_size=20,
            )
        except Exception as exc:
            print(f"  Search failed: {exc}")
            continue

        if not projects:
            print(f"  No projects found matching '{query}'. Try again.")
            continue

        # De-duplicate by meta.name (traverse may return same
        # repo in sibling namespaces)
        seen: dict[str, Any] = {}
        for p in projects:
            name = p.meta.name if p.meta else p.uuid
            if name not in seen:
                seen[name] = p
        projects = list(seen.values())

        print(f"\n  Found {len(projects)} project(s):")
        for i, p in enumerate(projects, 1):
            name = p.meta.name if p.meta else p.uuid
            ns = p.tenant_meta.namespace if p.tenant_meta else ""
            print(f"  {i}. {name}  ({ns})")

        try:
            choice = input("\n  Select a project [1]: ").strip() or "1"
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            sys.exit(0)

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(projects):
                selected = projects[idx]
                name = selected.meta.name if selected.meta else selected.uuid
                print(f"  Selected: {name}")
                return selected
            else:
                print("  Invalid selection. Try again.")
        except ValueError:
            print("  Invalid input. Enter a number.")


# ---------------------------------------------------------------------------
# Phase 4: Context loading
# ---------------------------------------------------------------------------


def load_context(
    client: endorlabs.Client,
    project: Any,
    session_dir: Path,
) -> str:
    """Pull all context for the project and return summary text for the LLM.

    Args:
        client: Authenticated client.
        project: Selected project resource.
        session_dir: Session output directory.

    Returns:
        Combined summary Markdown text for injection into the LLM prompt.
    """
    project_name = project.meta.name if project.meta else project.uuid

    # Pull findings, policies, versions
    print("  Loading findings, policies, and versions ...")
    session = create_session(client, project, session_dir)
    print(f"    {session.message}")

    # Pull dependencies and call graphs
    print("  Loading dependencies and call graphs ...")
    proj_slug = slugify(project_name)
    dep_out_dir = str(session_dir / proj_slug / "dependencies")

    try:
        api_client = client._client  # type: ignore[attr-defined]  # noqa: SLF001
        project_ns = (
            project.tenant_meta.namespace
            if project.tenant_meta and project.tenant_meta.namespace
            else client._default_namespace or ""  # noqa: SLF001
        )
        dep_result = process_project(
            client,
            api_client,
            project_ns,
            project,
            dep_out_dir,
            pv_limit=5,
            dep_metadata_max_pages=10,
        )
        # Write the summary file
        summary_path = Path(dep_out_dir) / "dependency-callgraph-summary.md"
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(dep_result.report, encoding="utf-8")
        print(f"    Dependencies: {dep_result.dep_metadata_count} metadata rows")
    except Exception as exc:
        logger.warning("Failed to load dependencies: %s", exc)
        print(f"    Warning: dependency loading failed: {exc}")
        dep_result = None

    # Collect summaries for LLM context
    context_parts: list[str] = []
    proj_dir = session_dir / proj_slug

    for rel_path in [
        "project-summary.md",
        "findings/findings-summary.md",
        "policies/policies-summary.md",
        "repository-versions/versions-summary.md",
        "dependencies/dependency-callgraph-summary.md",
    ]:
        full_path = proj_dir / rel_path
        if full_path.exists():
            text = full_path.read_text(encoding="utf-8")
            # Truncate very large files for context window
            if len(text) > 50_000:
                text = text[:50_000] + "\n\n... (truncated)"
            context_parts.append(text)

    combined = "\n\n---\n\n".join(context_parts)
    print(f"  Context loaded: {len(combined):,} chars")
    return combined


# ---------------------------------------------------------------------------
# Phase 5: Chat loop
# ---------------------------------------------------------------------------


def chat_loop(
    client: endorlabs.Client,
    project: Any,
    context_text: str,
) -> None:
    """Interactive CLI chat with the LangGraph agent.

    Args:
        client: Authenticated client (for live API tools).
        project: Selected project resource.
        context_text: Pre-loaded summary context for the system prompt.
    """
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI

        from endorlabs.experimental.langgraph_agent import create_endor_graph
    except ImportError:
        print(
            "\n  LangGraph dependencies not installed."
            "\n  Install with: pip install endor-cockpit[experimental]"
            "\n  Exiting."
        )
        return

    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        print(
            "\n  GEMINI_API_KEY not set. The agent requires a Gemini API key."
            "\n  Exiting."
        )
        return

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        api_key=gemini_key,
    )
    graph = create_endor_graph(client, llm)

    project_name = project.meta.name if project.meta else project.uuid
    short_name = project_name.split("/")[-1].replace(".git", "")

    sep = "=" * 60
    print(f"\n{sep}")
    print(f"  Endor Labs Explorer \u2014 {short_name}")
    print("  Type 'quit' to exit, 'summary' for a quick overview")
    print(f"{sep}\n")

    messages: list[Any] = []
    if context_text:
        messages.append(
            (
                "system",
                f"You have access to pre-loaded analysis data for "
                f"{project_name}. Use this to answer questions about "
                f"dependencies, call graphs, findings, policies, and security.\n\n"
                f"{context_text}",
            )
        )

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue

        if user_input.lower() in ("quit", "exit", "q"):
            print("Goodbye!")
            break

        if user_input.lower() == "summary":
            user_input = (
                "Summarize this project: its dependency tree, call graph "
                "patterns, security findings by category, and active policies. "
                "Highlight any notable risks or patterns."
            )

        messages.append(("user", user_input))

        try:
            result = graph.invoke({"messages": messages})
            response = result["messages"][-1].content
            print(f"\nAssistant: {response}\n")
            messages = result["messages"]
        except Exception as exc:
            print(f"\n  Agent error: {exc}\n")


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def _load_dotenv() -> None:
    """Load ``.env`` from the current directory if present (no dependency)."""
    env_file = Path(".env")
    if not env_file.exists():
        return
    with open(env_file, encoding="utf-8") as f:
        for raw_line in f:
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


def main() -> None:
    """Interactive Endor Labs Explorer demo entry point."""
    _load_dotenv()

    logging.basicConfig(
        level=logging.ERROR,
        format="%(asctime)s %(levelname)-8s %(message)s",
        datefmt="%H:%M:%S",
    )

    print()
    print("  Endor Labs Interactive Explorer")
    print("  " + "=" * 36)
    print()

    # Phase 1: Auth
    client = authenticate()

    # Phase 2: whoami
    user = resolve_user(client)
    session_dir = Path(DEFAULT_CONTEXT_DIR) / f"session-{slugify(user)}"

    # Phase 3: Repo search
    project = search_repo(client)

    # Phase 4: Auto-load context
    print("\nLoading project context ...")
    context_text = load_context(client, project, session_dir)

    # Phase 5: Chat
    chat_loop(client, project, context_text)

    client.close()


if __name__ == "__main__":
    main()
