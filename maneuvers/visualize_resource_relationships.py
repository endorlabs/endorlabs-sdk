#!/usr/bin/env python3
"""
Resource Relationship Visualization

A script to visualize detailed resource relationships in Endor Labs platform
using NetworkX and matplotlib. Supports two main views:

1. Project-centric view: Shows a project's findings, dependencies,
   repositoryVersions, and packageVersions
2. Finding-centric view: Shows which packages introduced a finding,
   which projects are affected, and related dependencies

Requirements:
    pip install networkx matplotlib

Examples:
    # Project-centric view
    uv run python maneuvers/visualize_resource_relationships.py \
      --namespace "endor-solutions-tgowan" \
      --project-uuid "project-uuid-here" \
      --output "project_graph.png"

    # Finding-centric view
    uv run python maneuvers/visualize_resource_relationships.py \
      --namespace "endor-solutions-tgowan" \
      --finding-uuid "finding-uuid-here" \
      --output "finding_graph.png"
"""

import argparse
import logging
import os
import sys
from typing import Dict, List, Optional, Set, Tuple, Any

# Add the src directory to the path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

try:
    import networkx as nx
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
except ImportError as e:
    print(
        "Error: Required packages not installed.\n"
        "Please install: pip install networkx matplotlib"
    )
    sys.exit(1)

from endor_cockpit.api_client import APIClient
from endor_cockpit.resources import (
    finding,
    package_version,
    project,
    repository,
    repository_version,
    dependency_metadata,
)
from endor_cockpit.resources.finding import Finding
from endor_cockpit.resources.package_version import PackageVersion
from endor_cockpit.resources.project import Project
from endor_cockpit.resources.repository import Repository
from endor_cockpit.resources.repository_version import RepositoryVersion
from endor_cockpit.resources.dependency_metadata import DependencyMetadata
from endor_cockpit.types import ListParameters
from endor_cockpit.utils.logging_config import setup_logging

logger = logging.getLogger(__name__)


def collect_project_resources(
    client: APIClient, namespace: str, project_uuid: str
) -> Dict[str, Any]:
    """
    Collect all resources related to a project.

    Args:
        client: Authenticated APIClient instance
        namespace: Target namespace
        project_uuid: Project UUID

    Returns:
        Dictionary containing all project-related resources
    """
    logger.info(f"Collecting resources for project: {project_uuid}")

    # Get the project
    project_obj = project.get_project(client, namespace, project_uuid)
    if not project_obj:
        raise ValueError(f"Project {project_uuid} not found in namespace {namespace}")

    # Collect findings
    logger.debug("Collecting findings...")
    findings_list = []
    try:
        findings_list_params = ListParameters(
            filter=f'spec.project_uuid=="{project_uuid}"',
            page_size=500,
        )
        findings_list = finding.list_findings(client, namespace, findings_list_params)
    except Exception as e:
        logger.warning(f"Error collecting findings: {e}")

    # Collect repository (if exists)
    logger.debug("Collecting repository...")
    repository_obj = None
    try:
        repos_list_params = ListParameters(
            filter=f'meta.parent_uuid=="{project_uuid}"',
        )
        repos = repository.list_repositories(client, namespace, repos_list_params)
        if repos:
            repository_obj = repos[0]
    except Exception as e:
        logger.warning(f"Error collecting repository: {e}")

    # Collect repository versions
    logger.debug("Collecting repository versions...")
    repo_versions = []
    try:
        repo_versions_params = ListParameters(
            filter=f'meta.parent_uuid=="{project_uuid}"',
        )
        repo_versions = repository_version.list_repository_versions(
            client, namespace, repo_versions_params
        )
    except Exception as e:
        logger.warning(f"Error collecting repository versions: {e}")

    # Collect package versions
    logger.debug("Collecting package versions...")
    package_versions_list = []
    try:
        package_versions_params = ListParameters(
            filter=f'spec.project_uuid=="{project_uuid}"',
            page_size=500,
        )
        package_versions_list = package_version.list_package_versions(
            client, namespace, package_versions_params
        )
    except Exception as e:
        logger.warning(f"Error collecting package versions: {e}")

    # Collect dependency metadata for all package versions
    logger.debug("Collecting dependency metadata...")
    dependency_metadata_list = []
    for pkg_version in package_versions_list:
        try:
            deps_params = ListParameters(
                filter=f'meta.parent_uuid=="{pkg_version.uuid}"',
            )
            deps = dependency_metadata.list_dependency_metadata(
                client, namespace, deps_params
            )
            dependency_metadata_list.extend(deps)
        except Exception as e:
            logger.debug(f"Error collecting dependency metadata for {pkg_version.uuid}: {e}")

    logger.info(
        f"Collected resources: {len(findings_list)} findings, "
        f"{len(package_versions_list)} package versions, "
        f"{len(repo_versions)} repository versions, "
        f"{len(dependency_metadata_list)} dependency metadata entries"
    )

    return {
        "project": project_obj,
        "findings": findings_list,
        "repository": repository_obj,
        "repository_versions": repo_versions,
        "package_versions": package_versions_list,
        "dependency_metadata": dependency_metadata_list,
    }


def collect_finding_resources(
    client: APIClient, namespace: str, finding_uuid: str
) -> Dict[str, Any]:
    """
    Collect all resources related to a finding.

    Args:
        client: Authenticated APIClient instance
        namespace: Target namespace
        finding_uuid: Finding UUID

    Returns:
        Dictionary containing all finding-related resources
    """
    logger.info(f"Collecting resources for finding: {finding_uuid}")

    # Get the finding
    finding_obj = finding.get_finding(client, namespace, finding_uuid)
    if not finding_obj:
        raise ValueError(f"Finding {finding_uuid} not found in namespace {namespace}")

    # Get the project
    project_obj = None
    if finding_obj.spec and finding_obj.spec.project_uuid:
        try:
            project_obj = project.get_project(
                client, namespace, finding_obj.spec.project_uuid
            )
            if not project_obj:
                logger.warning(
                    f"Project {finding_obj.spec.project_uuid} not found for finding"
                )
        except Exception as e:
            logger.warning(f"Error getting project for finding: {e}")

    # Resolve target resource
    target_resource = None
    if finding_obj.spec and finding_obj.spec.target_uuid:
        try:
            target_resource = resolve_target_resource(
                client, namespace, finding_obj.spec.target_uuid
            )
        except Exception as e:
            logger.warning(f"Error resolving target resource: {e}")

    # Resolve dependency package
    dependency_package = None
    finding_spec = finding_obj.spec
    if finding_spec:
        if (
            finding_spec.target_dependency_package_name
            or finding_spec.target_dependency_name
        ):
            try:
                dependency_package = resolve_dependency_package(
                    client,
                    namespace,
                    package_name=finding_spec.target_dependency_name,
                    package_version=finding_spec.target_dependency_version,
                    package_name_full=finding_spec.target_dependency_package_name,
                )
            except Exception as e:
                logger.warning(f"Error resolving dependency package: {e}")

    return {
        "finding": finding_obj,
        "project": project_obj,
        "target_resource": target_resource,
        "dependency_package": dependency_package,
        "transitive_dependencies": [],  # Will be built in build_transitive_dependency_graph
    }


def resolve_target_resource(
    client: APIClient, namespace: str, target_uuid: str
) -> Optional[Dict[str, Any]]:
    """
    Resolve a finding's target resource by UUID.

    Findings can target PackageVersion, Repository, or RepositoryVersion.
    This function tries each type until it finds a match.

    Args:
        client: Authenticated APIClient instance
        namespace: Target namespace
        target_uuid: UUID of the target resource

    Returns:
        Dictionary with 'type' and 'resource' keys, or None if not found
    """
    if not target_uuid:
        return None

    logger.debug(f"Resolving target resource: {target_uuid}")

    # Try PackageVersion first (most common)
    try:
        pkg_version = package_version.get_package_version(client, namespace, target_uuid)
        if pkg_version:
            logger.debug(f"Target resource is PackageVersion: {target_uuid}")
            return {"type": "PackageVersion", "resource": pkg_version}
    except Exception as e:
        logger.debug(f"Target is not PackageVersion: {e}")

    # Try RepositoryVersion
    try:
        repo_version = repository_version.get_repository_version(
            client, namespace, target_uuid
        )
        if repo_version:
            logger.debug(f"Target resource is RepositoryVersion: {target_uuid}")
            return {"type": "RepositoryVersion", "resource": repo_version}
    except Exception as e:
        logger.debug(f"Target is not RepositoryVersion: {e}")

    # Try Repository
    try:
        repo = repository.get_repository(client, namespace, target_uuid)
        if repo:
            logger.debug(f"Target resource is Repository: {target_uuid}")
            return {"type": "Repository", "resource": repo}
    except Exception as e:
        logger.debug(f"Target is not Repository: {e}")

    logger.warning(f"Could not resolve target resource: {target_uuid}")
    return None


def resolve_dependency_package(
    client: APIClient,
    namespace: str,
    package_name: Optional[str] = None,
    package_version: Optional[str] = None,
    package_name_full: Optional[str] = None,
) -> Optional[PackageVersion]:
    """
    Resolve a dependency package by name and version.

    Args:
        client: Authenticated APIClient instance
        namespace: Target namespace
        package_name: Dependency package name
        package_version: Dependency package version
        package_name_full: Fully qualified package name (e.g., "eco://package@version")

    Returns:
        PackageVersion if found, None otherwise
    """
    # Try using full package name first if available
    if package_name_full:
        logger.debug(f"Resolving dependency package by full name: {package_name_full}")
        try:
            # PackageVersion names are in format "ecosystem://package@version"
            # Try to find by name
            list_params = ListParameters(
                filter=f'meta.name=="{package_name_full}"',
            )
            pkg_versions = package_version.list_package_versions(
                client, namespace, list_params
            )
            if pkg_versions:
                logger.debug(f"Found package by full name: {package_name_full}")
                return pkg_versions[0]
        except Exception as e:
            logger.debug(f"Error resolving by full name: {e}")

    # Try using package name and version
    if package_name and package_version:
        logger.debug(
            f"Resolving dependency package: {package_name}@{package_version}"
        )
        try:
            # Try to find by spec.package_name and version in name
            # PackageVersion names include version, so search for it
            search_name = f"{package_name}@{package_version}"
            list_params = ListParameters(
                filter=f'meta.name contains "{search_name}"',
            )
            pkg_versions = package_version.list_package_versions(
                client, namespace, list_params
            )
            if pkg_versions:
                # Filter to exact match if possible
                for pkg in pkg_versions:
                    if (
                        pkg.spec
                        and pkg.spec.package_name == package_name
                        and pkg.meta
                        and package_version in pkg.meta.name
                    ):
                        logger.debug(
                            f"Found package: {package_name}@{package_version}"
                        )
                        return pkg
                # Return first match if no exact match
                if pkg_versions:
                    logger.debug(
                        f"Found approximate match for: {package_name}@{package_version}"
                    )
                    return pkg_versions[0]
        except Exception as e:
            logger.debug(f"Error resolving by name/version: {e}")

    # Try using just package name
    if package_name:
        logger.debug(f"Resolving dependency package by name only: {package_name}")
        try:
            list_params = ListParameters(
                filter=f'spec.package_name=="{package_name}"',
            )
            pkg_versions = package_version.list_package_versions(
                client, namespace, list_params
            )
            if pkg_versions:
                # If version specified, prefer matching version
                if package_version:
                    for pkg in pkg_versions:
                        if pkg.meta and package_version in pkg.meta.name:
                            return pkg
                # Return first match
                logger.debug(f"Found package by name: {package_name}")
                return pkg_versions[0]
        except Exception as e:
            logger.debug(f"Error resolving by name: {e}")

    logger.warning(
        f"Could not resolve dependency package: "
        f"{package_name_full or f'{package_name}@{package_version}'}"
    )
    return None


def build_transitive_dependency_graph(
    client: APIClient,
    namespace: str,
    root_package_versions: List[PackageVersion],
    dependency_metadata_list: List[DependencyMetadata],
    include_transitive: bool = True,
    max_depth: Optional[int] = None,
    max_nodes: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Build a transitive dependency graph from root package versions.

    Args:
        client: Authenticated APIClient instance
        namespace: Target namespace
        root_package_versions: List of root PackageVersions to start from
        dependency_metadata_list: List of DependencyMetadata entries
        include_transitive: Whether to include transitive dependencies
        max_depth: Maximum depth to traverse (None = unlimited)
        max_nodes: Maximum number of nodes to include (None = unlimited)

    Returns:
        Dictionary with:
        - 'nodes': List of PackageVersions in the graph
        - 'edges': List of (from_uuid, to_uuid) dependency edges
        - 'metadata_map': Dict mapping importer_uuid -> List[DependencyMetadata]
    """
    logger.info(
        f"Building dependency graph from {len(root_package_versions)} root packages"
    )

    # Build a map of importer -> dependencies from DependencyMetadata
    metadata_map: Dict[str, List[DependencyMetadata]] = {}
    dependency_uuid_to_metadata: Dict[str, DependencyMetadata] = {}

    for dep_meta in dependency_metadata_list:
        if dep_meta.spec and dep_meta.spec.importer_data:
            importer_uuid = dep_meta.spec.importer_data.package_version_uuid
            if importer_uuid not in metadata_map:
                metadata_map[importer_uuid] = []
            metadata_map[importer_uuid].append(dep_meta)

            if dep_meta.spec and dep_meta.spec.dependency_data:
                dep_uuid = dep_meta.spec.dependency_data.package_version_uuid
                dependency_uuid_to_metadata[dep_uuid] = dep_meta

    # Collect all PackageVersions we've seen
    seen_package_uuids: Set[str] = set()
    package_versions_map: Dict[str, PackageVersion] = {}
    edges: List[Tuple[str, str]] = []

    # Add root packages
    for root_pkg in root_package_versions:
        seen_package_uuids.add(root_pkg.uuid)
        package_versions_map[root_pkg.uuid] = root_pkg

    def traverse_dependencies(
        importer_uuid: str, current_depth: int = 0
    ) -> None:
        """Recursively traverse dependencies."""
        # Check depth limit
        if max_depth is not None and current_depth >= max_depth:
            return

        # Check node limit
        if max_nodes is not None and len(seen_package_uuids) >= max_nodes:
            return

        # Get dependencies for this importer
        if importer_uuid not in metadata_map:
            return

        for dep_meta in metadata_map[importer_uuid]:
            if not dep_meta.spec or not dep_meta.spec.dependency_data:
                continue

            dep_uuid = dep_meta.spec.dependency_data.package_version_uuid

            # Add edge
            edges.append((importer_uuid, dep_uuid))

            # If we haven't seen this dependency yet, fetch it and recurse
            if dep_uuid not in seen_package_uuids:
                seen_package_uuids.add(dep_uuid)

                # Try to get the PackageVersion
                try:
                    dep_pkg = package_version.get_package_version(
                        client, namespace, dep_uuid
                    )
                    if dep_pkg:
                        package_versions_map[dep_uuid] = dep_pkg

                        # Recurse if including transitive
                        if include_transitive:
                            traverse_dependencies(dep_uuid, current_depth + 1)
                    else:
                        logger.debug(
                            f"Could not fetch PackageVersion: {dep_uuid}"
                        )
                except Exception as e:
                    logger.debug(
                        f"Error fetching PackageVersion {dep_uuid}: {e}"
                    )

    # Traverse from each root package
    for root_pkg in root_package_versions:
        if include_transitive:
            traverse_dependencies(root_pkg.uuid, 0)
        else:
            # Just add direct dependencies
            if root_pkg.uuid in metadata_map:
                for dep_meta in metadata_map[root_pkg.uuid]:
                    if dep_meta.spec and dep_meta.spec.dependency_data:
                        dep_uuid = dep_meta.spec.dependency_data.package_version_uuid
                        edges.append((root_pkg.uuid, dep_uuid))
                        if dep_uuid not in seen_package_uuids:
                            seen_package_uuids.add(dep_uuid)
                            try:
                                dep_pkg = package_version.get_package_version(
                                    client, namespace, dep_uuid
                                )
                                if dep_pkg:
                                    package_versions_map[dep_uuid] = dep_pkg
                            except Exception as e:
                                logger.debug(f"Error fetching PackageVersion {dep_uuid}: {e}")

    logger.info(
        f"Built dependency graph: {len(package_versions_map)} nodes, "
        f"{len(edges)} edges"
    )

    return {
        "nodes": list(package_versions_map.values()),
        "edges": edges,
        "metadata_map": metadata_map,
    }


class ProjectGraphBuilder:
    """Builds NetworkX graphs for project-centric visualizations."""

    def __init__(self, client: APIClient, namespace: str):
        self.client = client
        self.namespace = namespace

    def build_graph(
        self,
        resources: Dict[str, Any],
        include_transitive: bool = True,
        max_depth: Optional[int] = None,
        max_nodes: Optional[int] = None,
        group_by_severity: bool = False,
        group_by_ecosystem: bool = False,
        show_dependency_metadata: bool = False,
    ) -> nx.DiGraph:
        """
        Build a NetworkX graph for project-centric visualization.

        Args:
            resources: Dictionary from collect_project_resources()
            include_transitive: Include transitive dependencies
            max_depth: Maximum dependency depth
            max_nodes: Maximum number of nodes
            group_by_severity: Group findings by severity
            group_by_ecosystem: Group packages by ecosystem
            show_dependency_metadata: Include DependencyMetadata nodes

        Returns:
            NetworkX directed graph
        """
        G = nx.DiGraph()
        project_obj = resources["project"]

        # Add project node (central node)
        project_node_id = f"project:{project_obj.uuid}"
        G.add_node(
            project_node_id,
            node_type="project",
            display_name=project_obj.meta.name if project_obj.meta else "Project",
            uuid=project_obj.uuid,
            resource=project_obj,
        )

        # Build dependency graph
        dep_graph = build_transitive_dependency_graph(
            self.client,
            self.namespace,
            resources["package_versions"],
            resources["dependency_metadata"],
            include_transitive=include_transitive,
            max_depth=max_depth,
            max_nodes=max_nodes,
        )

        # Add package version nodes
        for pkg_version in dep_graph["nodes"]:
            pkg_node_id = f"package:{pkg_version.uuid}"
            pkg_name = (
                pkg_version.meta.name
                if pkg_version.meta
                else f"{pkg_version.spec.package_name if pkg_version.spec else 'Unknown'}"
            )
            ecosystem = (
                pkg_version.spec.ecosystem.value
                if pkg_version.spec
                and pkg_version.spec.ecosystem
                else "UNKNOWN"
            )
            G.add_node(
                pkg_node_id,
                node_type="package_version",
                display_name=pkg_name[:50],  # Truncate long names
                uuid=pkg_version.uuid,
                ecosystem=ecosystem,
                resource=pkg_version,
            )
            # Connect to project
            G.add_edge(
                project_node_id,
                pkg_node_id,
                edge_type="belongs_to",
            )

        # Add dependency edges
        for from_uuid, to_uuid in dep_graph["edges"]:
            from_node = f"package:{from_uuid}"
            to_node = f"package:{to_uuid}"
            if from_node in G and to_node in G:
                G.add_edge(from_node, to_node, edge_type="depends_on")

        # Add finding nodes
        findings_by_severity: Dict[str, List[Finding]] = {}
        for finding_obj in resources["findings"]:
            severity = (
                finding_obj.spec.level.value
                if finding_obj.spec and finding_obj.spec.level
                else "UNKNOWN"
            )
            if severity not in findings_by_severity:
                findings_by_severity[severity] = []
            findings_by_severity[severity].append(finding_obj)

        for finding_obj in resources["findings"]:
            finding_node_id = f"finding:{finding_obj.uuid}"
            finding_name = (
                finding_obj.meta.name
                if finding_obj.meta
                else "Finding"
            )
            severity = (
                finding_obj.spec.level.value
                if finding_obj.spec and finding_obj.spec.level
                else "UNKNOWN"
            )
            G.add_node(
                finding_node_id,
                node_type="finding",
                display_name=finding_name[:50],
                uuid=finding_obj.uuid,
                severity=severity,
                resource=finding_obj,
            )
            # Connect to project
            G.add_edge(
                project_node_id,
                finding_node_id,
                edge_type="belongs_to",
            )

            # Connect to target resource if available
            if finding_obj.spec and finding_obj.spec.target_uuid:
                target_uuid = finding_obj.spec.target_uuid
                # Check if target is a package version we have
                target_node = f"package:{target_uuid}"
                if target_node in G:
                    G.add_edge(
                        finding_node_id,
                        target_node,
                        edge_type="targets",
                    )

        # Add repository node
        if resources["repository"]:
            repo_obj = resources["repository"]
            repo_node_id = f"repository:{repo_obj.uuid}"
            repo_name = (
                repo_obj.meta.name
                if repo_obj.meta
                else "Repository"
            )
            G.add_node(
                repo_node_id,
                node_type="repository",
                display_name=repo_name[:50],
                uuid=repo_obj.uuid,
                resource=repo_obj,
            )
            # Connect to project
            G.add_edge(
                project_node_id,
                repo_node_id,
                edge_type="belongs_to",
            )

        # Add repository version nodes
        for repo_version in resources["repository_versions"]:
            repo_ver_node_id = f"repo_version:{repo_version.uuid}"
            repo_ver_name = (
                repo_version.meta.name
                if repo_version.meta
                else "RepositoryVersion"
            )
            G.add_node(
                repo_ver_node_id,
                node_type="repository_version",
                display_name=repo_ver_name[:50],
                uuid=repo_version.uuid,
                resource=repo_version,
            )
            # Connect to project
            G.add_edge(
                project_node_id,
                repo_ver_node_id,
                edge_type="belongs_to",
            )

        # Add dependency metadata nodes if requested
        if show_dependency_metadata:
            for dep_meta in resources["dependency_metadata"]:
                dep_meta_node_id = f"dep_meta:{dep_meta.uuid}"
                G.add_node(
                    dep_meta_node_id,
                    node_type="dependency_metadata",
                    display_name="DepMeta",
                    uuid=dep_meta.uuid,
                    resource=dep_meta,
                )
                # Connect to importer and dependency
                if dep_meta.spec and dep_meta.spec.importer_data:
                    importer_uuid = dep_meta.spec.importer_data.package_version_uuid
                    importer_node = f"package:{importer_uuid}"
                    if importer_node in G:
                        G.add_edge(
                            importer_node,
                            dep_meta_node_id,
                            edge_type="has_metadata",
                        )
                if dep_meta.spec and dep_meta.spec.dependency_data:
                    dep_uuid = dep_meta.spec.dependency_data.package_version_uuid
                    dep_node = f"package:{dep_uuid}"
                    if dep_node in G:
                        G.add_edge(
                            dep_meta_node_id,
                            dep_node,
                            edge_type="references",
                        )

        logger.info(
            f"Built project graph: {len(G.nodes())} nodes, {len(G.edges())} edges"
        )
        return G


class FindingGraphBuilder:
    """Builds NetworkX graphs for finding-centric visualizations."""

    def __init__(self, client: APIClient, namespace: str):
        self.client = client
        self.namespace = namespace

    def build_graph(
        self,
        resources: Dict[str, Any],
        include_transitive: bool = True,
        max_depth: Optional[int] = None,
        max_nodes: Optional[int] = None,
    ) -> nx.DiGraph:
        """
        Build a NetworkX graph for finding-centric visualization.

        Args:
            resources: Dictionary from collect_finding_resources()
            include_transitive: Include transitive dependencies
            max_depth: Maximum dependency depth
            max_nodes: Maximum number of nodes

        Returns:
            NetworkX directed graph
        """
        G = nx.DiGraph()
        finding_obj = resources["finding"]

        # Add finding node (central node)
        finding_node_id = f"finding:{finding_obj.uuid}"
        finding_name = (
            finding_obj.meta.name
            if finding_obj.meta
            else "Finding"
        )
        severity = (
            finding_obj.spec.level.value
            if finding_obj.spec and finding_obj.spec.level
            else "UNKNOWN"
        )
        G.add_node(
            finding_node_id,
            node_type="finding",
            display_name=finding_name[:50],
            uuid=finding_obj.uuid,
            severity=severity,
            resource=finding_obj,
        )

        # Add project node
        if resources["project"]:
            project_obj = resources["project"]
            project_node_id = f"project:{project_obj.uuid}"
            G.add_node(
                project_node_id,
                node_type="project",
                display_name=(
                    project_obj.meta.name
                    if project_obj.meta
                    else "Project"
                ),
                uuid=project_obj.uuid,
                resource=project_obj,
            )
            # Connect finding to project
            G.add_edge(
                finding_node_id,
                project_node_id,
                edge_type="belongs_to",
            )

        # Add target resource node
        if resources["target_resource"]:
            target_info = resources["target_resource"]
            target_type = target_info["type"]
            target_obj = target_info["resource"]
            target_node_id = f"{target_type.lower()}:{target_obj.uuid}"
            target_name = (
                target_obj.meta.name
                if target_obj.meta
                else target_type
            )
            G.add_node(
                target_node_id,
                node_type=target_type.lower(),
                display_name=target_name[:50],
                uuid=target_obj.uuid,
                resource=target_obj,
            )
            # Connect finding to target
            G.add_edge(
                finding_node_id,
                target_node_id,
                edge_type="targets",
            )

        # Add dependency package and transitive dependencies
        if resources["dependency_package"]:
            dep_pkg = resources["dependency_package"]
            dep_node_id = f"package:{dep_pkg.uuid}"
            dep_name = (
                dep_pkg.meta.name
                if dep_pkg.meta
                else f"{dep_pkg.spec.package_name if dep_pkg.spec else 'Unknown'}"
            )
            G.add_node(
                dep_node_id,
                node_type="package_version",
                display_name=dep_name[:50],
                uuid=dep_pkg.uuid,
                ecosystem=(
                    dep_pkg.spec.ecosystem.value
                    if dep_pkg.spec and dep_pkg.spec.ecosystem
                    else "UNKNOWN"
                ),
                resource=dep_pkg,
            )
            # Connect finding to dependency package
            G.add_edge(
                finding_node_id,
                dep_node_id,
                edge_type="introduced_by",
            )

            # Build transitive dependency graph from this package
            if include_transitive:
                # Get dependency metadata for this package
                try:
                    deps_params = ListParameters(
                        filter=f'meta.parent_uuid=="{dep_pkg.uuid}"',
                    )
                    dep_metadata = dependency_metadata.list_dependency_metadata(
                        self.client, self.namespace, deps_params
                    )
                    dep_graph = build_transitive_dependency_graph(
                        self.client,
                        self.namespace,
                        [dep_pkg],
                        dep_metadata,
                        include_transitive=include_transitive,
                        max_depth=max_depth,
                        max_nodes=max_nodes,
                    )

                    # Add dependency nodes and edges
                    for pkg_version in dep_graph["nodes"]:
                        if pkg_version.uuid == dep_pkg.uuid:
                            continue  # Already added
                        pkg_node_id = f"package:{pkg_version.uuid}"
                        pkg_name = (
                            pkg_version.meta.name
                            if pkg_version.meta
                            else f"{pkg_version.spec.package_name if pkg_version.spec else 'Unknown'}"
                        )
                        G.add_node(
                            pkg_node_id,
                            node_type="package_version",
                            display_name=pkg_name[:50],
                            uuid=pkg_version.uuid,
                            ecosystem=(
                                pkg_version.spec.ecosystem.value
                                if pkg_version.spec
                                and pkg_version.spec.ecosystem
                                else "UNKNOWN"
                            ),
                            resource=pkg_version,
                        )

                    # Add dependency edges
                    for from_uuid, to_uuid in dep_graph["edges"]:
                        from_node = f"package:{from_uuid}"
                        to_node = f"package:{to_uuid}"
                        if from_node in G and to_node in G:
                            G.add_edge(from_node, to_node, edge_type="depends_on")
                except Exception as e:
                    logger.warning(f"Error building transitive dependencies: {e}")

        logger.info(
            f"Built finding graph: {len(G.nodes())} nodes, {len(G.edges())} edges"
        )
        return G


def create_resource_layout(
    G: nx.DiGraph, central_node: str, layout_type: str = "hierarchical"
) -> Dict[str, Tuple[float, float]]:
    """
    Create a custom layout for resource relationship graphs.

    Args:
        G: NetworkX directed graph
        central_node: Node ID of the central resource (project or finding)
        layout_type: Layout algorithm ("hierarchical", "spring", "circular")

    Returns:
        Dictionary mapping node names to (x, y) positions
    """
    if layout_type == "hierarchical":
        # Use hierarchical layout with central node at top
        try:
            pos = nx.nx_agraph.graphviz_layout(G, prog="dot")
            return pos
        except Exception:
            logger.warning("Graphviz not available, using spring layout")
            layout_type = "spring"

    if layout_type == "spring":
        # Use spring layout with central node fixed
        pos = nx.spring_layout(G, k=2, iterations=100, seed=42)
        if central_node in pos:
            # Center the central node
            pos[central_node] = (0.0, 0.0)
        return pos

    if layout_type == "circular":
        pos = nx.circular_layout(G)
        if central_node in pos:
            pos[central_node] = (0.0, 0.0)
        return pos

    # Default to spring
    return nx.spring_layout(G, k=2, iterations=100, seed=42)


def get_severity_color(severity: str) -> str:
    """Get color for finding severity."""
    severity_colors = {
        "CRITICAL": "#FF0000",  # Red
        "HIGH": "#FF8800",  # Orange
        "MEDIUM": "#FFDD00",  # Yellow
        "LOW": "#00AA00",  # Green
        "INFO": "#0088FF",  # Blue
    }
    return severity_colors.get(severity.upper(), "#888888")  # Gray default


def get_ecosystem_color(ecosystem: str) -> str:
    """Get color for package ecosystem."""
    ecosystem_colors = {
        "ECOSYSTEM_PYPI": "#3776AB",  # Python blue
        "ECOSYSTEM_NPM": "#CB3837",  # NPM red
        "ECOSYSTEM_MAVEN": "#C71A36",  # Maven red
        "ECOSYSTEM_GO": "#00ADD8",  # Go blue
        "ECOSYSTEM_RUST": "#000000",  # Rust black
        "ECOSYSTEM_NUGET": "#004880",  # NuGet blue
        "ECOSYSTEM_GEM": "#E9572F",  # Ruby gem red
    }
    return ecosystem_colors.get(ecosystem.upper(), "#888888")  # Gray default


def visualize_resource_graph(
    G: nx.DiGraph,
    output_file: str,
    title: str,
    figsize: Tuple[int, int] = (20, 16),
    layout_type: str = "hierarchical",
) -> None:
    """
    Visualize a resource relationship graph with matplotlib.

    Args:
        G: NetworkX directed graph
        output_file: Output file path
        title: Graph title
        figsize: Figure size (width, height)
        layout_type: Layout algorithm
    """
    logger.info(
        f"Visualizing graph with {len(G.nodes())} nodes and {len(G.edges())} edges"
    )

    # Find central node (project or finding)
    central_node = None
    for node in G.nodes():
        node_type = G.nodes[node].get("node_type", "")
        if node_type in ["project", "finding"]:
            central_node = node
            break

    if not central_node:
        # Use first node as fallback
        central_node = list(G.nodes())[0] if G.nodes() else None

    # Create layout
    if central_node:
        pos = create_resource_layout(G, central_node, layout_type)
    else:
        pos = nx.spring_layout(G, k=2, iterations=100, seed=42)

    # Create figure
    fig, ax = plt.subplots(figsize=figsize)

    # Separate nodes by type
    project_nodes = [
        n for n, d in G.nodes(data=True) if d.get("node_type") == "project"
    ]
    finding_nodes = [
        n for n, d in G.nodes(data=True) if d.get("node_type") == "finding"
    ]
    package_nodes = [
        n for n, d in G.nodes(data=True) if d.get("node_type") == "package_version"
    ]
    repository_nodes = [
        n for n, d in G.nodes(data=True) if d.get("node_type") == "repository"
    ]
    repo_version_nodes = [
        n
        for n, d in G.nodes(data=True)
        if d.get("node_type") == "repository_version"
    ]
    dep_meta_nodes = [
        n
        for n, d in G.nodes(data=True)
        if d.get("node_type") == "dependency_metadata"
    ]

    # Separate edges by type
    belongs_to_edges = [
        (u, v) for u, v, d in G.edges(data=True) if d.get("edge_type") == "belongs_to"
    ]
    depends_on_edges = [
        (u, v) for u, v, d in G.edges(data=True) if d.get("edge_type") == "depends_on"
    ]
    targets_edges = [
        (u, v) for u, v, d in G.edges(data=True) if d.get("edge_type") == "targets"
    ]
    introduced_by_edges = [
        (u, v)
        for u, v, d in G.edges(data=True)
        if d.get("edge_type") == "introduced_by"
    ]
    has_metadata_edges = [
        (u, v)
        for u, v, d in G.edges(data=True)
        if d.get("edge_type") == "has_metadata"
    ]
    references_edges = [
        (u, v)
        for u, v, d in G.edges(data=True)
        if d.get("edge_type") == "references"
    ]

    # Draw edges (order matters for layering)
    # Draw dependency edges first (background)
    if depends_on_edges:
        nx.draw_networkx_edges(
            G,
            pos,
            edgelist=depends_on_edges,
            edge_color="lightgray",
            alpha=0.4,
            arrows=True,
            arrowsize=10,
            arrowstyle="-|>",
            width=1,
            style="dashed",
            ax=ax,
        )

    # Draw belongs_to edges
    if belongs_to_edges:
        nx.draw_networkx_edges(
            G,
            pos,
            edgelist=belongs_to_edges,
            edge_color="blue",
            alpha=0.5,
            arrows=True,
            arrowsize=12,
            arrowstyle="-|>",
            width=1.5,
            ax=ax,
        )

    # Draw targets edges (thick)
    if targets_edges:
        nx.draw_networkx_edges(
            G,
            pos,
            edgelist=targets_edges,
            edge_color="darkblue",
            alpha=0.7,
            arrows=True,
            arrowsize=15,
            arrowstyle="-|>",
            width=3,
            ax=ax,
        )

    # Draw introduced_by edges (red dashed)
    if introduced_by_edges:
        nx.draw_networkx_edges(
            G,
            pos,
            edgelist=introduced_by_edges,
            edge_color="red",
            alpha=0.6,
            arrows=True,
            arrowsize=12,
            arrowstyle="-|>",
            width=2,
            style="dashed",
            ax=ax,
        )

    # Draw metadata edges
    if has_metadata_edges or references_edges:
        nx.draw_networkx_edges(
            G,
            pos,
            edgelist=has_metadata_edges + references_edges,
            edge_color="purple",
            alpha=0.3,
            arrows=True,
            arrowsize=8,
            arrowstyle="-|>",
            width=1,
            style="dotted",
            ax=ax,
        )

    # Draw project nodes (large rectangle, blue)
    if project_nodes:
        nx.draw_networkx_nodes(
            G,
            pos,
            nodelist=project_nodes,
            node_color="darkblue",
            node_size=3000,
            node_shape="s",
            alpha=0.9,
            ax=ax,
        )
        labels_project = {
            n: G.nodes[n].get("display_name", n)[:30] for n in project_nodes
        }
        nx.draw_networkx_labels(
            G, pos, labels_project, font_size=10, font_weight="bold", ax=ax
        )

    # Draw finding nodes (diamond, color by severity)
    if finding_nodes:
        for finding_node in finding_nodes:
            severity = G.nodes[finding_node].get("severity", "UNKNOWN")
            color = get_severity_color(severity)
            nx.draw_networkx_nodes(
                G,
                pos,
                nodelist=[finding_node],
                node_color=color,
                node_size=2000,
                node_shape="d",
                alpha=0.8,
                ax=ax,
            )
        labels_finding = {
            n: G.nodes[n].get("display_name", n)[:30] for n in finding_nodes
        }
        nx.draw_networkx_labels(
            G, pos, labels_finding, font_size=8, font_color="black", ax=ax
        )

    # Draw package nodes (circle, color by ecosystem)
    if package_nodes:
        # Group by ecosystem for consistent coloring
        packages_by_ecosystem: Dict[str, List[str]] = {}
        for pkg_node in package_nodes:
            ecosystem = G.nodes[pkg_node].get("ecosystem", "UNKNOWN")
            if ecosystem not in packages_by_ecosystem:
                packages_by_ecosystem[ecosystem] = []
            packages_by_ecosystem[ecosystem].append(pkg_node)

        for ecosystem, nodes in packages_by_ecosystem.items():
            color = get_ecosystem_color(ecosystem)
            nx.draw_networkx_nodes(
                G,
                pos,
                nodelist=nodes,
                node_color=color,
                node_size=1200,
                node_shape="o",
                alpha=0.7,
                ax=ax,
            )

        # Draw labels for packages (only for central ones to avoid clutter)
        if len(package_nodes) <= 50:
            labels_package = {
                n: G.nodes[n].get("display_name", n)[:25] for n in package_nodes
            }
            nx.draw_networkx_labels(
                G, pos, labels_package, font_size=6, font_color="white", ax=ax
            )

    # Draw repository nodes (square, light blue)
    if repository_nodes:
        nx.draw_networkx_nodes(
            G,
            pos,
            nodelist=repository_nodes,
            node_color="lightblue",
            node_size=1500,
            node_shape="s",
            alpha=0.7,
            ax=ax,
        )
        labels_repo = {
            n: G.nodes[n].get("display_name", n)[:30] for n in repository_nodes
        }
        nx.draw_networkx_labels(
            G, pos, labels_repo, font_size=8, font_color="black", ax=ax
        )

    # Draw repository version nodes (triangle, gray)
    if repo_version_nodes:
        nx.draw_networkx_nodes(
            G,
            pos,
            nodelist=repo_version_nodes,
            node_color="gray",
            node_size=1000,
            node_shape="^",
            alpha=0.6,
            ax=ax,
        )
        labels_repo_ver = {
            n: G.nodes[n].get("display_name", n)[:25] for n in repo_version_nodes
        }
        nx.draw_networkx_labels(
            G, pos, labels_repo_ver, font_size=6, font_color="black", ax=ax
        )

    # Draw dependency metadata nodes (small circle, light gray)
    if dep_meta_nodes:
        nx.draw_networkx_nodes(
            G,
            pos,
            nodelist=dep_meta_nodes,
            node_color="lightgray",
            node_size=400,
            node_shape="o",
            alpha=0.5,
            ax=ax,
        )

    # Add legend
    legend_elements = []
    if project_nodes:
        legend_elements.append(mpatches.Patch(color="darkblue", label="Project"))
    if finding_nodes:
        legend_elements.append(
            mpatches.Patch(color="red", label="Finding (Critical)")
        )
        legend_elements.append(
            mpatches.Patch(color="orange", label="Finding (High)")
        )
    if package_nodes:
        legend_elements.append(
            mpatches.Patch(color="#3776AB", label="PackageVersion")
        )
    if repository_nodes:
        legend_elements.append(mpatches.Patch(color="lightblue", label="Repository"))
    if repo_version_nodes:
        legend_elements.append(mpatches.Patch(color="gray", label="RepositoryVersion"))

    if legend_elements:
        ax.legend(handles=legend_elements, loc="upper left", fontsize=8)

    # Set title
    ax.set_title(
        f"{title}\n({len(G.nodes())} nodes, {len(G.edges())} edges)",
        fontsize=14,
        fontweight="bold",
    )

    # Remove axes
    ax.axis("off")

    # Save figure
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches="tight")
    logger.info(f"Graph saved to: {output_file}")
    plt.close()


def main():
    """Main function to create resource relationship visualizations."""
    parser = argparse.ArgumentParser(
        description="Visualize resource relationships using NetworkX",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Project-centric view
  uv run python maneuvers/visualize_resource_relationships.py \\
    --namespace "endor-solutions-tgowan" \\
    --project-uuid "project-uuid-here" \\
    --output "project_graph.png"

  # Finding-centric view
  uv run python maneuvers/visualize_resource_relationships.py \\
    --namespace "endor-solutions-tgowan" \\
    --finding-uuid "finding-uuid-here" \\
    --output "finding_graph.png"

  # With options
  uv run python maneuvers/visualize_resource_relationships.py \\
    --namespace "tenant.namespace" \\
    --project-uuid "uuid" \\
    --include-transitive-deps \\
    --group-by-severity \\
    --output "project_graph.png"
        """,
    )

    # Resource selection (mutually exclusive)
    resource_group = parser.add_mutually_exclusive_group(required=True)
    resource_group.add_argument(
        "--project-uuid",
        help="Project UUID for project-centric visualization",
    )
    resource_group.add_argument(
        "--finding-uuid",
        help="Finding UUID for finding-centric visualization",
    )

    # Required arguments
    parser.add_argument(
        "--namespace",
        required=True,
        help="Tenant namespace (canonical name) where the resource exists",
    )
    parser.add_argument(
        "--output",
        default="resource_graph.png",
        help="Output file path for the visualization (default: resource_graph.png)",
    )

    # Optional arguments
    parser.add_argument(
        "--include-transitive-deps",
        action="store_true",
        default=True,
        help="Include full transitive dependency tree (default: True)",
    )
    parser.add_argument(
        "--max-dependency-depth",
        type=int,
        default=None,
        help="Limit dependency depth (default: unlimited)",
    )
    parser.add_argument(
        "--group-by-severity",
        action="store_true",
        help="Group findings by severity (project view only)",
    )
    parser.add_argument(
        "--group-by-ecosystem",
        action="store_true",
        help="Group packages by ecosystem (project view only)",
    )
    parser.add_argument(
        "--show-dependency-metadata",
        action="store_true",
        help="Include DependencyMetadata nodes in visualization",
    )
    parser.add_argument(
        "--max-nodes",
        type=int,
        default=None,
        help="Maximum number of nodes to include (prevents overwhelming graphs)",
    )
    parser.add_argument(
        "--width",
        type=int,
        default=20,
        help="Figure width in inches (default: 20)",
    )
    parser.add_argument(
        "--height",
        type=int,
        default=16,
        help="Figure height in inches (default: 16)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    # Set up logging
    setup_logging()
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        # Initialize API client
        logger.info("Initializing API client...")
        try:
            client = APIClient()
        except Exception as e:
            logger.error(
                f"Failed to initialize API client: {e}\n"
                "Please ensure ENDOR_API, ENDOR_API_CREDENTIALS_KEY, "
                "and ENDOR_API_CREDENTIALS_SECRET are set."
            )
            sys.exit(1)

        # Validate namespace format (basic check)
        if not args.namespace or "." not in args.namespace:
            logger.warning(
                f"Namespace '{args.namespace}' may not be in canonical format "
                "(expected: tenant.namespace)"
            )

        # Determine visualization mode
        if args.project_uuid:
            logger.info(
                f"Creating project-centric visualization for: {args.project_uuid}"
            )

            # Validate project UUID format (basic check)
            if len(args.project_uuid) < 20:
                logger.warning(
                    f"Project UUID '{args.project_uuid}' seems unusually short. "
                    "Please verify it's correct."
                )

            # Collect project resources
            try:
                resources = collect_project_resources(
                    client, args.namespace, args.project_uuid
                )
            except ValueError as e:
                logger.error(
                    f"Error collecting project resources: {e}\n"
                    f"Project UUID: {args.project_uuid}\n"
                    f"Namespace: {args.namespace}"
                )
                sys.exit(1)
            except Exception as e:
                logger.error(
                    f"Unexpected error collecting resources: {e}", exc_info=True
                )
                sys.exit(1)

            # Validate we got the project
            if not resources.get("project"):
                logger.error(f"Project {args.project_uuid} not found")
                sys.exit(1)

            # Build graph
            graph_builder = ProjectGraphBuilder(client, args.namespace)
            try:
                G = graph_builder.build_graph(
                    resources,
                    include_transitive=args.include_transitive_deps,
                    max_depth=args.max_dependency_depth,
                    max_nodes=args.max_nodes,
                    group_by_severity=args.group_by_severity,
                    group_by_ecosystem=args.group_by_ecosystem,
                    show_dependency_metadata=args.show_dependency_metadata,
                )
                if len(G.nodes()) == 0:
                    logger.warning("Graph has no nodes - project may have no resources")
                if len(G.nodes()) > 1000:
                    logger.warning(
                        f"Graph has {len(G.nodes())} nodes - visualization may be cluttered. "
                        "Consider using --max-nodes or --max-dependency-depth"
                    )
            except Exception as e:
                logger.error(f"Error building project graph: {e}", exc_info=True)
                sys.exit(1)

            # Visualize
            project_name = (
                resources["project"].meta.name
                if resources["project"].meta
                else f"Project {args.project_uuid[:8]}"
            )
            title = f"Project: {project_name}"
            try:
                visualize_resource_graph(
                    G,
                    args.output,
                    title,
                    figsize=(args.width, args.height),
                    layout_type="hierarchical",
                )
            except Exception as e:
                logger.error(f"Error visualizing graph: {e}", exc_info=True)
                sys.exit(1)

            print(f"\n✅ Project visualization saved to: {args.output}")
            print(f"   Nodes: {len(G.nodes())}, Edges: {len(G.edges())}")

        elif args.finding_uuid:
            logger.info(
                f"Creating finding-centric visualization for: {args.finding_uuid}"
            )

            # Validate finding UUID format (basic check)
            if len(args.finding_uuid) < 20:
                logger.warning(
                    f"Finding UUID '{args.finding_uuid}' seems unusually short. "
                    "Please verify it's correct."
                )

            # Collect finding resources
            try:
                resources = collect_finding_resources(
                    client, args.namespace, args.finding_uuid
                )
            except ValueError as e:
                logger.error(
                    f"Error collecting finding resources: {e}\n"
                    f"Finding UUID: {args.finding_uuid}\n"
                    f"Namespace: {args.namespace}"
                )
                sys.exit(1)
            except Exception as e:
                logger.error(
                    f"Unexpected error collecting resources: {e}", exc_info=True
                )
                sys.exit(1)

            # Validate we got the finding
            if not resources.get("finding"):
                logger.error(f"Finding {args.finding_uuid} not found")
                sys.exit(1)

            # Target resource and dependency package already resolved in collect_finding_resources
            # But we can try to enhance if needed

            # Build graph
            graph_builder = FindingGraphBuilder(client, args.namespace)
            try:
                G = graph_builder.build_graph(
                    resources,
                    include_transitive=args.include_transitive_deps,
                    max_depth=args.max_dependency_depth,
                    max_nodes=args.max_nodes,
                )
                if len(G.nodes()) == 0:
                    logger.warning("Graph has no nodes - finding may have no related resources")
                if len(G.nodes()) > 1000:
                    logger.warning(
                        f"Graph has {len(G.nodes())} nodes - visualization may be cluttered. "
                        "Consider using --max-nodes or --max-dependency-depth"
                    )
            except Exception as e:
                logger.error(f"Error building finding graph: {e}", exc_info=True)
                sys.exit(1)

            # Visualize
            finding_name = (
                resources["finding"].meta.name
                if resources["finding"].meta
                else f"Finding {args.finding_uuid[:8]}"
            )
            title = f"Finding: {finding_name}"
            try:
                visualize_resource_graph(
                    G,
                    args.output,
                    title,
                    figsize=(args.width, args.height),
                    layout_type="hierarchical",
                )
            except Exception as e:
                logger.error(f"Error visualizing graph: {e}", exc_info=True)
                sys.exit(1)

            print(f"\n✅ Finding visualization saved to: {args.output}")
            print(f"   Nodes: {len(G.nodes())}, Edges: {len(G.edges())}")

    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

