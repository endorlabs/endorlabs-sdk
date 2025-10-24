#!/usr/bin/env python3
"""
Create Exception Policy Maneuver

A repeatable script for creating exception policies to suppress tagged findings using the Endor Labs API client.
This script creates Rego-based exception policies that automatically suppress findings tagged with
specific tags (e.g., 'false-positive').

Based on the OpenAPI schema and policy resource structure.

Example:

uv run python maneuvers/create_exception_policy.py \
  --namespace "endor-solutions-tgowan.cockpit" \
  --project-uuid "your-project-uuid" \
  --policy-name "Endor Cockpit - False Positive Exceptions" \
  --tag "false-positive" \
  --dry-run

## Note: This maneuver creates policies to suppress previously tagged findings.
"""

import argparse
import json
import logging
import os
import sys
from typing import List, Optional

# Add the src directory to the path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from endor_cockpit.api_client import APIClient
from endor_cockpit.resources import policy, project
from endor_cockpit.resources.policy import (
    CreatePolicyPayload,
    ExceptionReason,
    PolicyMeta,
    PolicySpec,
    PolicyType,
)

# Configure logging to reduce verbosity
logging.getLogger('urllib3.connectionpool').setLevel(logging.WARNING)
logging.getLogger('endor_cockpit').setLevel(logging.INFO)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def find_project_by_repository_url(
    client: APIClient,
    namespace: str,
    repository_url: str
) -> Optional[str]:
    """
    Find project UUID by repository URL.
    
    Args:
        client: Authenticated APIClient instance
        namespace: Target namespace
        repository_url: Repository URL to search for
        
    Returns:
        Project UUID or None if not found
    """
    try:
        # Try multiple filter approaches
        # Handle both github.com and api.github.com formats
        github_url = repository_url.replace("github.com", "api.github.com")
        filter_attempts = [
            f'spec.git.web_url=="{repository_url}"',
            f'spec.git.web_url=="{repository_url}.git"',
            f'spec.git.web_url=="{github_url}"',
            f'spec.git.web_url=="{github_url}.git"',
            f'meta.name=="{repository_url}"',
            f'meta.name=="{repository_url}.git"',
            f'spec.git.full_name=="{repository_url.split("/")[-1]}"',
        ]

        for filter_expr in filter_attempts:
            logger.info(f"Trying filter: {filter_expr}")
            from endor_cockpit.types import ListParameters
            list_params = ListParameters(filter=filter_expr)
            projects = project.list_projects(client, namespace, list_params)

            if projects:
                project_obj = projects[0]
                logger.info(f"Found project: {project_obj.meta.name} (UUID: {project_obj.uuid})")
                return project_obj.uuid

        # Fallback: search all projects
        logger.info("No projects found with filters, searching all projects...")
        all_projects = project.list_projects(client, namespace)
        
        for proj in all_projects:
            if repository_url in str(proj.model_dump()).lower():
                logger.info(f"Found matching project: {proj.meta.name} (UUID: {proj.uuid})")
                return proj.uuid

        logger.warning(f"No project found for repository: {repository_url}")
        return None

    except Exception as e:
        logger.error(f"Error finding project: {e}")
        return None


def create_exception_policy(
    client: APIClient,
    namespace: str,
    project_uuid: str,
    policy_name: str,
    policy_description: str,
    tag: str,
    propagate: bool = False
) -> Optional[dict]:
    """
    Create an exception policy to suppress findings with specific tags.
    
    Args:
        client: Authenticated APIClient instance
        namespace: Target namespace
        project_uuid: Project UUID to target
        policy_name: Name for the exception policy
        policy_description: Description for the exception policy
        tag: Tag to suppress (e.g., 'false-positive')
        propagate: Whether to propagate to child namespaces
        
    Returns:
        Created policy data or None if creation failed
    """
    try:
        # Build Rego rule to suppress findings with specified tag
        rego_rule = f"""package endor.cockpit.exceptions

match_finding[result] {{
  finding := input.resource
  finding.spec.project_uuid == "{project_uuid}"
  finding.meta.tags[_] == "{tag}"
  result = {{"Endor": {{"Finding": finding.uuid}}}}
}}"""

        # Create policy payload
        payload = CreatePolicyPayload(
            meta=PolicyMeta(
                name=policy_name,
                kind="Policy",
                description=policy_description,
                tags=["exception", tag, "endor-cockpit"],
            ),
            spec=PolicySpec(
                policy_type=PolicyType.EXCEPTION,
                rule=rego_rule,
                project_selector=[f"$uuid={project_uuid}"],
                resource_kinds=["Finding"],
                disable=False,
                exception={"reason": ExceptionReason.FALSE_POSITIVE},
            ),
            propagate=propagate,
        )

        # Create the policy
        exception_policy = policy.create_policy(client, namespace, payload)

        if exception_policy:
            logger.info(f"Created exception policy: {exception_policy.uuid}")
            return {
                "uuid": exception_policy.uuid,
                "name": exception_policy.meta.name,
                "namespace": namespace,
                "project_uuid": project_uuid,
                "tag": tag
            }
        else:
            logger.error("Failed to create exception policy")
            return None

    except Exception as e:
        logger.error(f"Error creating exception policy: {e}")
        
        # Log detailed error information
        if hasattr(e, "response"):
            try:
                error_details = (
                    e.response.json()
                    if hasattr(e.response, "json")
                    else str(e.response.text)
                )
                logger.error(f"API Error Details: {error_details}")
            except Exception:
                logger.error(
                    f"API Error Response: {
                        e.response.text
                        if hasattr(e.response, 'text')
                        else 'No response text'
                    }"
                )
        
        return None


def main():
    """Main function to create exception policy with command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Create exception policy to suppress tagged findings using Endor Labs API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create exception policy for false-positive tagged findings
  python maneuvers/create_exception_policy.py \\
    --namespace "endor-solutions-tgowan.cockpit" \\
    --project-uuid "your-project-uuid" \\
    --policy-name "Endor Cockpit - False Positive Exceptions" \\
    --tag "false-positive"

  # Create exception policy with repository URL lookup
  python maneuvers/create_exception_policy.py \\
    --namespace "endor-solutions-tgowan.cockpit" \\
    --repository-url "https://github.com/Endor-Solutions-Architecture/endor-cockpit" \\
    --policy-name "Endor Cockpit - False Positive Exceptions" \\
    --tag "false-positive" \\
    --propagate

  # Create exception policy with custom description
  python maneuvers/create_exception_policy.py \\
    --namespace "endor-solutions-tgowan.cockpit" \\
    --project-uuid "your-project-uuid" \\
    --policy-name "Custom Exception Policy" \\
    --description "Suppresses findings tagged as false-positive during manual triage" \\
    --tag "false-positive"
        """
    )

    # Required arguments
    parser.add_argument(
        "--namespace",
        required=True,
        help="Target namespace where the policy will be created"
    )
    parser.add_argument(
        "--policy-name",
        required=True,
        help="Name for the exception policy"
    )
    parser.add_argument(
        "--tag",
        required=True,
        help="Tag to suppress (e.g., 'false-positive')"
    )

    # Project identification (at least one required)
    project_group = parser.add_argument_group(
        "Project Identification",
        "Specify the project to target (at least one required)"
    )
    project_group.add_argument(
        "--project-uuid",
        help="Project UUID to target with the exception policy"
    )
    project_group.add_argument(
        "--repository-url",
        help="Repository URL to find project and target with the exception policy"
    )

    # Optional arguments
    parser.add_argument(
        "--description",
        help="Description for the exception policy (defaults to auto-generated description)"
    )
    parser.add_argument(
        "--propagate",
        action="store_true",
        help="Enable propagation to child namespaces"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show the policy payload that would be created without creating it"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )

    args = parser.parse_args()

    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Validate arguments
    if not args.project_uuid and not args.repository_url:
        parser.error("At least one of --project-uuid or --repository-url must be specified")

    try:
        # Initialize API client
        logger.info("Initializing API client...")
        client = APIClient()

        # Determine project UUID
        project_uuid = args.project_uuid
        if not project_uuid and args.repository_url:
            logger.info(f"Finding project for repository: {args.repository_url}")
            project_uuid = find_project_by_repository_url(client, args.namespace, args.repository_url)
            if not project_uuid:
                logger.error(f"Could not find project for repository: {args.repository_url}")
                sys.exit(1)

        # Generate description if not provided
        description = args.description
        if not description:
            description = (
                f"Suppresses findings tagged as '{args.tag}' during "
                f"manual triage for project {project_uuid}"
            )

        # Create Rego rule for preview
        rego_rule = f"""package endor.cockpit.exceptions

match_finding[result] {{
  finding := input.resource
  finding.spec.project_uuid == "{project_uuid}"
  finding.meta.tags[_] == "{args.tag}"
  result = {{"Endor": {{"Finding": finding.uuid}}}}
}}"""

        if args.dry_run:
            print("=== DRY RUN - Exception Policy Payload ===")
            print(f"Policy Name: {args.policy_name}")
            print(f"Description: {description}")
            print(f"Target Project UUID: {project_uuid}")
            print(f"Suppress Tag: {args.tag}")
            print(f"Propagate: {args.propagate}")
            print("\nRego Rule:")
            print(rego_rule)
            return

        # Create the exception policy
        logger.info("Creating exception policy...")
        result = create_exception_policy(
            client=client,
            namespace=args.namespace,
            project_uuid=project_uuid,
            policy_name=args.policy_name,
            policy_description=description,
            tag=args.tag,
            propagate=args.propagate
        )

        if result:
            print("=== Exception Policy Created Successfully ===")
            print(f"UUID: {result['uuid']}")
            print(f"Name: {result['name']}")
            print(f"Namespace: {result['namespace']}")
            print(f"Target Project: {result['project_uuid']}")
            print(f"Suppress Tag: {result['tag']}")
            print(f"Propagate: {args.propagate}")
        else:
            print("Failed to create exception policy")
            sys.exit(1)

    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
