"""Endor Labs SDK -- Feature Walkthrough.

Run with: uv run main.py

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
  9. Scan Trigger & Polling    -- Mutation + wait_until (opt-in)
 10. Workflow: Finding Triage  -- Higher-level composable workflow (dry-run)

Env: ENDOR_API_CREDENTIALS_KEY, ENDOR_API_CREDENTIALS_SECRET (or ENDOR_TOKEN).
"""

from __future__ import annotations

import endorlabs
from endorlabs import Client, F, NotFoundError

# ---------------------------------------------------------------------------
# Configuration -- change these to match your environment
# ---------------------------------------------------------------------------
TENANT = "endor-solutions-tgowan"
REPO_URL = "https://github.com/Endor-Solutions-Architecture/endorlabs-sdk.git"

# Opt-in flags for mutating operations (off by default)
DEMO_TRIGGER_SCAN = False


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
        print(f"    - {ns.meta.name}")
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
        print(f"  Caught NotFoundError with raw filter: {exc}")


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
# Section 9: Scan Trigger & Polling (opt-in)
# ===================================================================
def demo_scan_trigger(client: Client) -> None:
    """Trigger a full rescan and poll until it completes.

    This section is gated behind DEMO_TRIGGER_SCAN because it mutates
    state on the platform.  Set DEMO_TRIGGER_SCAN = True to enable.

    wait_until() uses jittered exponential backoff internally.
    """
    if not DEMO_TRIGGER_SCAN:
        print("  Skipped (set DEMO_TRIGGER_SCAN = True to enable).")
        return

    project = client.project.lookup(name=REPO_URL, traverse=True)
    print(f"  Triggering rescan for: {project.meta.name}")

    # Request a full rescan via flat kwargs on update()
    _ = client.project.update(project, scan_state="SCAN_STATE_REQUEST_FULL_RESCAN")

    # Poll until the scan returns to idle
    done = client.wait_until(
        lambda: (
            (p := client.project.get(project))
            and p.processing_status is not None
            and p.processing_status.scan_state == "SCAN_STATE_IDLE"
        ),
        timeout=300,
    )
    print(f"  Scan completed: {done}")

    # Fetch the latest scan result
    scans = client.scan_result.list(
        parent=project, sort_by="meta.create_time", desc=True, max_pages=1
    )
    if scans:
        print(f"  Latest scan: {scans[0].uuid}")


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
# Main -- run all sections in sequence
# ===================================================================
def main() -> None:
    """Run the SDK feature walkthrough."""
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
        ("9", "Scan Trigger & Polling"),
        ("10", "Workflow: Finding Triage"),
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
        ("9", "Scan Trigger & Polling", demo_scan_trigger),
        ("10", "Workflow: Finding Triage", demo_workflow_triage),
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
