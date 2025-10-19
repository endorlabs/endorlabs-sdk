# Project Resource Implementation Guide

> **Knowledge Base Entry**: Complete guide for implementing Project resources in Endor Cockpit SDK

## Overview

This guide documents the successful implementation of Project resources, including critical learnings, API patterns, and a repeatable workflow for implementing other resources.

## Project Resource Understanding

### **Core Concepts**
- **1:1 with Git Repository**: Each project represents a git-tracked repository
- **Namespace-scoped**: Projects belong to a specific namespace (e.g., `endor-solutions-tgowan.cockpit`)
- **Policy-driven**: Projects are subject to namespace policies and scanning
- **Finding container**: Projects contain findings from security scans
- **Processing status**: Tracks scan state, timing, and automated scan settings

### **Resource Structure**
```python
class Project(BaseModel):
    meta: ProjectMeta              # Metadata (name, description, timestamps)
    processing_status: ProcessingStatus  # Scan state and timing
    spec: ProjectSpec             # Git repository information
    tenant_meta: TenantMeta       # Namespace information
    uuid: str                     # Unique identifier
```

## API Implementation Patterns

### **Endpoint Pattern**
```
GET    /v1/namespaces/{tenant_meta.namespace}/projects
POST   /v1/namespaces/{tenant_meta.namespace}/projects
GET    /v1/namespaces/{tenant_meta.namespace}/projects/{uuid}
DELETE /v1/namespaces/{tenant_meta.namespace}/projects/{uuid}
```

### **Critical Parameters**
- **Path parameter**: `tenant_meta.namespace` (canonical namespace name)
- **NOT**: `namespace_uuid` or `tenant_namespace`
- **Example**: `endor-solutions-tgowan.cockpit`

### **Response Structure**
```json
{
  "list": {
    "objects": [
      {
        "meta": {
          "name": "https://github.com/owner/repo.git",
          "description": null,
          "create_time": "2025-10-18T15:44:29.121Z",
          "created_by": "user@endor.ai",
          "kind": "Project",
          "version": "v1"
        },
        "processing_status": {
          "disable_automated_scan": true,
          "scan_state": "SCAN_STATE_IDLE",
          "scan_time": "2025-10-19T02:54:15.996651723Z"
        },
        "spec": {
          "git": {
            "full_name": "owner/repo",
            "git_clone_url": "git@github.com:owner/repo.git",
            "http_clone_url": "https://github.com/owner/repo.git",
            "organization": "owner",
            "path": "repo",
            "web_url": "https://api.github.com/owner/repo"
          },
          "internal_reference_key": "https://github.com/owner/repo.git",
          "platform_source": "PLATFORM_SOURCE_GITHUB"
        },
        "tenant_meta": {
          "namespace": "endor-solutions-tgowan.cockpit"
        },
        "uuid": "68f3b5ddf04afdad6f14be97"
      }
    ]
  }
}
```

## Implementation Workflow

### **Step 1: Knowledge Base Query**
```python
from endor_cockpit.rag import query_vector_db

# Query for existing patterns
results = query_vector_db("How do I implement Project resources?")
results = query_vector_db("What are the API endpoints for projects?")
```

### **Step 2: OpenAPI Specification Analysis**
```bash
# Search for service endpoints
grep -i "ProjectService" tmp/openapiv2.swagger.json
grep -i "FindingService" tmp/openapiv2.swagger.json
grep -i "PolicyService" tmp/openapiv2.swagger.json
```

### **Step 3: GET Operations First**
```python
# Start with simple GET to understand structure
client = APIClient()
namespace = "endor-solutions-tgowan.cockpit"
response = client.get(f"v1/namespaces/{namespace}/projects")
print(response.json())
```

### **Step 4: Pydantic Model Creation**
```python
# Model from live data + API spec
class Project(BaseModel):
    meta: ProjectMeta
    processing_status: ProcessingStatus
    spec: ProjectSpec
    tenant_meta: TenantMeta
    uuid: str
```

### **Step 5: Resource Module Implementation**
```python
def list_projects(client: APIClient, tenant_meta_namespace: str) -> List[Project]:
    """List all projects in the specified namespace."""
    res = client.get(f"v1/namespaces/{tenant_meta_namespace}/projects")
    data = res.json()
    projects_data = data.get("list", {}).get("objects", [])
    return [Project(**item) for item in projects_data]
```

## Common Pitfalls & Solutions

### **❌ Wrong Path Parameter**
```python
# WRONG - This will fail
client.get(f"v1/namespaces/{namespace_uuid}/projects")

# CORRECT - Use canonical namespace
client.get(f"v1/namespaces/{tenant_meta_namespace}/projects")
```

### **❌ Wrong Response Parsing**
```python
# WRONG - This will fail
data = res.json().get("projects", [])

# CORRECT - Use list.objects structure
data = res.json().get("list", {}).get("objects", [])
```

### **❌ Direct API Calls**
```python
# WRONG - Direct calls may fail due to auth issues
response = client.get("v1/namespaces/...")

# CORRECT - Use resource modules
projects = list_projects(client, namespace)
```

## Testing Strategy

### **Collaborative Workspace**
```python
# workspace/workspace.py - Single file for experimentation
import sys
sys.path.insert(0, '..')
from endor_cockpit.api_client import APIClient
from endor_cockpit.resources import projects, findings, namespaces

client = APIClient()
namespace = os.getenv('ENDOR_NAMESPACE', 'endor-solutions-tgowan.cockpit')

# Test operations
projects_list = projects.list_projects(client, namespace)
print(f"Found {len(projects_list)} projects")
```

### **Validation Steps**
1. **Check namespace exists**: Verify canonical namespace format
2. **Test GET operations**: Ensure endpoints return data
3. **Validate models**: Confirm Pydantic models match API response
4. **Test CRUD operations**: Verify create, update, delete work
5. **Document quirks**: Record any API discrepancies

## Success Metrics

### **✅ Implementation Complete When:**
- [ ] GET operations return actual data (not empty lists)
- [ ] Pydantic models validate without errors
- [ ] All CRUD operations work correctly
- [ ] Resource module follows established patterns
- [ ] Documentation updated with learnings
- [ ] Tests pass for all operations

### **✅ Knowledge Base Updated When:**
- [ ] API patterns documented
- [ ] Common pitfalls recorded
- [ ] Workflow steps captured
- [ ] Quirks and learnings documented
- [ ] Repeatable process established

## Related Resources

- [Project Data Model](./projects.md)
- [Finding Data Model](./findings.md)
- [Namespace Data Model](./namespaces.md)
- [API Specification](../SPECIFICATION.md)
- [Troubleshooting Guide](../../workspace/troubleshooting-guide.md)

## Next Steps

1. **Finding Resources**: Apply same workflow to implement Finding endpoints
2. **Policy Resources**: Apply same workflow to implement Policy endpoints
3. **Tagging System**: Implement tagging functionality for Projects and Findings
4. **Integration Testing**: Create comprehensive test suite
5. **Documentation**: Update all guides with new patterns

---

*This guide serves as the definitive reference for implementing Endor Labs resources in the Cockpit SDK.*
