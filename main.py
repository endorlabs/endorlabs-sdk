"""Endor Labs SDK -- Feature Walkthrough.

Run with: uv run main.py [--scan] [--context]

A progressive, runnable demo of the SDK's major features. Each section is an
independent function so you can read, run, or copy the parts you need.

Sections:
  0. Setup & Identity          -- Client context manager, whoami()
  1. Discovery                 -- Namespaces, projects, pagination
  2. Lookup by Identity Kwargs -- filter_kwarg_map shorthand
  3. F() Filter Builder        -- Type-safe, composable filters
  4. Cross-Resource Join       -- Project -> Findings -> Scan Results
  5. Streaming Iteration       -- Memory-efficient list_iter()
  6. Pydantic Serialization    -- model_dump / model_dump_json
  7. Error Handling            -- NotFoundError, AmbiguousError
  8. Field Masking             -- Reduce response payload
  9. Scan Trigger & Log Stream -- ScanLogRequest API; live tailing (--scan)
 10. Workflow: Finding Triage  -- Higher-level composable workflow (dry-run)
 11. Call Graph Exploration     -- Decode & render call graph from protobuf

Env: ENDOR_API_CREDENTIALS_KEY, ENDOR_API_CREDENTIALS_SECRET (or ENDOR_TOKEN).
"""

from __future__ import annotations

import argparse

import endorlabs
from endorlabs import Client, F, NotFoundError, ValidationError

# ---------------------------------------------------------------------------
# Configuration -- change these to match your environment
# ---------------------------------------------------------------------------
TENANT = "endor-solutions-tgowan"
REPO_URL = "https://github.com/Endor-Solutions-Architecture/endorlabs-sdk.git"

# Target for Section 9 (Scan & Log Streaming) -- short scan duration project
SCAN_PROJECT_NS = "endor-solutions-tgowan.tgowan-endor"
SCAN_PROJECT_UUID = "69458a5eb0e3885f66676057"

# Target for Section 11 (Call Graph) -- project with call graph data
CALLGRAPH_PROJECT_UUID = "698cfb4f26aee2696691c78e"


# ===================================================================
# Section 0: Setup & Identity
# ===================================================================
def demo_setup() -> Client:
    """Create an authenticated client and print the current identity.

    The SDK reads credentials from environment variables automatically.
    Using the context manager (``with``) ensures connections are cleaned up,
    but here we return the client for reuse across sections.
    """
    client = endorlabs.Client(
        tenant=TENANT,
        logging_level="ERROR",
        auth_method="api-key",
    )

    # whoami() resolves the human-readable identity bound to the API key
    identity = client.whoami()  # type: ignore[attr-defined]  # dynamic facade
    print(f"  Authenticated as: {identity}")
    print(f"  Default tenant:   {TENANT}")

    # Fetch the auth policy for detailed identity info (permissions, expiration)
    if identity:
        policy = client.authorization_policy.lookup(name=identity, traverse=True)
        if policy.spec:
            roles = policy.spec.permissions.roles if policy.spec.permissions else []
            print(f"  Roles:            {roles}")
            expiration = policy.spec.expiration_time or "never"
            print(f"  Expires:          {expiration}")

    return client


# ===================================================================
# Section 1: Discovery -- Namespaces & Projects
# ===================================================================
def demo_discovery(client: Client) -> None:
    """List namespaces and projects to explore what's available.

    ``traverse=True`` walks the full namespace hierarchy under the tenant.
    ``max_pages`` caps pagination so the demo stays fast.
    """
    # List all namespaces under the tenant
    namespaces = client.namespace.list(traverse=True)
    print(f"  Namespaces found: {len(namespaces)}")
    for ns in namespaces[:5]:
        full = ns.spec.full_name if ns.spec else ns.meta.name
        print(f"    - {full}")
    if len(namespaces) > 5:
        print(f"    ... and {len(namespaces) - 5} more")

    # List projects with pagination control
    projects = client.project.list(max_pages=1)
    print(f"  Projects (first page): {len(projects)}")
    for proj in projects[:3]:
        print(f"    - {proj.meta.name}")


# ===================================================================
# Section 2: Lookup by Identity Kwargs
# ===================================================================
def demo_lookup(client: Client) -> None:
    """Find a single resource by name using identity kwargs.

    The registry maps ``name=`` to ``meta.name`` in the API filter, so
    ``client.project.lookup(name="...")`` is a shorthand for:
        ``client.project.lookup(filter='meta.name=="..."')``

    ``lookup()`` returns exactly one result or raises NotFoundError /
    AmbiguousError.
    """
    project = client.project.lookup(
        name=REPO_URL,
        traverse=True,
    )
    print(f"  Found project: {project.meta.name}")
    print(f"  UUID:          {project.uuid}")


# ===================================================================
# Section 3: The F() Filter Builder
# ===================================================================
def demo_filters(client: Client) -> None:
    """Build type-safe, composable filters with the F() builder.

    F() supports all 12 API operators (==, !=, <, >, <=, >=, contains,
    not contains, in, not in, matches, exists) plus & (AND) and | (OR)
    for composition.  Date helpers: F.now("-72h"), F.date("2024-01-01").

    Raw filter strings are still accepted for backward compatibility.
    """
    # Simple equality filter
    critical = client.finding.list(
        filter=F("spec.level") == "FINDING_LEVEL_CRITICAL",
        traverse=True,
        max_pages=1,
    )
    print(f"  Critical findings (first page): {len(critical)}")

    # Composed filter: high+ severity AND reachable function
    high_reachable = client.finding.list(
        filter=(
            F("spec.level").is_in("FINDING_LEVEL_CRITICAL", "FINDING_LEVEL_HIGH")
            & F("spec.finding_tags").contains("FINDING_TAGS_REACHABLE_FUNCTION")
        ),
        traverse=True,
        max_pages=1,
    )
    print(f"  High+ reachable findings: {len(high_reachable)}")

    # Date helper: findings created in the last 72 hours
    recent = client.finding.list(
        filter=F("meta.create_time") >= F.now("-72h"),
        traverse=True,
        max_pages=1,
    )
    print(f"  Findings in last 72h: {len(recent)}")

    # Show the generated wire format for inspection
    composed = (F("spec.level") == "FINDING_LEVEL_CRITICAL") & (
        F("meta.create_time") >= F.now("-72h")
    )
    print(f"  Wire format: {composed}")


# ===================================================================
# Section 4: Cross-Resource Join (Project -> Findings -> Scans)
# ===================================================================
def demo_cross_resource(client: Client) -> None:
    """Navigate from a Project to its Findings and Scan Results.

    Two patterns:
      A) Filter-based join -- use ``spec.project_uuid`` to scope any resource
         to a project.  Works for all resources.
      B) Parent scoping -- use ``parent=project`` for resources that declare
         ``parent_kind`` in the registry (scan_result, repository_version).
         The SDK automatically adds ``meta.parent_uuid == project.uuid``.
    """
    # Step 1: Find the project
    project = client.project.lookup(name=REPO_URL, traverse=True)
    print(f"  Project: {project.meta.name}")

    # Pattern A: Filter-based join (findings scoped to project)
    findings = client.finding.list(
        filter=(
            (F("spec.project_uuid") == project.uuid)
            & (F("spec.level") == "FINDING_LEVEL_CRITICAL")
        ),
        sort_by="meta.create_time",
        desc=True,
        max_pages=1,
    )
    print(f"  Critical findings for project: {len(findings)}")
    for f_obj in findings[:3]:
        print(f"    - [{f_obj.spec.level}] {f_obj.spec.summary}")

    # Pattern B: Parent scoping (scan results for the project)
    # scan_result has parent_kind="project" in the registry, so parent= works.
    scans = client.scan_result.list(
        parent=project,
        sort_by="meta.create_time",
        desc=True,
        max_pages=1,
    )
    print(f"  Scan results for project: {len(scans)}")
    if scans:
        latest = scans[0]
        print(f"    Latest scan UUID: {latest.uuid}")
        ns = latest.tenant_meta.namespace if latest.tenant_meta else TENANT
        scan_url = (
            f"https://app.endorlabs.com/t/{ns}"
            f"/projects/{project.uuid}/scans/{latest.uuid}"
        )
        print(f"    Scan URL: {scan_url}")


# ===================================================================
# Section 5: Streaming Iteration
# ===================================================================
def demo_streaming(client: Client) -> None:
    """Process resources one at a time with list_iter().

    Unlike list() which loads all results into memory, list_iter() yields
    resources one page at a time -- ideal for large result sets or
    streaming pipelines.
    """
    count = 0
    for finding in client.finding.list_iter(traverse=True, max_pages=1):
        count += 1
        if count <= 3:
            print(f"    - [{finding.spec.level}] {finding.spec.summary}")
    print(f"  Streamed {count} findings (list_iter, 1 page)")


# ===================================================================
# Section 6: Pydantic Model Serialization
# ===================================================================
def demo_serialization(client: Client) -> None:
    """Every resource is a Pydantic model with full serialization support.

    - model_dump_json() -> JSON string (great for logging, storage)
    - model_dump()      -> Python dict (great for transformations)
    - exclude_none=True  -> compact output without null fields
    """
    projects = client.project.list(max_pages=1)
    if not projects:
        print("  No projects to serialize.")
        return

    project = projects[0]

    # JSON serialization (truncated for display)
    json_str = project.model_dump_json(indent=2)
    preview = json_str[:300]
    print(f"  JSON preview ({len(json_str)} chars total):")
    print(f"    {preview}...")

    # Dict serialization (compact)
    compact = project.model_dump(exclude_none=True)
    print(f"  Dict keys (exclude_none): {list(compact.keys())}")


# ===================================================================
# Section 7: Error Handling
# ===================================================================
def demo_error_handling(client: Client) -> None:
    """The SDK provides a structured exception hierarchy.

    All exceptions inherit from EndorAPIError and include context like
    status_code, operation, namespace, and resource_uuid.

    Key exceptions:
      - NotFoundError (404)      -- resource doesn't exist
      - AmbiguousError           -- lookup matched multiple resources
      - ValidationError (400)    -- bad request parameters
      - PermissionDeniedError (403)
      - UnauthorizedError (401)
      - RateLimitError (429)
      - ServerError (5xx)
    """
    # Intentionally trigger NotFoundError
    try:
        _ = client.project.lookup(name="nonexistent-repo-that-does-not-exist")
    except NotFoundError as exc:
        print(f"  Caught NotFoundError (expected): {exc}")

    # Show that raw filter strings still work alongside F()
    try:
        _ = client.project.lookup(
            filter='meta.name=="also-nonexistent"',
            traverse=True,
        )
    except NotFoundError as exc:
        print(f"  Caught NotFoundError (expected, raw filter): {exc}")

    # Malformed regex triggers protobuf field validation on the server (400)
    try:
        _ = client.project.list(filter='meta.name matches "["')
    except ValidationError as exc:
        print(f"  Caught ValidationError (expected): {exc}")


# ===================================================================
# Section 8: Field Masking
# ===================================================================
def demo_field_masking(client: Client) -> None:
    """Use ``mask=`` to request only the fields you need.

    This reduces response payload size and deserialization cost --
    especially useful for large resources like findings or package versions.
    """
    # Request only name and UUID
    projects = client.project.list(
        mask="meta.name,uuid",
        max_pages=1,
    )
    print(f"  Masked projects (first page): {len(projects)}")
    for proj in projects[:3]:
        print(f"    - {proj.meta.name} ({proj.uuid})")


# ===================================================================
# Section 9: Scan Trigger & Log Streaming  (helpers + demo)
# ===================================================================

# Type alias used by the log-streaming helpers below.
_SeenLogs = set[tuple[str | None, str]]


def _print_log_lines(lines: list[str], head: int = 10, tail: int = 5) -> None:
    """Print log lines with head/tail truncation for readability."""
    if len(lines) <= head + tail:
        for line in lines:
            print(line)
        return
    for line in lines[:head]:
        print(line)
    print(f"  ... ({len(lines) - head - tail} messages omitted)")
    for line in lines[-tail:]:
        print(line)


def _fetch_scan_log_batch(
    log_client: Client,
    scan_uuid: str,
    start_time: str | None,
    seen: _SeenLogs,
) -> tuple[int, str | None, list[str]]:
    """POST a ScanLogRequest and collect new log lines.

    Returns:
        (new_message_count, updated_start_time, formatted_lines) — the
        caller should feed the returned start_time back on the next call
        so the window advances.  Formatted lines are ready to print.
    """
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

    new_count = 0
    lines: list[str] = []
    messages = result.spec.log_messages if result.spec else None
    for msg in messages or []:
        key = (msg.timestamp, str(msg.json_payload))
        if key in seen:
            continue
        seen.add(key)
        new_count += 1

        level = (msg.level.value if msg.level else "?").replace("LOG_LEVEL_", "")
        ts = msg.timestamp[:19] if msg.timestamp else ""
        text = ""
        if msg.json_payload:
            text = msg.json_payload.get("message", str(msg.json_payload))
        if len(text) > 120:
            text = text[:117] + "..."
        lines.append(f"  {ts} [{level:>8s}] {text}")

        # Advance watermark so the next poll skips old entries
        if msg.timestamp and (start_time is None or msg.timestamp > start_time):
            start_time = msg.timestamp

    return new_count, start_time, lines


def _poll_scan_logs(
    ns_client: Client,
    log_client: Client,
    scan_uuid: str,
    start_time: str | None,
) -> int:
    """Poll for new logs every 5 s until the scan finishes.

    Returns:
        Total number of unique log messages printed.
    """
    import contextlib
    import time

    seen: _SeenLogs = set()
    all_lines: list[str] = []

    while True:
        try:
            new, start_time, batch_lines = _fetch_scan_log_batch(
                log_client, scan_uuid, start_time, seen
            )
            all_lines.extend(batch_lines)
            if new:
                print(f"  ... +{new} new ({len(seen)} total)")
        except Exception as exc:
            print(f"  (log poll error: {exc})")

        # Check whether the scan has finished
        current = ns_client.scan_result.get(scan_uuid)
        current_status = current.spec.status if current and current.spec else None
        if current_status and current_status != "STATUS_RUNNING":
            with contextlib.suppress(Exception):
                _, _, final_lines = _fetch_scan_log_batch(
                    log_client, scan_uuid, start_time, seen
                )
                all_lines.extend(final_lines)
            print(f"\n  --- Scan finished: {current_status} ---")
            break

        time.sleep(5)

    _print_log_lines(all_lines)
    return len(seen)


def demo_scan_and_stream(client: Client, *, trigger_scan: bool = False) -> None:
    """Trigger a scan and stream logs in real-time, like the Endor Labs UI.

    Demonstrates:
    - The ScanLogRequest API for retrieving scan logs
    - Polling with advancing time windows for live log tailing
    - Scan trigger via project update (opt-in with ``--scan``)

    Without ``--scan``: displays logs from the most recent scan result.
    With ``--scan``: triggers a new scan and streams logs as they arrive.
    """
    import time
    from datetime import datetime, timedelta

    # Scope a client to the target project's namespace, sharing transport
    ns_client = endorlabs.Client(
        api_client=client._client,  # noqa: SLF001
        tenant=SCAN_PROJECT_NS,
    )

    project = ns_client.project.get(SCAN_PROJECT_UUID)
    print(f"  Project:   {project.meta.name}")
    print(f"  Namespace: {SCAN_PROJECT_NS}")

    if trigger_scan:
        print("  Triggering rescan...")
        _ = ns_client.project.update(
            project, scan_state="SCAN_STATE_REQUEST_FULL_RESCAN"
        )
        time.sleep(3)  # brief pause for the platform to create the scan result

    # Find the latest scan result
    scans = ns_client.scan_result.list(
        parent=project, sort_by="meta.create_time", desc=True, max_pages=1
    )
    if not scans:
        print("  No scan results found for this project.")
        return

    scan = scans[0]
    scan_uuid = scan.uuid
    scan_ns = scan.tenant_meta.namespace if scan.tenant_meta else SCAN_PROJECT_NS
    status = scan.spec.status if scan.spec else "UNKNOWN"
    is_live = status == "STATUS_RUNNING"
    print(f"  ScanResult: {scan_uuid}")
    print(f"  Status:    {status}")

    # Initial time window: scan start minus 1h (API-recommended buffer).
    start_time: str | None = None
    if scan.spec and scan.spec.start_time:
        start_dt = datetime.fromisoformat(scan.spec.start_time)
        start_time = (start_dt - timedelta(hours=1)).isoformat()

    # ScanLogRequest API requires the scan result's own namespace
    log_client = endorlabs.Client(
        api_client=client._client,  # noqa: SLF001
        tenant=scan_ns,
    )

    mode = "live" if is_live else "recent"
    print(f"\n  --- Scan Logs ({mode}) ---")

    if is_live:
        total = _poll_scan_logs(ns_client, log_client, scan_uuid, start_time)
        print(f"  Total messages streamed: {total}")
    else:
        # One-shot: display logs from the most recent completed scan
        seen: _SeenLogs = set()
        lines: list[str] = []
        try:
            _, _, lines = _fetch_scan_log_batch(log_client, scan_uuid, start_time, seen)
        except Exception as exc:
            print(f"  Log fetch error: {exc}")
        _print_log_lines(lines)
        print(f"  Total messages: {len(seen)}")


# ===================================================================
# Section 10: Workflow -- Finding Triage (dry-run)
# ===================================================================
def demo_workflow_triage(client: Client) -> None:
    """Use the finding_triage workflow to tag findings by criteria.

    Workflows are higher-level composable functions that orchestrate
    multiple SDK calls.  dry_run=True previews the operation without
    making changes.
    """
    from endorlabs.workflows.finding_triage import tag_findings_by_criteria

    project = client.project.lookup(name=REPO_URL, traverse=True)
    namespace = project.tenant_meta.namespace if project.tenant_meta else TENANT

    result = tag_findings_by_criteria(
        client,
        namespace=namespace,
        project_uuid=project.uuid,
        categories=["FINDING_CATEGORY_SAST"],
        tag="reviewed",
        dry_run=True,
    )
    print(f"  Triage result (dry-run): {result.message}")
    print(
        f"  Status: {result.status}, Total: {result.total}, Would tag: {result.tagged}"
    )


# ===================================================================
# Section 11: Call Graph Exploration
# ===================================================================
def demo_call_graph(client: Client) -> None:
    """Retrieve, decode, and display a truncated call graph.

    Demonstrates the ``dependency_explorer`` module which can:

    - Fetch raw call graph data from ``/v1/namespaces/{ns}/call-graph-data``
    - Decode zstd-compressed protobuf (no compiled proto dependency)
    - Render an ASCII call tree showing caller-to-callee relationships

    Requires the ``zstandard`` package for protobuf decompression.
    """
    from endorlabs.tools.dependency_explorer import (
        _build_call_tree,  # pyright: ignore[reportPrivateUsage]
        decode_callgraph,
        retrieve_call_graph_full,
    )

    # Find the project (traverse to search child namespaces)
    projects = client.project.list(
        filter=F("uuid") == CALLGRAPH_PROJECT_UUID,
        traverse=True,
        max_pages=1,
        page_size=1,
    )
    if not projects:
        print("  Project not found.")
        return

    project = projects[0]
    namespace = project.tenant_meta.namespace if project.tenant_meta else TENANT
    print(f"  Project:   {project.meta.name}")
    print(f"  Namespace: {namespace}")

    # Get a PackageVersion that has call graph data
    pvs = client.package_version.list(
        namespace=namespace,
        filter=(
            f'spec.project_uuid=="{CALLGRAPH_PROJECT_UUID}"'
            " AND spec.call_graph_available==true"
        ),
        max_pages=1,
        page_size=1,
    )
    if not pvs:
        print("  No PackageVersions with call graph found.")
        return

    pv = pvs[0]
    print(f"  Package:   {pv.meta.name}")

    # Retrieve the raw call graph via the low-level API
    api_client = client._client  # noqa: SLF001
    if api_client is None:
        print("  Client is closed.")
        return
    cg_data = retrieve_call_graph_full(api_client, namespace, pv.uuid)
    if not cg_data or "zstd_bytes" not in cg_data:
        print("  No decodable call graph data returned.")
        return

    # Decode the zstd-compressed protobuf into structured data
    info = decode_callgraph(cg_data)
    total_fp = sum(len(t.methods) for t in info.internal_types)
    total_tp = sum(len(t.methods) for t in info.external_types)

    print(f"  Language:   {info.language}")
    print(
        f"  Modules:    {len(info.internal_types)} internal, "
        f"{len(info.external_types)} external"
    )
    print(f"  Functions:  {total_fp} first-party, {total_tp} third-party stubs")
    print(f"  Call edges: {len(info.call_edges)}")

    # Show a truncated ASCII call tree
    tree = _build_call_tree(info)
    tree_lines = tree.splitlines()
    max_lines = 25
    print(f"\n  Call Tree ({len(tree_lines)} lines, showing first {max_lines}):")
    for line in tree_lines[:max_lines]:
        print(f"    {line}")
    if len(tree_lines) > max_lines:
        print(f"    ... and {len(tree_lines) - max_lines} more lines")


# ===================================================================
# Main -- run all sections in sequence
# ===================================================================
def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for the demo walkthrough."""
    parser = argparse.ArgumentParser(
        description="Endor Labs SDK -- Feature Walkthrough",
    )
    parser.add_argument(
        "--scan",
        action="store_true",
        default=False,
        help=(
            "Trigger a new scan and stream logs live (Section 9). "
            "Without this flag, Section 9 still runs but shows logs "
            "from the most recent completed scan."
        ),
    )
    parser.add_argument(
        "--context",
        action="store_true",
        default=False,
        help=(
            "Bootstrap local context by downloading the OpenAPI spec and "
            "user docs into .endorlabs-context/. Uses force=True to "
            "re-download even if files already exist."
        ),
    )
    return parser.parse_args()


def main() -> None:
    """Run the SDK feature walkthrough."""
    args = parse_args()

    if args.context:
        print("\n" + "=" * 60)
        print(" Context Bootstrap")
        print("=" * 60)
        status = endorlabs.init(force=True)
        print(f"  OpenAPI spec: {status.openapi_path}")
        print(f"  User docs:    {status.user_docs_path} ({status.user_docs_count} pages)")
        print("  Context sync complete.")

    sections: list[tuple[str, str]] = [
        ("0", "Setup & Identity"),
        ("1", "Discovery -- Namespaces & Projects"),
        ("2", "Lookup by Identity Kwargs"),
        ("3", "F() Filter Builder"),
        ("4", "Cross-Resource Join"),
        ("5", "Streaming Iteration"),
        ("6", "Pydantic Model Serialization"),
        ("7", "Error Handling"),
        ("8", "Field Masking"),
        ("9", "Scan Trigger & Log Streaming"),
        ("10", "Workflow: Finding Triage"),
        ("11", "Call Graph Exploration"),
    ]

    # Section 0 returns the client; the rest consume it
    print(f"\n{'=' * 60}")
    print(f" [{sections[0][0]}] {sections[0][1]}")
    print(f"{'=' * 60}")
    client = demo_setup()

    # Map section numbers to their demo functions
    demos: list[tuple[str, str, object]] = [
        ("1", "Discovery -- Namespaces & Projects", demo_discovery),
        ("2", "Lookup by Identity Kwargs", demo_lookup),
        ("3", "F() Filter Builder", demo_filters),
        ("4", "Cross-Resource Join", demo_cross_resource),
        ("5", "Streaming Iteration", demo_streaming),
        ("6", "Pydantic Model Serialization", demo_serialization),
        ("7", "Error Handling", demo_error_handling),
        ("8", "Field Masking", demo_field_masking),
        (
            "9",
            "Scan Trigger & Log Streaming",
            lambda c: demo_scan_and_stream(c, trigger_scan=args.scan),
        ),
        ("10", "Workflow: Finding Triage", demo_workflow_triage),
        ("11", "Call Graph Exploration", demo_call_graph),
    ]

    try:
        for num, title, func in demos:
            print(f"\n{'=' * 60}")
            print(f" [{num}] {title}")
            print(f"{'=' * 60}")
            try:
                func(client)  # type: ignore[operator]
            except Exception as exc:
                print(f"  ERROR: {exc}")
                print("  (continuing to next section)")
    finally:
        client.close()
        print(f"\n{'=' * 60}")
        print(" Done. Client closed.")
        print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
