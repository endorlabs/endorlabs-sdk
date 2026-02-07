"""Minimal entrypoint for Endor SDK (maximum UX demo).

Run with: uv run main.py
Uses tenant and project ID only; no argparse, no pre-knowledge of backend paths
or filter syntax. Demonstrates: resolve by ID, resource as context, list(parent=),
.namespace, trigger scan, wait_until idle.

Env: ENDOR_API_CREDENTIALS_KEY, ENDOR_API_CREDENTIALS_SECRET (or .env).
"""

import endorlabs


def main() -> None:
    #########################################################
    ## Basic Usage Examples
    #########################################################
    """Create a client and list namespaces (demo entrypoint)."""
    # Replace with your tenant namespace
    client = endorlabs.Client(
        tenant="endor-solutions-tgowan",
        logging_level="ERROR",
        auth_method="api-key",
    )

    project = client.project.lookup(
        filter="meta.name == https://github.com/DefectDojo/django-DefectDojo.git"
    )
    findings = client.finding.list(
        filter=f"spec.project_uuid == {project.uuid}", traverse=True
    )
    for finding in findings:
        print(f"Finding: {finding.spec.summary}")
    print(f"Total findings: {len(findings)}")

    my_api_keys = client.api_key.list(traverse=True)
    for api_key in my_api_keys:
        print(f"API Key: {api_key.meta.name}")

    my_scan_profiles = client.scan_profile.list(traverse=True)
    for scan_profile in my_scan_profiles:
        print(f"Scan Profile: {scan_profile.meta.name}")

    # Example: List operations
    namespaces = client.namespace.list(traverse=True)
    for ns in namespaces:
        print(f"Namespaces: {ns.meta.name}")

    projects = client.project.list(traverse=True)  # Paginate by Page ID
    for project in projects:
        print(f"Projects: {project.meta.name}")

    projects = client.project.list(
        filter="meta.name==https://github.com/Endor-Solutions-Architecture/endor-cockpit.git",
        max_pages=1,
    )

    #########################################################
    ## Advanced Usage Examples
    #########################################################
    # Invoking a scan and waiting for it to complete
    # Find project by name (repo URL). SDK equivalent of:
    #   endorctl api list -r Project --traverse --filter "meta.name contains <repo_url>"
    repo_url = "https://github.com/tgowan-endor/BenchmarkJava.git"
    project = client.project.lookup(
        traverse=True,
        filter=f"meta.name=={repo_url}",  # exact name match
    )
    # Anything not attached to facade must be passed to the facade.
    # scan_state uses flat kwargs; pass directly; define in facade's update method.
    _ = client.project.update(project, scan_state="SCAN_STATE_REQUEST_FULL_RESCAN")
    # Wait for scan to complete
    _ = client.wait_until(
        lambda: (
            (p := client.project.get(project))
            and p.processing_status is not None
            and p.processing_status.scan_state == "SCAN_STATE_IDLE"
        ),
        timeout=300,
    )

    # Getting scan results for a project
    scans = client.scan_result.list(
        parent=project, max_pages=1, sort_by="meta.create_time", desc=True
    )
    print(f"Project: {project.meta.name}; scan results: {len(scans)}")
    print(f"Scan: {scans[0].model_dump_json(indent=2)}")


if __name__ == "__main__":
    main()
