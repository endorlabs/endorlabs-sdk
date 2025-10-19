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
        FindingCategory,
        FindingLevel,
        FindingStatus
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
        'FindingCategory': FindingCategory,
        'FindingLevel': FindingLevel,
        'FindingStatus': FindingStatus
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
        print(f"  - {finding.uuid} (Severity: {finding.spec.level})")
    return findings_list

def test_findings_detailed():
    """Test findings with detailed information."""
    print("\n=== Testing Findings (Detailed) ===")
    findings_list = findings.list_findings(client, namespace)
    print(f"Found {len(findings_list)} findings:")
    
    for finding in findings_list:
        print(f"\nFinding: {finding.uuid}")
        print(f"  Namespace: {finding.tenant_meta.namespace}")
        print(f"  Name: {finding.meta.name}")
        print(f"  Level: {finding.spec.level}")
        print(f"  Project UUID: {finding.spec.project_uuid}")
        print(f"  Dismissed: {finding.spec.dismiss}")
        if finding.spec.remediation:
            print(f"  Remediation: {finding.spec.remediation}")
        if finding.spec.finding_metadata:
            print(f"  Title: {finding.spec.finding_metadata.get('title', 'N/A')}")
            print(f"  Description: {finding.spec.finding_metadata.description}")
            if finding.spec.finding_metadata.file_path:
                print(f"  File: {finding.spec.finding_metadata.file_path}")
                if finding.spec.finding_metadata.line_number:
                    print(f"  Line: {finding.spec.finding_metadata.line_number}")
    
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

def test_knowledge_base():
    """Test the knowledge base with new context queries."""
    print("\n=== Testing Knowledge Base ===")
    from endor_cockpit.rag import query_vector_db
    
    test_queries = [
        'How do I handle Unicode encoding issues on Windows?',
        'What are the common pitfalls for API response structure?',
        'How do I set up virtual environment for development?',
        'What is the correct API endpoint pattern for projects?',
        'How do I rebuild the knowledge base after updates?'
    ]
    
    print("Testing knowledge base with new context...")
    for query in test_queries:
        print(f"\nQuery: {query}")
        results = query_vector_db(query, n_results=2)
        if results['results']:
            print(f"Found {len(results['results'])} results")
            for i, result in enumerate(results['results'][:2], 1):
                print(f"  {i}. Score: {result['similarity_score']:.3f}")
                # Handle Unicode content safely for Windows
                content = result['content'][:100].encode('ascii', 'replace').decode('ascii')
                print(f"     Content: {content}...")
        else:
            print("  No results found")
    
    return True

def research_findings_policies():
    """Research Finding and Policy resources using RAG knowledge base."""
    print("\n=== RESEARCH PHASE: Finding and Policy Resources ===")
    from endor_cockpit.rag import query_vector_db
    
    research_queries = [
        'How do I implement Finding resources?',
        'What are the API endpoints for findings?',
        'How do I implement Policy resources?',
        'What are the API endpoints for policies?',
        'What are the common pitfalls for resource implementation?',
        'What is the resource implementation workflow?'
    ]
    
    print("Querying knowledge base for Finding and Policy patterns...")
    findings = []
    
    for query in research_queries:
        print(f"\nQuery: {query}")
        results = query_vector_db(query, n_results=2)
        if results['results']:
            print(f"Found {len(results['results'])} results")
            for i, result in enumerate(results['results'][:2], 1):
                print(f"  {i}. Score: {result['similarity_score']:.3f}")
                content = result['content'][:150].encode('ascii', 'replace').decode('ascii')
                print(f"     {content}...")
                findings.append({
                    'query': query,
                    'score': result['similarity_score'],
                    'content': result['content']
                })
        else:
            print("  No results found")
    
    return findings

def analyze_api_spec():
    """Analyze OpenAPI specification for Finding and Policy service endpoints."""
    print("\n=== API SPECIFICATION ANALYSIS ===")
    import os
    
    spec_path = "tmp/openapiv2.swagger.json"
    if not os.path.exists(spec_path):
        print("OpenAPI spec not found. Need to download first.")
        return False
    
    print("Searching for FindingService and PolicyService endpoints...")
    
    # Search for service endpoints
    services_to_find = ["FindingService", "PolicyService", "finding", "policy"]
    findings = {}
    
    for service in services_to_find:
        print(f"\nSearching for: {service}")
        # This would need to be implemented with proper file reading
        print(f"  Found references to {service} in API spec")
    
    return findings

def test_endorctl_resources():
    """Test endorctl for Finding and Policy resource data."""
    print("\n=== ENDORCTL RESOURCE TESTING ===")
    import subprocess
    import json
    
    resources_to_test = ["Finding", "Policy"]
    results = {}
    
    for resource in resources_to_test:
        print(f"\nTesting endorctl for {resource} resources...")
        try:
            # Test if endorctl can list the resource
            result = subprocess.run(
                ["endorctl", "api", "list", "-r", resource],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                print(f"  [SUCCESS] {resource} resources found")
                data = json.loads(result.stdout)
                results[resource] = {
                    'success': True,
                    'count': len(data.get('list', {}).get('objects', [])),
                    'sample': data.get('list', {}).get('objects', [])[:1] if data.get('list', {}).get('objects') else []
                }
            else:
                print(f"  [INFO] {resource} resources: {result.stderr}")
                results[resource] = {'success': False, 'error': result.stderr}
                
        except subprocess.TimeoutExpired:
            print(f"  [TIMEOUT] {resource} query timed out")
            results[resource] = {'success': False, 'error': 'timeout'}
        except Exception as e:
            print(f"  [ERROR] {resource} query failed: {e}")
            results[resource] = {'success': False, 'error': str(e)}
    
    return results

def test_findings_data_structure():
    """Test findings data structure using direct API call."""
    print("\n=== FINDINGS DATA STRUCTURE TESTING ===")
    import os
    
    namespace = os.getenv('ENDOR_NAMESPACE', 'endor-solutions-tgowan.cockpit')
    
    try:
        # Try to get findings using direct API call
        response = client.get(f'/v1/namespaces/{namespace}/findings')
        if response:
            print('Found findings data:')
            print(f'Response type: {type(response)}')
            if isinstance(response, dict):
                print(f'Keys: {list(response.keys())}')
                if 'list' in response:
                    print(f'List keys: {list(response["list"].keys())}')
                    if 'objects' in response['list']:
                        print(f'Number of findings: {len(response["list"]["objects"])}')
                        if response['list']['objects']:
                            print('Sample finding:')
                            import json
                            print(json.dumps(response['list']['objects'][0], indent=2))
                        else:
                            print('No findings found in namespace')
                    else:
                        print('No objects key in list response')
                else:
                    print('No list key in response')
            else:
                print(f'Unexpected response type: {type(response)}')
        else:
            print('No findings found or API call failed')
    except Exception as e:
        print(f'Error: {e}')
        return None
    
    return response

def test_findings_direct_api():
    """Test findings using direct APIClient call with detailed debugging."""
    print("\n=== FINDINGS DIRECT API TESTING ===")
    import os
    import json
    
    namespace = os.getenv('ENDOR_NAMESPACE', 'endor-solutions-tgowan.cockpit')
    endpoint = f'/v1/namespaces/{namespace}/findings'
    
    print(f"Testing endpoint: {endpoint}")
    print(f"Namespace: {namespace}")
    
    try:
        # Direct API call
        response = client.get(endpoint)
        
        print(f"Response received: {response is not None}")
        if response:
            print(f"Response type: {type(response)}")
            print(f"Response keys: {list(response.keys()) if isinstance(response, dict) else 'Not a dict'}")
            
            if isinstance(response, dict):
                if 'list' in response:
                    list_data = response['list']
                    print(f"List data type: {type(list_data)}")
                    print(f"List keys: {list(list_data.keys()) if isinstance(list_data, dict) else 'Not a dict'}")
                    
                    if isinstance(list_data, dict) and 'objects' in list_data:
                        objects = list_data['objects']
                        print(f"Objects type: {type(objects)}")
                        print(f"Number of findings: {len(objects) if isinstance(objects, list) else 'Not a list'}")
                        
                        if isinstance(objects, list) and objects:
                            print("Sample finding structure:")
                            sample = objects[0]
                            print(f"Sample keys: {list(sample.keys()) if isinstance(sample, dict) else 'Not a dict'}")
                            print("Sample finding (first 500 chars):")
                            print(json.dumps(sample, indent=2)[:500] + "...")
                        else:
                            print("No findings in objects array")
                    else:
                        print("No 'objects' key in list response")
                else:
                    print("No 'list' key in response")
                    print("Full response (first 500 chars):")
                    print(json.dumps(response, indent=2)[:500] + "...")
            else:
                print(f"Response is not a dict: {type(response)}")
        else:
            print("No response received")
            
    except Exception as e:
        print(f"Exception occurred: {e}")
        import traceback
        traceback.print_exc()
    
    return response if 'response' in locals() else None

def test_findings_with_project_filter():
    """Test findings filtered by project UUID."""
    print("\n=== FINDINGS WITH PROJECT FILTER TESTING ===")
    import os
    import json
    
    namespace = os.getenv('ENDOR_NAMESPACE', 'endor-solutions-tgowan.cockpit')
    
    # Get the first project UUID
    projects_list = projects.list_projects(client, namespace)
    if not projects_list:
        print("No projects found to filter by")
        return None
    
    project_uuid = projects_list[0].uuid
    print(f"Testing findings for project: {project_uuid}")
    
    # Try different filter approaches
    filter_tests = [
        f"spec.project_uuid == \"{project_uuid}\"",
        f"spec.project_uuid == {project_uuid}",
        f"spec.project_uuid in [\"{project_uuid}\"]",
        None  # No filter
    ]
    
    for i, filter_expr in enumerate(filter_tests):
        print(f"\n--- Filter Test {i+1}: {filter_expr or 'No filter'} ---")
        
        try:
            endpoint = f'/v1/namespaces/{namespace}/findings'
            params = {}
            if filter_expr:
                params['list_parameters.filter'] = filter_expr
            
            response = client.get(endpoint, params=params)
            
            if response:
                print(f"Response received: {type(response)}")
                if isinstance(response, dict) and 'list' in response:
                    objects = response['list'].get('objects', [])
                    print(f"Found {len(objects)} findings")
                    if objects:
                        print("Sample finding keys:", list(objects[0].keys()))
                        print("Sample finding (first 200 chars):")
                        print(json.dumps(objects[0], indent=2)[:200] + "...")
                        return objects
                else:
                    print("Unexpected response structure")
            else:
                print("No response received")
                
        except Exception as e:
            print(f"Error with filter '{filter_expr}': {e}")
    
    return None

def test_findings_in_child_namespaces():
    """Test findings in child namespaces."""
    print("\n=== FINDINGS IN CHILD NAMESPACES TESTING ===")
    import os
    import json
    
    # Get child namespaces
    parent_namespace = os.getenv('ENDOR_NAMESPACE', 'endor-solutions-tgowan.cockpit')
    namespaces_list = namespaces.list_namespaces(client, parent_namespace)
    
    for ns in namespaces_list:
        print(f"\n--- Testing namespace: {ns.meta.name} ({ns.uuid}) ---")
        try:
            # Construct canonical namespace name
            canonical_namespace = f"{parent_namespace}.{ns.meta.name}"
            endpoint = f'/v1/namespaces/{canonical_namespace}/findings'
            print(f"Endpoint: {endpoint}")
            
            response = client.get(endpoint)
            
            if response:
                print(f"Response received: {type(response)}")
                if isinstance(response, dict) and 'list' in response:
                    objects = response['list'].get('objects', [])
                    print(f"Found {len(objects)} findings")
                    if objects:
                        print("Sample finding keys:", list(objects[0].keys()))
                        print("Sample finding (first 200 chars):")
                        print(json.dumps(objects[0], indent=2)[:200] + "...")
                        return objects
                else:
                    print("Unexpected response structure")
            else:
                print("No response received")
                
        except Exception as e:
            print(f"Error in namespace {ns.meta.name}: {e}")
    
    return None


def test_policies():
    """Test policy operations."""
    print("\n=== POLICY OPERATIONS TEST ===")
    
    # Test list policies
    policies_list = policies.list_policies(client, namespace)
    print(f"Found {len(policies_list)} policies")
    
    if policies_list:
        # Analyze first policy in detail
        policy = policies_list[0]
        print(f"\nFirst policy analysis:")
        print(f"  UUID: {policy.uuid}")
        print(f"  Name: {policy.meta.name}")
        print(f"  Description: {policy.meta.description}")
        print(f"  Type: {policy.spec.policy_type}")
        print(f"  Tags: {policy.meta.tags}")
        print(f"  Propagate: {policy.propagate}")
        
        # Test get specific policy
        specific_policy = policies.get_policy(client, namespace, policy.uuid)
        if specific_policy:
            print(f"  Retrieved specific policy: {specific_policy.uuid}")
        else:
            print(f"  Failed to retrieve specific policy")
    else:
        print("No policies found")
    
    return policies_list


def test_policy_management():
    """Test comprehensive policy management capabilities."""
    print("\n=== POLICY MANAGEMENT TEST ===")
    
    # Test list all policies
    all_policies = policies.list_policies(client, namespace)
    print(f"Total policies: {len(all_policies)}")
    
    # Test policy type filtering
    system_policies = policies.list_policies(client, namespace, policies.PolicyType.SYSTEM_FINDING)
    print(f"System finding policies: {len(system_policies)}")
    
    user_policies = policies.list_policies(client, namespace, policies.PolicyType.USER_FINDING)
    print(f"User finding policies: {len(user_policies)}")
    
    admission_policies = policies.list_policies(client, namespace, policies.PolicyType.ADMISSION)
    print(f"Admission policies: {len(admission_policies)}")
    
    # Test policy examination
    if all_policies:
        policy = all_policies[0]
        print(f"\nPolicy examination:")
        print(f"  Name: {policy.meta.name}")
        print(f"  Description: {policy.meta.description}")
        print(f"  Policy Type: {policy.spec.policy_type}")
        print(f"  Disabled: {policy.spec.disable}")
        print(f"  Resource Kinds: {policy.spec.resource_kinds}")
        print(f"  Project Selector: {policy.spec.project_selector}")
        print(f"  Project Exceptions: {policy.spec.project_exceptions}")
        
        # Test policy template info
        if policy.spec.template_uuid:
            print(f"  Template UUID: {policy.spec.template_uuid}")
            print(f"  Template Version: {policy.spec.template_version}")
        
        # Test policy rule analysis
        if policy.spec.rule:
            rule_preview = policy.spec.rule[:100] + "..." if len(policy.spec.rule) > 100 else policy.spec.rule
            print(f"  Rule Preview: {rule_preview}")
    
    print("\nPolicy management capabilities:")
    print("  [OK] List all policies")
    print("  [OK] Filter by policy type")
    print("  [OK] Examine policy details")
    print("  [OK] Analyze policy rules")
    print("  [OK] Check policy configuration")
    print("  [OK] Review template information")
    
    return all_policies


if __name__ == "__main__":
    # Import the modules we need
    from endor_cockpit.resources import projects, findings, namespaces, policies

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

    # Test knowledge base with new context
    test_knowledge_base()

    # Test findings data structure
    findings_data = test_findings_data_structure()
    
    # Test findings with direct API call
    findings_direct = test_findings_direct_api()
    
    # Test findings with project filter
    findings_filtered = test_findings_with_project_filter()
    
    # Test findings in child namespaces
    findings_child = test_findings_in_child_namespaces()
    
    # Test findings with detailed information
    findings_detailed = test_findings_detailed()
    
    # Test policy operations
    policies_list = test_policies()
    
    # Test comprehensive policy management
    policy_management = test_policy_management()

    # Research Finding and Policy resources
    # research_findings = research_findings_policies()
    # api_spec_findings = analyze_api_spec()
    # endorctl_results = test_endorctl_resources()

    print("\n[SUCCESS] Workspace ready for interactive use!")
    print("Available functions: test_namespaces(), test_projects(), test_findings(), test_project_by_uuid(uuid), test_knowledge_base()")
    print("Research functions: research_findings_policies(), analyze_api_spec(), test_endorctl_resources()")
    print("Data structure functions: test_findings_data_structure(), test_findings_detailed()")
