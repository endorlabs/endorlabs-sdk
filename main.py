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
    """Create a client and list namespaces (demo entrypoint)."""
    client = endorlabs.Client(
        tenant=os.getenv("ENDOR_NAMESPACE", "endor-solutions-tgowan"),
        logging_level="ERROR",
        auth_method="api-key",
    )
    # Example: List operations
    namespaces = client.namespaces.list(traverse=True)
    for ns in namespaces:
        print(f"Namespaces: {ns.meta.name}")

    projects = client.projects.list(traverse=True)
    for project in projects:
        print(f"Projects: {project.meta.name}")

    projects = client.projects.list(filter="meta.name==https://github.com/Endor-Solutions-Architecture/endor-cockpit.git", max_pages=1)

    # Get operations

    # Print operations
    print(f"Project: {project.spec.platform_source}") # Print Attribute
    print(project) # Print Object
    print(project.model_dump_json(indent=2)) # Print JSON via Pydantic


if __name__ == "__main__":
    main()
