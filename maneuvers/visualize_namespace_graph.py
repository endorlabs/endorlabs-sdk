#!/usr/bin/env python3
"""
Namespace and Project Graph Visualization

A script to visualize the hierarchical structure of namespaces and their
associated projects using NetworkX and matplotlib.

This script:
1. Fetches all namespaces (including child namespaces) from the tenant
2. Fetches all projects from each namespace
3. Builds a NetworkX graph showing:
   - Namespace hierarchy (parent-child relationships)
   - Projects connected to their namespaces
4. Visualizes the graph with color-coded nodes

Requirements:
    pip install networkx matplotlib

Example:
    uv run python maneuvers/visualize_namespace_graph.py \
      --namespace "tenant.namespace" \
      --output "namespace_graph.png"
"""

import argparse
import logging
import os
import sys
from typing import Dict, List, Set, Tuple

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
from endor_cockpit.resources import namespace, project
from endor_cockpit.resources.namespace import Namespace
from endor_cockpit.resources.project import Project
from endor_cockpit.types import ListParameters
from endor_cockpit.utils.logging_config import setup_logging

logger = logging.getLogger(__name__)


def get_parent_namespace(canonical_name: str) -> str:
    """
    Extract parent namespace from canonical name.

    Args:
        canonical_name: Full namespace name (e.g., "tenant.namespace.child")

    Returns:
        Parent namespace name (e.g., "tenant.namespace") or empty string if root
    """
    parts = canonical_name.split(".")
    if len(parts) <= 1:  # Just tenant name
        return ""
    return ".".join(parts[:-1])


def get_namespace_depth(canonical_name: str, tenant_namespace: str) -> int:
    """
    Get the depth of a namespace in the hierarchy.

    Args:
        canonical_name: Full namespace name (e.g., "tenant.namespace.child")
        tenant_namespace: Root tenant namespace

    Returns:
        Depth level (0 for tenant, 1 for first level, etc.)
    """
    if canonical_name == tenant_namespace:
        return 0
    # Count dots after tenant name
    tenant_parts = tenant_namespace.split(".")
    namespace_parts = canonical_name.split(".")
    # Depth is number of additional parts beyond tenant
    return len(namespace_parts) - len(tenant_parts)


def create_hierarchical_layout(
    G: nx.DiGraph, tenant_namespace: str
) -> Dict[str, Tuple[float, float]]:
    """
    Create a hierarchical tree layout for the namespace graph.

    This layout positions nodes in levels based on their depth in the hierarchy,
    creating a clean top-down tree structure.

    Args:
        G: NetworkX directed graph
        tenant_namespace: Root tenant namespace

    Returns:
        Dictionary mapping node names to (x, y) positions
    """
    pos = {}

    # Group nodes by depth
    nodes_by_depth: Dict[int, List[str]] = {}
    max_depth = 0

    for node in G.nodes():
        node_data = G.nodes[node]
        node_type = node_data.get("node_type", "unknown")

        if node_type == "tenant":
            depth = 0
        elif node_type == "namespace":
            # Get depth from canonical name
            canonical_name = node
            depth = get_namespace_depth(canonical_name, tenant_namespace)
        else:  # project
            # Projects are at the depth of their namespace + 1
            namespace = node_data.get("namespace", tenant_namespace)
            depth = get_namespace_depth(namespace, tenant_namespace) + 1

        if depth not in nodes_by_depth:
            nodes_by_depth[depth] = []
        nodes_by_depth[depth].append(node)
        max_depth = max(max_depth, depth)

    # Position nodes at each depth level, organizing children under parents
    # First, position tenant at top
    tenant_node_list = [n for n in G.nodes() if G.nodes[n].get("node_type") == "tenant"]
    if tenant_node_list:
        for node in tenant_node_list:
            pos[node] = (0.0, max_depth + 1)

    # Position namespaces level by level, organizing children under parents
    def position_children(parent_name: str, parent_x: float, depth: int) -> None:
        """Recursively position children under their parent."""
        # Find all children of this parent
        children = []
        for node in G.nodes():
            if node == parent_name:
                continue
            node_data = G.nodes[node]
            if node_data.get("node_type") == "namespace":
                canonical_name = node
                parent = get_parent_namespace(canonical_name)
                if parent == parent_name:
                    children.append(node)

        if not children:
            return

        y_pos = max_depth - depth
        num_children = len(children)
        sorted_children = sorted(children)

        if num_children == 1:
            # Single child: position directly under parent
            child_x = parent_x
            pos[sorted_children[0]] = (child_x, y_pos)
            position_children(sorted_children[0], child_x, depth + 1)
        else:
            # Multiple children: spread them horizontally
            spacing = min(2.0 / max(num_children - 1, 1), 1.5)
            start_x = parent_x - (spacing * (num_children - 1)) / 2

            for i, child in enumerate(sorted_children):
                child_x = start_x + i * spacing
                pos[child] = (child_x, y_pos)
                position_children(child, child_x, depth + 1)

    # Start positioning from root level (depth 1)
    root_namespaces = []
    for node in G.nodes():
        node_data = G.nodes[node]
        if node_data.get("node_type") == "namespace":
            canonical_name = node
            parent = get_parent_namespace(canonical_name)
            if parent == tenant_namespace or parent == "":
                root_namespaces.append(node)

    if root_namespaces:
        num_root = len(root_namespaces)
        sorted_root = sorted(root_namespaces)
        y_pos = max_depth

        if num_root == 1:
            pos[sorted_root[0]] = (0.0, y_pos)
            position_children(sorted_root[0], 0.0, 2)
        else:
            spacing = min(3.0 / max(num_root - 1, 1), 2.0)
            start_x = -spacing * (num_root - 1) / 2
            for i, ns in enumerate(sorted_root):
                ns_x = start_x + i * spacing
                pos[ns] = (ns_x, y_pos)
                position_children(ns, ns_x, 2)

    # Position projects under their namespaces
    for node in G.nodes():
        node_data = G.nodes[node]
        if node_data.get("node_type") == "project":
            namespace = node_data.get("namespace", tenant_namespace)
            if namespace in pos:
                ns_x, ns_y = pos[namespace]
                # Find projects at this namespace
                projects_at_ns = [
                    n
                    for n in G.nodes()
                    if G.nodes[n].get("node_type") == "project"
                    and G.nodes[n].get("namespace") == namespace
                ]
                num_projects = len(projects_at_ns)
                project_depth = get_namespace_depth(namespace, tenant_namespace) + 1
                y_pos = max_depth - project_depth

                if num_projects == 1:
                    pos[node] = (ns_x, y_pos)
                else:
                    # Spread projects horizontally
                    sorted_projects = sorted(projects_at_ns)
                    idx = sorted_projects.index(node)
                    spacing = 0.6 / max(num_projects - 1, 1)
                    start_x = ns_x - (spacing * (num_projects - 1)) / 2
                    pos[node] = (start_x + idx * spacing, y_pos)

    return pos


def build_namespace_hierarchy(
    namespaces: List[Namespace], tenant_namespace: str
) -> Dict[str, Namespace]:
    """
    Build a dictionary mapping canonical namespace names to Namespace objects.

    Uses canonical names constructed during collection (stored in _canonical_name),
    which follow dot notation: parent.namespace_name

    Args:
        namespaces: List of namespace objects (with _canonical_name attribute)
        tenant_namespace: Root tenant namespace (for fallback)

    Returns:
        Dictionary mapping canonical names to Namespace objects
    """
    namespace_map = {}

    for ns in namespaces:
        # Use pre-computed canonical name if available
        if hasattr(ns, "_canonical_name"):
            canonical_name = getattr(ns, "_canonical_name")
        else:
            # Fallback: construct from tenant_meta and meta.name
            if ns.meta and ns.meta.name:
                namespace_name = ns.meta.name
                parent = (
                    ns.tenant_meta.namespace
                    if ns.tenant_meta and ns.tenant_meta.namespace
                    else tenant_namespace
                )
                canonical_name = f"{parent}.{namespace_name}"
            elif ns.tenant_meta and ns.tenant_meta.namespace:
                canonical_name = ns.tenant_meta.namespace
            else:
                canonical_name = f"namespace-{ns.uuid[:8]}"

        namespace_map[canonical_name] = ns

    return namespace_map


def collect_all_namespaces(
    client: APIClient, tenant_namespace: str
) -> List[Namespace]:
    """
    Recursively collect all namespaces including all nested child namespaces.

    This function ensures we get all namespaces at all levels of the hierarchy,
    not just direct children. It recursively traverses each namespace to find
    its children.

    Args:
        client: Authenticated APIClient instance
        tenant_namespace: Root tenant namespace

    Returns:
        List of all namespaces at all levels
    """
    logger.info(f"Recursively collecting namespaces from: {tenant_namespace}")
    all_namespaces: List[Namespace] = []
    namespace_canonical_names: Dict[str, str] = {}  # UUID -> canonical name
    seen_namespace_uuids: Set[str] = set()
    processed_parents: Set[str] = set()

    def collect_recursive(parent_ns: str) -> None:
        """Recursively collect namespaces starting from parent_ns."""
        # Check if we've already processed this parent to avoid infinite loops
        if parent_ns in processed_parents:
            return
        processed_parents.add(parent_ns)

        try:
            # List direct children of this namespace
            list_params = ListParameters(traverse=False)
            child_namespaces = namespace.list_namespaces(
                client, parent_ns, list_params
            )

            for ns in child_namespaces:
                # Track by UUID to avoid duplicates
                if ns.uuid in seen_namespace_uuids:
                    continue
                seen_namespace_uuids.add(ns.uuid)

                # Construct canonical name using dot notation: parent.namespace_name
                if ns.meta and ns.meta.name:
                    namespace_name = ns.meta.name
                    # Build canonical name: parent.namespace_name
                    canonical_name = f"{parent_ns}.{namespace_name}"
                else:
                    # Fallback: use tenant_meta.namespace if available
                    if ns.tenant_meta and ns.tenant_meta.namespace:
                        canonical_name = ns.tenant_meta.namespace
                    else:
                        logger.warning(
                            f"Namespace {ns.uuid} has no name or tenant_meta, "
                            "using UUID as identifier"
                        )
                        canonical_name = f"namespace-{ns.uuid[:8]}"

                # Store canonical name mapping
                namespace_canonical_names[ns.uuid] = canonical_name
                all_namespaces.append(ns)
                logger.debug(
                    f"Collected namespace: {canonical_name} "
                    f"(UUID: {ns.uuid}, name: {ns.meta.name if ns.meta else 'N/A'})"
                )

                # Recursively collect children of this namespace using canonical name
                collect_recursive(canonical_name)

        except Exception as e:
            logger.warning(
                f"Error collecting namespaces from {parent_ns}: {e}"
            )

    # Start recursive collection from the root tenant namespace
    collect_recursive(tenant_namespace)

    logger.info(f"Found {len(all_namespaces)} namespaces (all levels)")
    # Store canonical names as an attribute on namespaces for later use
    for ns in all_namespaces:
        if ns.uuid in namespace_canonical_names:
            # Store canonical name in a way we can access it later
            # We'll use this in build_namespace_hierarchy
            setattr(ns, "_canonical_name", namespace_canonical_names[ns.uuid])

    return all_namespaces


def collect_projects_by_namespace(
    client: APIClient, namespace_map: Dict[str, Namespace]
) -> Dict[str, List[Project]]:
    """
    Collect all projects grouped by their namespace.

    Args:
        client: Authenticated APIClient instance
        namespace_map: Dictionary mapping namespace names to Namespace objects

    Returns:
        Dictionary mapping namespace names to lists of projects
    """
    projects_by_namespace: Dict[str, List[Project]] = {}
    total_projects = 0

    for ns_name, ns_obj in namespace_map.items():
        try:
            logger.debug(f"Collecting projects from namespace: {ns_name}")
            projects_list = project.list_projects(client, ns_name)
            if projects_list:
                projects_by_namespace[ns_name] = projects_list
                total_projects += len(projects_list)
                logger.debug(
                    f"  Found {len(projects_list)} projects in {ns_name}"
                )
        except Exception as e:
            logger.warning(f"Error collecting projects from {ns_name}: {e}")

    logger.info(f"Found {total_projects} total projects across all namespaces")
    return projects_by_namespace


def build_graph(
    namespace_map: Dict[str, Namespace],
    projects_by_namespace: Dict[str, List[Project]],
    tenant_namespace: str,
) -> nx.DiGraph:
    """
    Build a NetworkX directed graph of namespaces and projects.

    Args:
        namespace_map: Dictionary mapping namespace names to Namespace objects
        projects_by_namespace: Dictionary mapping namespace names to project lists
        tenant_namespace: Root tenant namespace

    Returns:
        NetworkX directed graph
    """
    G = nx.DiGraph()

    # Add namespace nodes
    for ns_name, ns_obj in namespace_map.items():
        display_name = ns_obj.meta.name if ns_obj.meta else ns_name.split(".")[-1]
        G.add_node(
            ns_name,
            node_type="namespace",
            display_name=display_name,
            uuid=ns_obj.uuid,
            description=ns_obj.meta.description if ns_obj.meta else "",
        )

    # Add namespace hierarchy edges (parent-child relationships)
    for ns_name in namespace_map.keys():
        parent = get_parent_namespace(ns_name)
        if parent and parent in namespace_map:
            G.add_edge(parent, ns_name, edge_type="namespace_hierarchy")
        elif not parent:
            # Root namespace - connect to tenant if it's not already a node
            if tenant_namespace not in G:
                G.add_node(
                    tenant_namespace,
                    node_type="tenant",
                    display_name=tenant_namespace.split(".")[0],
                    uuid="",
                    description="Tenant root",
                )
            G.add_edge(tenant_namespace, ns_name, edge_type="namespace_hierarchy")

    # Add project nodes and connect them to their namespaces
    for ns_name, projects_list in projects_by_namespace.items():
        for proj in projects_list:
            project_id = f"project:{proj.uuid}"
            project_name = proj.meta.name if proj.meta else f"Project {proj.uuid[:8]}"
            G.add_node(
                project_id,
                node_type="project",
                display_name=project_name,
                uuid=proj.uuid,
                namespace=ns_name,
                description=proj.meta.description if proj.meta else "",
            )
            # Connect project to its namespace
            if ns_name in G:
                G.add_edge(ns_name, project_id, edge_type="contains_project")

    return G


def visualize_graph(
    G: nx.DiGraph,
    output_file: str,
    layout: str = "hierarchical",
    figsize: Tuple[int, int] = (16, 12),
    tenant_namespace: str = "",
) -> None:
    """
    Visualize the NetworkX graph with matplotlib.

    Args:
        G: NetworkX directed graph
        output_file: Output file path for the visualization
        layout: Layout algorithm ("hierarchical", "spring", "circular")
        figsize: Figure size (width, height)
    """
    logger.info(f"Visualizing graph with {len(G.nodes())} nodes and {len(G.edges())} edges")

    # Create figure
    fig, ax = plt.subplots(figsize=figsize)

    # Choose layout
    if layout == "hierarchical":
        try:
            # Try graphviz first for best hierarchical layout
            pos = nx.nx_agraph.graphviz_layout(G, prog="dot")
        except Exception:
            logger.warning("Graphviz not available, using hierarchical tree layout")
            # Use a custom hierarchical layout based on namespace depth
            pos = create_hierarchical_layout(G, tenant_namespace)
    elif layout == "spring":
        pos = nx.spring_layout(G, k=3, iterations=100, seed=42)
    elif layout == "circular":
        pos = nx.circular_layout(G)
    else:
        pos = create_hierarchical_layout(G, tenant_namespace)

    # Separate nodes by type
    namespace_nodes = [n for n, d in G.nodes(data=True) if d.get("node_type") == "namespace"]
    tenant_nodes = [n for n, d in G.nodes(data=True) if d.get("node_type") == "tenant"]
    project_nodes = [n for n, d in G.nodes(data=True) if d.get("node_type") == "project"]

    # Draw edges
    namespace_edges = [
        (u, v) for u, v, d in G.edges(data=True) if d.get("edge_type") == "namespace_hierarchy"
    ]
    project_edges = [
        (u, v) for u, v, d in G.edges(data=True) if d.get("edge_type") == "contains_project"
    ]

    # Draw namespace hierarchy edges
    nx.draw_networkx_edges(
        G,
        pos,
        edgelist=namespace_edges,
        edge_color="gray",
        alpha=0.5,
        arrows=True,
        arrowsize=15,
        arrowstyle="-|>",
        width=2,
        ax=ax,
    )

    # Draw project edges
    nx.draw_networkx_edges(
        G,
        pos,
        edgelist=project_edges,
        edge_color="lightblue",
        alpha=0.3,
        arrows=True,
        arrowsize=10,
        arrowstyle="-|>",
        width=1,
        style="dashed",
        ax=ax,
    )

    # Draw tenant nodes
    if tenant_nodes:
        nx.draw_networkx_nodes(
            G,
            pos,
            nodelist=tenant_nodes,
            node_color="darkblue",
            node_size=2000,
            node_shape="s",
            alpha=0.8,
            ax=ax,
        )
        labels_tenant = {
            n: G.nodes[n].get("display_name", n) for n in tenant_nodes
        }
        nx.draw_networkx_labels(
            G, pos, labels_tenant, font_size=10, font_weight="bold", ax=ax
        )

    # Draw namespace nodes
    nx.draw_networkx_nodes(
        G,
        pos,
        nodelist=namespace_nodes,
        node_color="lightgreen",
        node_size=1500,
        node_shape="o",
        alpha=0.8,
        ax=ax,
    )
    labels_namespace = {
        n: G.nodes[n].get("display_name", n.split(".")[-1]) for n in namespace_nodes
    }
    nx.draw_networkx_labels(
        G, pos, labels_namespace, font_size=8, font_color="black", ax=ax
    )

    # Draw project nodes
    nx.draw_networkx_nodes(
        G,
        pos,
        nodelist=project_nodes,
        node_color="lightcoral",
        node_size=800,
        node_shape="^",
        alpha=0.7,
        ax=ax,
    )
    labels_project = {
        n: G.nodes[n].get("display_name", n)[:20] for n in project_nodes
    }
    nx.draw_networkx_labels(
        G, pos, labels_project, font_size=6, font_color="darkred", ax=ax
    )

    # Add legend
    legend_elements = [
        mpatches.Patch(color="darkblue", label="Tenant"),
        mpatches.Patch(color="lightgreen", label="Namespace"),
        mpatches.Patch(color="lightcoral", label="Project"),
    ]
    ax.legend(handles=legend_elements, loc="upper left")

    # Set title
    ax.set_title(
        f"Namespace and Project Hierarchy\n"
        f"({len(namespace_nodes)} namespaces, {len(project_nodes)} projects)",
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


def print_graph_summary(
    G: nx.DiGraph,
    namespace_map: Dict[str, Namespace],
    projects_by_namespace: Dict[str, List[Project]],
) -> None:
    """
    Print a text summary of the graph structure.

    Args:
        G: NetworkX directed graph
        namespace_map: Dictionary mapping namespace names to Namespace objects
        projects_by_namespace: Dictionary mapping namespace names to project lists
    """
    print("\n" + "=" * 80)
    print("GRAPH SUMMARY")
    print("=" * 80)
    print(f"Total nodes: {len(G.nodes())}")
    print(f"Total edges: {len(G.edges())}")
    print(f"\nNamespaces: {len(namespace_map)}")
    print(f"Projects: {sum(len(p) for p in projects_by_namespace.values())}")

    print("\n" + "-" * 80)
    print("NAMESPACE HIERARCHY")
    print("-" * 80)
    for ns_name, ns_obj in sorted(namespace_map.items()):
        display_name = ns_obj.meta.name if ns_obj.meta else ns_name.split(".")[-1]
        project_count = len(projects_by_namespace.get(ns_name, []))
        parent = get_parent_namespace(ns_name)
        indent = "  " * (len(ns_name.split(".")) - 2)
        print(f"{indent}├─ {display_name} ({ns_name})")
        if project_count > 0:
            print(f"{indent}   └─ {project_count} project(s)")

    print("\n" + "-" * 80)
    print("PROJECTS BY NAMESPACE")
    print("-" * 80)
    for ns_name, projects_list in sorted(projects_by_namespace.items()):
        display_name = (
            namespace_map[ns_name].meta.name
            if namespace_map[ns_name].meta
            else ns_name.split(".")[-1]
        )
        print(f"\n{display_name} ({ns_name}):")
        for proj in projects_list[:10]:  # Show first 10 projects
            proj_name = proj.meta.name if proj.meta else f"Project {proj.uuid[:8]}"
            print(f"  • {proj_name}")
        if len(projects_list) > 10:
            print(f"  ... and {len(projects_list) - 10} more projects")


def main():
    """Main function to create the visualization."""
    parser = argparse.ArgumentParser(
        description="Visualize namespace and project hierarchy using NetworkX",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic visualization
  uv run python maneuvers/visualize_namespace_graph.py \\
    --namespace "endor-solutions-tgowan"

  # Save to specific file
  uv run python maneuvers/visualize_namespace_graph.py \\
    --namespace "endor-solutions-tgowan" \\
    --output "my_namespace_graph.png"

  # Use different layout
  uv run python maneuvers/visualize_namespace_graph.py \\
    --namespace "endor-solutions-tgowan" \\
    --layout "spring" \\
    --output "namespace_graph_spring.png"
        """,
    )

    parser.add_argument(
        "--namespace",
        required=True,
        help="Tenant namespace (canonical name) to visualize",
    )
    parser.add_argument(
        "--output",
        default="namespace_graph.png",
        help="Output file path for the visualization (default: namespace_graph.png)",
    )
    parser.add_argument(
        "--layout",
        choices=["hierarchical", "spring", "circular"],
        default="hierarchical",
        help="Layout algorithm for graph visualization (default: hierarchical)",
    )
    parser.add_argument(
        "--width",
        type=int,
        default=16,
        help="Figure width in inches (default: 16)",
    )
    parser.add_argument(
        "--height",
        type=int,
        default=12,
        help="Figure height in inches (default: 12)",
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
        client = APIClient()

        # Collect namespaces
        logger.info("Collecting namespaces...")
        all_namespaces = collect_all_namespaces(client, args.namespace)
        if not all_namespaces:
            logger.warning(f"No namespaces found in {args.namespace}")
            print(f"No namespaces found in {args.namespace}")
            return

        # Build namespace map with proper canonical names
        namespace_map = build_namespace_hierarchy(all_namespaces, args.namespace)

        # Collect projects
        logger.info("Collecting projects...")
        projects_by_namespace = collect_projects_by_namespace(client, namespace_map)

        # Build graph
        logger.info("Building graph...")
        G = build_graph(namespace_map, projects_by_namespace, args.namespace)

        # Print summary
        print_graph_summary(G, namespace_map, projects_by_namespace)

        # Visualize
        logger.info("Creating visualization...")
        visualize_graph(
            G,
            args.output,
            layout=args.layout,
            figsize=(args.width, args.height),
            tenant_namespace=args.namespace,
        )

        print(f"\n✅ Visualization saved to: {args.output}")

    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

