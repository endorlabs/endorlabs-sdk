#!/usr/bin/env python3
"""
Simple workspace for Endor Cockpit API experimentation.
"""

import sys
import os

# Add src to path for imports FIRST
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from endor_cockpit.api_client import APIClient
from endor_cockpit.resources import namespaces

def main():
    """Main workspace function."""
    # Initialize APIClient
    from endor_cockpit.api_client import APIClient
    client = APIClient()
    
    # Import resource modules
    from endor_cockpit.resources import namespaces, projects, findings, tags
    
    # Import Pydantic classes
    from endor_cockpit.resources.namespaces import (
        CreateNamespacePayload, 
        NamespaceMetaCreate,
        NamespaceMetaUpdate,
        UpdateNamespacePayload
    )
    from endor_cockpit.resources.projects import (
        CreateProjectPayload,
        ProjectMetaCreate,
        ProjectMetaUpdate,
        UpdateProjectPayload
    )
    from endor_cockpit.resources.findings import (
        FindingType,
        Severity,
        Status
    )
    
    # Get current namespace
    namespace = os.getenv('ENDOR_NAMESPACE', 'endor-solutions-tgowan.cockpit')
    
    # Make everything available in global scope
    globals().update({
        'client': client,
        'namespace': namespace,
        'namespaces': namespaces,
        'projects': projects,
        'findings': findings,
        'tags': tags,
        'CreateNamespacePayload': CreateNamespacePayload,
        'NamespaceMetaCreate': NamespaceMetaCreate,
        'NamespaceMetaUpdate': NamespaceMetaUpdate,
        'UpdateNamespacePayload': UpdateNamespacePayload,
        'CreateProjectPayload': CreateProjectPayload,
        'ProjectMetaCreate': ProjectMetaCreate,
        'ProjectMetaUpdate': ProjectMetaUpdate,
        'UpdateProjectPayload': UpdateProjectPayload,
        'FindingType': FindingType,
        'Severity': Severity,
        'Status': Status
    })
    
    print("Workspace ready. Available objects:")
    print("  client, namespace, namespaces, projects, findings, tags")
    print("  CreateNamespacePayload, NamespaceMetaCreate, etc.")
    print("  FindingType, Severity, Status")

def test_namespaces():
    """Test namespace operations."""
    print("=== Testing Namespaces ===")
    namespaces_list = namespaces.list_namespaces(client, namespace)
    print(f"Found {len(namespaces_list)} namespaces:")
    for ns in namespaces_list:
        print(f"  - {ns.meta.name} (UUID: {ns.uuid})")
    return namespaces_list

def test_projects():
    """Test project operations."""
    print("\n=== Testing Projects ===")
    projects_list = projects.list_projects(client, namespace)
    print(f"Found {len(projects_list)} projects:")
    for project in projects_list:
        print(f"  - {project.meta.name} (UUID: {project.uuid})")
        print(f"    Namespace: {project.tenant_meta.namespace}")
        print(f"    Description: {project.meta.description}")
    return projects_list

def test_findings():
    """Test finding operations."""
    print("\n=== Testing Findings ===")
    findings_list = findings.list_findings(client, namespace)
    print(f"Found {len(findings_list)} findings:")
    for finding in findings_list:
        print(f"  - {finding.meta.details.title} (Severity: {finding.meta.severity.value})")
    return findings_list

def test_project_by_uuid(project_uuid: str):
    """Test getting a specific project by UUID."""
    print(f"\n=== Testing Get Project: {project_uuid} ===")
    project = projects.get_project(client, namespace, project_uuid)
    if project:
        print(f"Found project: {project.meta.name}")
        print(f"  Namespace: {project.tenant_meta.namespace}")
        print(f"  Scan State: {project.processing_status.scan_state}")
    else:
        print("Project not found")
    return project

if __name__ == "__main__":
    # Import the modules we need
    from endor_cockpit.resources import projects, findings, namespaces

    client = APIClient()
    namespace = os.getenv('ENDOR_NAMESPACE', 'endor-solutions-tgowan.cockpit')

    print("[START] Endor Cockpit Resource Testing Workspace")
    print(f"Namespace: {namespace}")
    print("=" * 50)

    # Run all tests
    namespaces_list = test_namespaces()
    projects_list = test_projects()
    findings_list = test_findings()

    # Test specific project if available
    if projects_list:
        test_project_by_uuid(projects_list[0].uuid)

    print("\n[SUCCESS] Workspace ready for interactive use!")
    print("Available functions: test_namespaces(), test_projects(), test_findings(), test_project_by_uuid(uuid)")
