<!-- e0b9a3ea-0e65-4183-9a3f-2bf1191a3d9a 4e8c435f-d220-4ef9-ad5d-0b117185d08c -->
# Wayfinder: Graph-Based Data Model Navigator

## Overview

Wayfinder is a graph-based navigation system for the Endor Labs data model. It uses NetworkX to represent resources, relationships, and definitions as an interactive graph that agents can traverse to understand the API structure and build complex workflows.

**Key Design Principles:**

- Resources (Finding, Project, etc.) are nodes
- Definitions (v1Meta, v1FindingSpec, etc.) are subgraphs
- NetworkX provides graph operations and traversal
- Agent-friendly interface for data model exploration
- Exportable to multiple visualization formats or libraries: Pyvis / Plotly / Dash

---

## Phase 1: Stash Existing Plan and Index OpenAPI Definitions

### 1.1 Move Previous Plan

Move `agent-sd.plan.md` to `.workspace/2025-10-24-agent-sdk-task-disambiguation.plan.md` for future reference.

### 1.2 Create OpenAPI Definitions Index

**Script: `scripts/index_openapi_definitions.py`**

```python
"""
Extract all definitions from OpenAPI spec and generate searchable index.
Output: docs/OPENAPI_DEFINITIONS_INDEX.md
"""

import json
from typing import Dict, List, Set
from pathlib import Path

def index_openapi_definitions(spec_path: str, output_path: str):
    """Generate markdown index of all OpenAPI definitions"""
    
    with open(spec_path) as f:
        spec = json.load(f)
    
    definitions = spec.get("definitions", {})
    
    # Build cross-reference map
    ref_usage = analyze_reference_usage(spec)
    service_usage = map_services_to_definitions(spec)
    
    # Generate markdown
    markdown = generate_index_markdown(definitions, ref_usage, service_usage)
    
    with open(output_path, 'w') as f:
        f.write(markdown)

def analyze_reference_usage(spec: dict) -> Dict[str, List[str]]:
    """Find all $ref usages across the spec"""
    # Track which definitions reference which others
    pass

def map_services_to_definitions(spec: dict) -> Dict[str, List[str]]:
    """Map services to the definitions they use"""
    # Extract from paths and tags
    pass

def generate_index_markdown(definitions, ref_usage, service_usage) -> str:
    """Generate formatted markdown index"""
    # Table of contents with anchor links
    # Full definition details per resource
    # Cross-references and relationships
    pass
```

**Output Format: `docs/OPENAPI_DEFINITIONS_INDEX.md`**

```markdown
# OpenAPI Definitions Index

Total Definitions: 546
Last Updated: 2025-10-24

## Table of Contents

- [A](#a) | [B](#b) | [C](#c) ... [Z](#z)

### A
- [AIQueryPackageData](#aiquerypackagedata)
- [AffectedSource](#affectedsource)
...

## Definitions

### v1Finding
**Type:** object
**Category:** Resource
**Used By Services:** FindingService
**References:** v1TenantMeta, v1Meta, v1FindingSpec, v1Context
**Referenced By:** FindingService (all endpoints)

**Properties:**
- `uuid` (string, readOnly): Unique identifier for the finding
- `tenant_meta` ($ref: v1TenantMeta): Namespace metadata
- `meta` ($ref: v1Meta): Resource metadata (name, tags, timestamps)
- `spec` ($ref: v1FindingSpec): Finding specification with severity, status, etc.
- `context` ($ref: v1Context): Scan context information
- `propagate` (boolean): Whether to propagate to child namespaces

**Required:** tenant_meta, meta, spec

**Related Resources:** Project, RepositoryVersion, PackageVersion
**Known Relationships:**
- parent_uuid → RepositoryVersion
- spec.target_uuid → RepositoryVersion
- spec.project_uuid → Project

---

### v1Meta
**Type:** object
**Category:** Shared Definition
**Used By Services:** All resource services
**Referenced By:** 89+ definitions

**Properties:**
- `name` (string, required): Resource name
- `kind` (string): Resource kind
- `version` (string): Resource version
- `create_time` (string, date-time, readOnly): Creation timestamp
- `update_time` (string, date-time, readOnly): Last update timestamp
- `tags` (array[string]): Resource tags
- `annotations` (object): Key-value annotations
- `description` (string): Resource description
...

**Pattern:** Universal metadata structure for all Endor Labs resources
```

---

## Phase 2: Delete Old Holocron RAG Implementation

### 2.1 Files and Directories to Delete

```
src/holocron/                     # Entire directory
tests/test_holocron_config.py
tests/test_content_types.py
tests/test_chunking_optimization.py
holocron_data/                    # Entire directory
docs/holocron/                    # Entire directory
```

### 2.2 Remove References from Documentation

Search and clean these files:

- `docs/protocols/development/troubleshooting-protocol.md`
- `docs/protocols/development/development-protocol.md`
- `docs/protocols/development/code-commit-protocol.md`
- `docs/protocols/mandatory-development-rules.md`
- `docs/protocols/mandatory-context.md`

Remove all holocron-related content, imports, and references.

### 2.3 Verification

```bash
# Ensure no remaining references
grep -r "holocron" src/ docs/ tests/ --exclude-dir=__pycache__
```

---

## Phase 3: Build Wayfinder Graph Module

### 3.1 Architecture

**Module: `src/wayfinder/`**

```
src/wayfinder/
├── __init__.py              # Exports: WayfinderGraph, build_graph, query
├── graph.py                 # Core graph implementation with NetworkX
├── builder.py               # Build graph from OpenAPI + live data
├── models.py                # Node/Edge/Subgraph models
├── exporters.py             # Export to GraphML, Cypher, DOT, JSON
├── queries.py               # Graph query utilities for agents
└── cli.py                   # Command-line interface
```

### 3.2 Core Graph Implementation (`src/wayfinder/graph.py`)

```python
"""
Core Wayfinder graph implementation using NetworkX.
Resources are nodes, Definitions are subgraphs.
"""

import networkx as nx
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
from enum import Enum

class NodeType(Enum):
    """Types of nodes in the Wayfinder graph"""
    RESOURCE = "resource"           # Finding, Project, Policy
    SERVICE = "service"             # FindingService, ProjectService
    ENDPOINT = "endpoint"           # GET /v1/.../findings
    DEFINITION = "definition"       # v1Meta, v1FindingSpec
    ATTRIBUTE = "attribute"         # spec.level, meta.tags

class EdgeType(Enum):
    """Types of edges in the Wayfinder graph"""
    OWNS = "owns"                   # Service owns Resource
    EXPOSES = "exposes"             # Service exposes Endpoint
    OPERATES_ON = "operates_on"     # Endpoint operates on Resource
    HAS_ATTRIBUTE = "has_attribute" # Resource has Attribute
    REFERENCES = "references"       # Resource references Resource
    PARENT = "parent"               # Resource has parent Resource
    USES_DEFINITION = "uses_definition" # Resource uses Definition
    PART_OF = "part_of"            # Attribute part of Definition subgraph

@dataclass
class Node:
    """Node in the Wayfinder graph"""
    id: str
    type: NodeType
    label: str
    properties: Dict[str, any]
    
    def to_networkx_attrs(self) -> Dict:
        """Convert to NetworkX node attributes"""
        return {
            "type": self.type.value,
            "label": self.label,
            **self.properties
        }

@dataclass
class Edge:
    """Edge in the Wayfinder graph"""
    source: str
    target: str
    type: EdgeType
    label: Optional[str] = None
    properties: Optional[Dict[str, any]] = None
    
    def to_networkx_attrs(self) -> Dict:
        """Convert to NetworkX edge attributes"""
        attrs = {"type": self.type.value}
        if self.label:
            attrs["label"] = self.label
        if self.properties:
            attrs.update(self.properties)
        return attrs

class WayfinderGraph:
    """
    NetworkX-based graph representing Endor Labs data model.
    
    **Agent Interface:**
    - find_resource(name): Get resource node
    - get_relationships(resource): Get all relationships for a resource
    - find_path(source, target): Find navigation path between resources
    - get_definition_subgraph(definition): Get subgraph for a definition
    - query_attributes(resource, mutable_only): Get resource attributes
    """
    
    def __init__(self):
        self.graph = nx.MultiDiGraph()  # Allow multiple edges between nodes
        self._resource_index: Dict[str, str] = {}  # name -> node_id
        self._definition_subgraphs: Dict[str, Set[str]] = {}  # definition -> node_ids
    
    def add_resource(self, node: Node) -> str:
        """Add a resource node to the graph"""
        self.graph.add_node(node.id, **node.to_networkx_attrs())
        if node.type == NodeType.RESOURCE:
            self._resource_index[node.label] = node.id
        return node.id
    
    def add_edge(self, edge: Edge):
        """Add an edge to the graph"""
        self.graph.add_edge(
            edge.source,
            edge.target,
            **edge.to_networkx_attrs()
        )
    
    def add_definition_subgraph(self, definition_name: str, nodes: List[Node]):
        """Add a definition as a subgraph"""
        node_ids = set()
        for node in nodes:
            node_id = self.add_resource(node)
            node_ids.add(node_id)
        self._definition_subgraphs[definition_name] = node_ids
    
    # Agent-friendly query methods
    
    def find_resource(self, name: str) -> Optional[Dict]:
        """Find a resource node by name"""
        node_id = self._resource_index.get(name)
        if node_id:
            return {"id": node_id, **self.graph.nodes[node_id]}
        return None
    
    def get_relationships(
        self, 
        resource: str, 
        edge_type: Optional[EdgeType] = None
    ) -> List[Dict]:
        """
        Get all relationships for a resource.
        
        Example:
            finding_rels = graph.get_relationships("Finding")
            # Returns: [
            #   {"type": "references", "target": "RepositoryVersion", "via": "spec.target_uuid"},
            #   {"type": "references", "target": "Project", "via": "spec.project_uuid"}
            # ]
        """
        node_id = self._resource_index.get(resource)
        if not node_id:
            return []
        
        relationships = []
        for _, target, data in self.graph.out_edges(node_id, data=True):
            if edge_type is None or data.get("type") == edge_type.value:
                target_node = self.graph.nodes[target]
                relationships.append({
                    "type": data.get("type"),
                    "target": target_node.get("label"),
                    "target_id": target,
                    **{k: v for k, v in data.items() if k not in ["type"]}
                })
        
        return relationships
    
    def find_path(self, source: str, target: str) -> Optional[List[str]]:
        """
        Find navigation path between resources.
        
        Example:
            path = graph.find_path("Finding", "Project")
            # Returns: ["Finding", "RepositoryVersion", "Project"]
        """
        source_id = self._resource_index.get(source)
        target_id = self._resource_index.get(target)
        
        if not source_id or not target_id:
            return None
        
        try:
            path_ids = nx.shortest_path(self.graph, source_id, target_id)
            return [self.graph.nodes[nid]["label"] for nid in path_ids]
        except nx.NetworkXNoPath:
            return None
    
    def get_definition_subgraph(self, definition: str) -> nx.DiGraph:
        """
        Get subgraph for a definition.
        
        Example:
            meta_subgraph = graph.get_definition_subgraph("v1Meta")
            # Returns NetworkX subgraph with all v1Meta attributes
        """
        node_ids = self._definition_subgraphs.get(definition, set())
        return self.graph.subgraph(node_ids)
    
    def query_attributes(
        self,
        resource: str,
        mutable_only: bool = False,
        required_only: bool = False
    ) -> List[Dict]:
        """
        Get resource attributes with filters.
        
        Example:
            # Get mutable fields for Finding
            mutable_fields = graph.query_attributes("Finding", mutable_only=True)
            # Returns: [
            #   {"name": "meta.tags", "type": "array", "mutability": "mutable"},
            #   {"name": "spec.dismiss", "type": "boolean", "mutability": "mutable"}
            # ]
        """
        node_id = self._resource_index.get(resource)
        if not node_id:
            return []
        
        attributes = []
        for _, target, data in self.graph.out_edges(node_id, data=True):
            if data.get("type") == EdgeType.HAS_ATTRIBUTE.value:
                target_node = self.graph.nodes[target]
                attr = {
                    "name": target_node.get("label"),
                    "type": target_node.get("attr_type"),
                    "mutability": target_node.get("mutability"),
                    "required": target_node.get("required", False),
                    "description": target_node.get("description")
                }
                
                if mutable_only and attr["mutability"] != "mutable":
                    continue
                if required_only and not attr["required"]:
                    continue
                
                attributes.append(attr)
        
        return attributes
    
    def get_statistics(self) -> Dict:
        """Get graph statistics"""
        return {
            "total_nodes": self.graph.number_of_nodes(),
            "total_edges": self.graph.number_of_edges(),
            "resources": len([n for n, d in self.graph.nodes(data=True) 
                            if d.get("type") == "resource"]),
            "services": len([n for n, d in self.graph.nodes(data=True) 
                           if d.get("type") == "service"]),
            "definitions": len(self._definition_subgraphs),
        }
    
    def to_networkx(self) -> nx.MultiDiGraph:
        """Get underlying NetworkX graph for advanced operations"""
        return self.graph
```

### 3.3 Graph Builder (`src/wayfinder/builder.py`)

```python
"""
Build Wayfinder graph from OpenAPI spec and live API data.
"""

from typing import Dict, Optional
import json
from pathlib import Path

from .graph import WayfinderGraph, Node, Edge, NodeType, EdgeType
from endor_cockpit.api_client import APIClient

class GraphBuilder:
    """Build Wayfinder graph from various sources"""
    
    def __init__(self):
        self.graph = WayfinderGraph()
    
    def build_from_openapi(self, spec_path: str) -> WayfinderGraph:
        """Build graph from OpenAPI specification"""
        with open(spec_path) as f:
            spec = json.load(f)
        
        # Extract services from tags
        self._add_services(spec.get("tags", []))
        
        # Extract resources and definitions
        definitions = spec.get("definitions", {})
        self._add_resources_and_definitions(definitions)
        
        # Extract endpoints from paths
        self._add_endpoints(spec.get("paths", {}))
        
        # Add known relationships from data_model_analysis.md
        self._add_known_relationships()
        
        return self.graph
    
    def _add_services(self, tags: List[Dict]):
        """Add service nodes from OpenAPI tags"""
        for tag in tags:
            service_name = tag.get("name")
            if service_name and service_name.endswith("Service"):
                node = Node(
                    id=f"service_{service_name}",
                    type=NodeType.SERVICE,
                    label=service_name,
                    properties={"description": tag.get("description", "")}
                )
                self.graph.add_resource(node)
    
    def _add_resources_and_definitions(self, definitions: Dict):
        """
        Add resource and definition nodes.
        Resources: v1Finding, v1Project, etc.
        Definitions: v1Meta, v1FindingSpec, etc. (as subgraphs)
        """
        for def_name, def_spec in definitions.items():
            # Determine if this is a resource (has endpoints) or definition (shared)
            is_resource = self._is_resource_definition(def_name, def_spec)
            
            if is_resource:
                self._add_resource_node(def_name, def_spec)
            else:
                self._add_definition_subgraph(def_name, def_spec)
    
    def _is_resource_definition(self, name: str, spec: Dict) -> bool:
        """Determine if definition represents a resource with endpoints"""
        # Heuristic: Has uuid, tenant_meta, meta, spec structure
        props = spec.get("properties", {})
        return all(k in props for k in ["uuid", "tenant_meta", "meta", "spec"])
    
    def _add_resource_node(self, def_name: str, def_spec: Dict):
        """Add a resource node with its attributes"""
        resource_name = def_name.replace("v1", "")
        
        node = Node(
            id=f"resource_{resource_name}",
            type=NodeType.RESOURCE,
            label=resource_name,
            properties={
                "definition": def_name,
                "has_endpoint": True,
                "description": def_spec.get("description", "")
            }
        )
        self.graph.add_resource(node)
        
        # Add attributes
        self._add_resource_attributes(node.id, resource_name, def_spec)
    
    def _add_definition_subgraph(self, def_name: str, def_spec: Dict):
        """Add a definition as a subgraph of attribute nodes"""
        properties = def_spec.get("properties", {})
        required = set(def_spec.get("required", []))
        
        attribute_nodes = []
        for prop_name, prop_spec in properties.items():
            attr_node = Node(
                id=f"attr_{def_name}_{prop_name}",
                type=NodeType.ATTRIBUTE,
                label=f"{def_name}.{prop_name}",
                properties={
                    "attr_type": prop_spec.get("type", "unknown"),
                    "required": prop_name in required,
                    "description": prop_spec.get("description", ""),
                    "read_only": prop_spec.get("readOnly", False),
                }
            )
            attribute_nodes.append(attr_node)
        
        self.graph.add_definition_subgraph(def_name, attribute_nodes)
    
    def _add_resource_attributes(self, resource_id: str, resource_name: str, spec: Dict):
        """Add attribute nodes for a resource with mutability metadata"""
        # Use known mutability patterns from existing implementations
        mutability_map = self._get_mutability_map(resource_name)
        
        properties = spec.get("properties", {})
        for prop_name, prop_spec in properties.items():
            attr_node = Node(
                id=f"attr_{resource_name}_{prop_name}",
                type=NodeType.ATTRIBUTE,
                label=f"{resource_name}.{prop_name}",
                properties={
                    "attr_type": prop_spec.get("type", "unknown"),
                    "mutability": mutability_map.get(prop_name, "unknown"),
                    "description": prop_spec.get("description", ""),
                }
            )
            attr_id = self.graph.add_resource(attr_node)
            
            # Add HAS_ATTRIBUTE edge
            edge = Edge(
                source=resource_id,
                target=attr_id,
                type=EdgeType.HAS_ATTRIBUTE
            )
            self.graph.add_edge(edge)
    
    def _get_mutability_map(self, resource_name: str) -> Dict[str, str]:
        """Get mutability metadata from existing resource implementations"""
        # Known patterns from finding.py, policy.py, etc.
        if resource_name == "Finding":
            return {
                "uuid": "immutable",
                "meta": "mutable",  # meta.tags specifically
                "spec": "partial",  # Some fields mutable, some not
                "tenant_meta": "immutable",
            }
        # Add other resources as implemented
        return {}
    
    def _add_endpoints(self, paths: Dict):
        """Add endpoint nodes and connect to services/resources"""
        for path, methods in paths.items():
            for method, details in methods.items():
                if method.upper() not in ["GET", "POST", "PATCH", "DELETE", "PUT"]:
                    continue
                
                tags = details.get("tags", [])
                if tags:
                    service_name = tags[0]
                    self._add_endpoint_node(method.upper(), path, service_name, details)
    
    def _add_endpoint_node(self, method: str, path: str, service: str, details: Dict):
        """Add an endpoint node"""
        endpoint_id = f"endpoint_{method}_{path.replace('/', '_')}"
        
        node = Node(
            id=endpoint_id,
            type=NodeType.ENDPOINT,
            label=f"{method} {path}",
            properties={
                "method": method,
                "path": path,
                "summary": details.get("summary", ""),
            }
        )
        self.graph.add_resource(node)
        
        # Connect to service
        service_id = f"service_{service}"
        edge = Edge(
            source=service_id,
            target=endpoint_id,
            type=EdgeType.EXPOSES
        )
        self.graph.add_edge(edge)
    
    def _add_known_relationships(self):
        """Add known relationships from data_model_analysis.md"""
        known_rels = {
            "Finding": [
                ("RepositoryVersion", "parent_uuid", EdgeType.PARENT),
                ("RepositoryVersion", "spec.target_uuid", EdgeType.REFERENCES),
                ("Project", "spec.project_uuid", EdgeType.REFERENCES),
            ],
            "RepositoryVersion": [
                ("Project", "parent_uuid", EdgeType.PARENT),
            ],
            "Repository": [
                ("Project", "parent_uuid", EdgeType.PARENT),
            ],
        }
        
        for source, targets in known_rels.items():
            source_node = self.graph.find_resource(source)
            if not source_node:
                continue
            
            for target, via, edge_type in targets:
                target_node = self.graph.find_resource(target)
                if not target_node:
                    continue
                
                edge = Edge(
                    source=source_node["id"],
                    target=target_node["id"],
                    type=edge_type,
                    label=via,
                    properties={"via": via}
                )
                self.graph.add_edge(edge)
    
def build_graph(
    openapi_path: str = "external_docs/openapi-swagger.json"
) -> WayfinderGraph:
    """
    Build Wayfinder graph from OpenAPI specification.
    
    Static graph generated from swagger document.
    Regenerate when OpenAPI spec is updated.
    
    Example:
        graph = build_graph()
        finding = graph.find_resource("Finding")
        relationships = graph.get_relationships("Finding")
    """
    builder = GraphBuilder()
    graph = builder.build_from_openapi(openapi_path)
    return graph
```

### 3.4 Exporters (`src/wayfinder/exporters.py`)

```python
"""Export Wayfinder graph to various formats"""

import networkx as nx
from typing import Optional
from .graph import WayfinderGraph

def export_graphml(graph: WayfinderGraph, output_path: str):
    """Export to GraphML format (yEd, Gephi compatible)"""
    nx.write_graphml(graph.to_networkx(), output_path)

def export_cypher(graph: WayfinderGraph, output_path: str):
    """Export to Cypher format (Neo4j)"""
    # Generate CREATE statements
    pass

def export_dot(graph: WayfinderGraph, output_path: str):
    """Export to DOT format (Graphviz)"""
    nx.drawing.nx_pydot.write_dot(graph.to_networkx(), output_path)

def export_json(graph: WayfinderGraph, output_path: str):
    """Export to JSON format (generic)"""
    # node-link format for D3.js compatibility
    data = nx.node_link_data(graph.to_networkx())
    import json
    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2)
```

### 3.5 CLI Interface (`src/wayfinder/cli.py`)

```python
"""Command-line interface for Wayfinder"""

import click
from pathlib import Path
from .builder import build_graph
from . import exporters

@click.group()
def cli():
    """Wayfinder: Graph-based Endor Labs data model navigator"""
    pass

@cli.command()
@click.option("--output", "-o", required=True, help="Output file path")
@click.option("--format", "-f", default="graphml", 
              type=click.Choice(["graphml", "cypher", "dot", "json"]))
@click.option("--live", is_flag=True, help="Include live API data")
@click.option("--namespace", "-n", help="Namespace for live data")
def build(output, format, live, namespace):
    """Build and export Wayfinder graph"""
    click.echo("Building Wayfinder graph...")
    
    graph = build_graph(live_data=live, namespace=namespace)
    
    click.echo(f"Graph statistics: {graph.get_statistics()}")
    
    # Export
    exporter = {
        "graphml": exporters.export_graphml,
        "cypher": exporters.export_cypher,
        "dot": exporters.export_dot,
        "json": exporters.export_json,
    }[format]
    
    exporter(graph, output)
    click.echo(f"Exported to {output}")

@cli.command()
@click.argument("resource")
def relationships(resource):
    """Show relationships for a resource"""
    graph = build_graph()
    rels = graph.get_relationships(resource)
    
    click.echo(f"\nRelationships for {resource}:")
    for rel in rels:
        click.echo(f"  {rel['type']} -> {rel['target']} (via {rel.get('via', 'N/A')})")

@cli.command()
@click.argument("resource")
@click.option("--mutable-only", is_flag=True, help="Show only mutable attributes")
def attributes(resource, mutable_only):
    """Show attributes for a resource"""
    graph = build_graph()
    attrs = graph.query_attributes(resource, mutable_only=mutable_only)
    
    click.echo(f"\nAttributes for {resource}:")
    for attr in attrs:
        mutability_marker = "✏️ " if attr["mutability"] == "mutable" else "🔒 "
        click.echo(f"  {mutability_marker}{attr['name']} ({attr['type']})")

if __name__ == "__main__":
    cli()
```

### 3.6 Agent Interface Example

```python
"""Example: Agent using Wayfinder to understand data model"""

from wayfinder import build_graph

# Initialize graph
graph = build_graph()

# Agent task: "Suppress all XSS findings in dev branch"

# Step 1: Understand Finding resource
finding = graph.find_resource("Finding")
print(f"Found resource: {finding['label']}")

# Step 2: What can I safely modify?
mutable_fields = graph.query_attributes("Finding", mutable_only=True)
print("Mutable fields:", [f["name"] for f in mutable_fields])
# Output: ["meta.tags", "spec.dismiss", "spec.remediation"]

# Step 3: What do I need for exception policy?
rels = graph.get_relationships("Finding")
print("Finding references:")
for rel in rels:
    if rel["type"] == "references":
        print(f"  - {rel['target']} via {rel['via']}")
# Output:
#   - RepositoryVersion via spec.target_uuid
#   - Project via spec.project_uuid

# Step 4: Navigate to Project
path = graph.find_path("Finding", "Project")
print("Navigation path:", " -> ".join(path))
# Output: Finding -> RepositoryVersion -> Project
```

---

## Phase 4: Integration and Documentation

### 4.1 Update Repository Structure

```
src/
├── wayfinder/              # NEW: Graph-based navigator
│   ├── __init__.py
│   ├── graph.py
│   ├── builder.py
│   ├── models.py
│   ├── exporters.py
│   ├── queries.py
│   └── cli.py
├── endor_cockpit/         # Existing SDK
│   ├── resources/
│   └── ...
└── (remove holocron)

scripts/
├── index_openapi_definitions.py  # NEW

docs/
├── OPENAPI_DEFINITIONS_INDEX.md  # NEW
├── wayfinder/                     # NEW
│   ├── README.md
│   ├── AGENT_GUIDE.md
│   └── VISUALIZATION.md
└── (remove holocron/)
```

### 4.2 Documentation Files

**docs/wayfinder/README.md**

- Overview of Wayfinder
- NetworkX graph structure
- Node and edge types

**docs/wayfinder/AGENT_GUIDE.md**

- Agent-specific workflows
- Using Wayfinder for task planning
- Data model navigation patterns

**docs/wayfinder/VISUALIZATION.md**

- Exporting graphs
- Layout recommendations
- Example queries and views

---

## Implementation Steps

### Step 1: Stash and Index (0.5 day)

1. Move agent-sd.plan.md to .workspace
2. Implement `scripts/index_openapi_definitions.py`
3. Generate `docs/OPENAPI_DEFINITIONS_INDEX.md`
4. Verify completeness

### Step 2: Delete Holocron (0.5 day)

1. Delete src/holocron, tests/test_holocron*, holocron_data/
2. Remove references from docs/protocols/
3. Verify no remaining imports

### Step 3: Build Wayfinder Core (1-2 days)

1. Implement graph.py with NetworkX
2. Implement builder.py with OpenAPI parsing
3. Add known relationships from data_model_analysis.md
4. Test graph construction

### Step 4: Exporters and CLI (0.5 day)

1. Implement exporters.py
2. Implement cli.py
3. Test export formats

### Step 5: Documentation (0.5 day)

1. Create docs/wayfinder/ structure
2. Write agent-focused documentation
3. Add usage examples

---

## Success Criteria

1. ✅ OpenAPI definitions index covers 100% of definitions
2. ✅ All Holocron RAG code deleted with zero references
3. ✅ Wayfinder graph uses NetworkX as underlying structure
4. ✅ Resources are nodes, Definitions are subgraphs
5. ✅ Graph includes all major resources (Finding, Project, Policy)
6. ✅ Agent can query: resources, relationships, attributes, paths
7. ✅ Attribute nodes include mutability metadata

---

## Alignment with Agentic SDK Interface

**How Wayfinder enables robust agentic operations:**

1. **Discovery**: Agent queries graph to understand available resources and relationships
2. **Validation**: Agent checks mutability before attempting updates
3. **Navigation**: Agent finds paths between resources for complex workflows
4. **Planning**: Agent uses graph structure to plan multi-step operations
5. **Documentation**: Graph serves as self-documenting data model
6. **Type Safety**: Attribute nodes provide type information for validation
7. **Visualization**: Human operators can inspect agent's understanding via exported graphs

**Example Agent Workflow:**

```python
# Agent receives: "Suppress XSS findings in dev branch"

# Use Wayfinder to understand the task
graph = build_graph()

# What is a Finding?
finding = graph.find_resource("Finding")

# What can I modify safely?
mutable = graph.query_attributes("Finding", mutable_only=True)
# Agent learns: can update meta.tags, spec.dismiss

# What do I need for exception policy?
rels = graph.get_relationships("Finding")
# Agent learns: needs RepositoryVersion UUID (via spec.target_uuid)

# How do I get from Finding to RepositoryVersion?
path = graph.find_path("Finding", "RepositoryVersion")
# Agent learns: Direct reference via spec.target_uuid

# Execute workflow using endor_cockpit SDK
from endor_cockpit.resources import finding, policy
# ... implementation using learned structure
```

### To-dos

- [ ] Move agent plan to .workspace and create OpenAPI definitions index script
- [ ] Delete old Holocron RAG implementation and all references
- [ ] Implement Wayfinder core with NetworkX (graph.py, builder.py, models.py)
- [ ] Implement exporters and CLI interface for Wayfinder
- [ ] Create Wayfinder documentation for agents and visualization