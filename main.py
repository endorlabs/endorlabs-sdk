"""Minimal entrypoint for Endor SDK.

Run with: uv run main.py
Environment is loaded from .env when using uv (UV_ENV_FILE) or direnv.
Credentials: set ENDOR_API_CREDENTIALS_KEY and ENDOR_API_CREDENTIALS_SECRET
in .env, or pass key= and secret= to APIClient(...).

Create an .env file in the root of the repository with the following variables:
ENDOR_API_CREDENTIALS_KEY=your-api-key
ENDOR_API_CREDENTIALS_SECRET=your-api-secret
ENDOR_NAMESPACE=your-tenant-namespace
ENDOR_LOG_LEVEL=DEBUG
ENDOR_MAX_RETRIES=5
ENDOR_TOKEN=your-token
ENDOR_AUTH_METHOD=api-key
ENDOR_EMAIL=your-email

Then run script with: uv run --env-file .env main.py

"""

import os

import endorlabs


def main() -> None:
    #########################################################
    ## Basic Usage Examples
    #########################################################
    """Create a client and list namespaces (demo entrypoint)."""
    # Replace with your tenant namespace
    client = endorlabs.Client(
        tenant=os.getenv("ENDOR_NAMESPACE", "endor-solutions-tgowan"),
        logging_level="ERROR",
        auth_method="api-key",
    )
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

    # Get operations
    project = client.project.get(projects[0].uuid)
    print(f"Project: {project.meta.name}")

    # Accessing Attributes of a resource
    if projects:
        project = projects[0]  # Get the first project
        print(f"Project: {project.spec.platform_source}")  # Print Attribute
        print(project)  # Print Object (its a Pydantic model)
        print(project.model_dump_json(indent=2))  # Print JSON via Pydantic

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
