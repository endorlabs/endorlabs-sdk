# Resource Implementation Workflow

> **Universal Guide**: Step-by-step process for implementing any Endor Labs resource in the Cockpit SDK

## Overview

This workflow provides a repeatable, systematic approach for implementing new resources (Projects, Findings, Policies, etc.) in the Endor Cockpit SDK. It's based on successful implementation of Project resources and incorporates all critical learnings.

## Pre-Implementation Checklist

### **Environment Setup**
- [ ] Virtual environment activated (`uv venv` + `source .venv/bin/activate`)
- [ ] Environment variables set (`ENDOR_API`, `ENDOR_API_CREDENTIALS_KEY`, `ENDOR_API_CREDENTIALS_SECRET`, `ENDOR_NAMESPACE`)
- [ ] OpenAPI spec downloaded (`tmp/openapiv2.swagger.json`)
- [ ] Workspace ready (`workspace/workspace.py`)

### **Knowledge Base Check**
```python
from endor_cockpit.rag import query_vector_db

# Query for existing patterns
results = query_vector_db("How do I implement {Resource} resources?")
results = query_vector_db("What are the API endpoints for {resource}?")
results = query_vector_db("What are the common pitfalls for {resource} implementation?")
```

## Step-by-Step Implementation Process

### **Step 1: OpenAPI Specification Analysis**

#### **1.1 Find Service Endpoints**
```bash
# Search for the resource service
grep -i "{Resource}Service" tmp/openapiv2.swagger.json
# Examples: ProjectService, FindingService, PolicyService
```

#### **1.2 Extract Endpoint Patterns**
```bash
# Find all endpoints for the service
grep -A 20 -B 5 "{Resource}Service" tmp/openapiv2.swagger.json
```

#### **1.3 Document Endpoint Structure**
- **List endpoint**: `GET /v1/namespaces/{tenant_meta.namespace}/{resource}`
- **Create endpoint**: `POST /v1/namespaces/{tenant_meta.namespace}/{resource}`
- **Get endpoint**: `GET /v1/namespaces/{tenant_meta.namespace}/{resource}/{uuid}`
- **Update endpoint**: `PATCH /v1/namespaces/{tenant_meta.namespace}/{resource}/{uuid}`
- **Delete endpoint**: `DELETE /v1/namespaces/{tenant_meta.namespace}/{resource}/{uuid}`

### **Step 2: GET Operations First**

#### **2.1 Test Basic GET Operation**
```python
# workspace/workspace.py
import sys
sys.path.insert(0, '..')
from endor_cockpit.api_client import APIClient
import os

client = APIClient()
namespace = os.getenv('ENDOR_NAMESPACE', 'endor-solutions-tgowan.cockpit')

# Test the endpoint
response = client.get(f"v1/namespaces/{namespace}/{resource}")
if response:
    print("Response keys:", list(response.json().keys()))
    print("Response structure:", response.json())
else:
    print("No response - check endpoint and authentication")
```

#### **2.2 Understand Response Structure**
- **Expected pattern**: `{"list": {"objects": [...]}}`
- **NOT**: Direct array `[...]`
- **Document**: Actual response structure for modeling

### **Step 3: Live Data Analysis**

#### **3.1 Use endorctl for Reference**
```bash
# Get live data structure
endorctl api list -r {Resource}
# Example: endorctl api list -r Project
```

#### **3.2 Compare with API Response**
- **endorctl output**: Shows actual data structure
- **API response**: Shows what SDK will receive
- **Identify**: Any differences or transformations needed

### **Step 4: Pydantic Model Creation**

#### **4.1 Start with Basic Structure**
```python
class {Resource}Meta(BaseModel):
    """Metadata for {Resource}."""
    name: str
    create_time: str
    created_by: str
    # Add fields based on live data analysis

class {Resource}(BaseModel):
    """An Endor Labs {resource} entity."""
    meta: {Resource}Meta
    uuid: str
    # Add fields based on API response structure
```

#### **4.2 Iterate Based on Validation Errors**
```python
# Test with live data
try:
    resource = {Resource}(**live_data)
    print("Model validation successful")
except ValidationError as e:
    print("Validation errors:", e.errors())
    # Fix model based on errors
```

### **Step 5: Resource Module Implementation**

#### **5.1 Implement CRUD Operations**
```python
def list_{resource}s(client: APIClient, tenant_meta_namespace: str) -> List[{Resource}]:
    """List all {resource}s in the specified namespace."""
    res = client.get(f"v1/namespaces/{tenant_meta_namespace}/{resource}s")
    data = res.json()
    {resource}s_data = data.get("list", {}).get("objects", [])
    return [{Resource}(**item) for item in {resource}s_data]

def get_{resource}(client: APIClient, tenant_meta_namespace: str, {resource}_uuid: str) -> Optional[{Resource}]:
    """Get a specific {resource} by UUID."""
    res = client.get(f"v1/namespaces/{tenant_meta_namespace}/{resource}s/{resource}_uuid")
    data = res.json()
    return {Resource}(**data)
```

#### **5.2 Test All Operations**
```python
# Test in workspace.py
{resource}s_list = {resource}s.list_{resource}s(client, namespace)
print(f"Found {len({resource}s_list)} {resource}s")

if {resource}s_list:
    for {resource} in {resource}s_list[:3]:
        print(f"  - {resource}.meta.name (UUID: {resource}.uuid)")
```

### **Step 6: Documentation & Knowledge Base Update**

#### **6.1 Update Implementation Guide**
- **Create**: `docs/knowledge/endor-data-model/{resource}-implementation-guide.md`
- **Include**: API patterns, common pitfalls, success metrics
- **Document**: All quirks and learnings

#### **6.2 Update Log**
```markdown
### **✅ {Resource} Resource Implementation Success**

#### **Key Learnings:**
- API endpoints: `/v1/namespaces/{tenant_meta.namespace}/{resource}s`
- Response structure: `{"list": {"objects": [...]}}`
- Critical parameters: Use `tenant_meta_namespace` not `namespace_uuid`
- Pydantic models: Based on live data + API spec

#### **Common Pitfalls:**
- Wrong path parameters
- Incorrect response parsing
- Direct API calls without resource modules
```

## Quality Assurance Checklist

### **✅ Implementation Complete When:**
- [ ] GET operations return actual data (not empty lists)
- [ ] Pydantic models validate without errors
- [ ] All CRUD operations work correctly
- [ ] Resource module follows established patterns
- [ ] Documentation updated with learnings
- [ ] Tests pass for all operations
- [ ] Workspace.py demonstrates working functionality

### **✅ Knowledge Base Updated When:**
- [ ] API patterns documented
- [ ] Common pitfalls recorded
- [ ] Workflow steps captured
- [ ] Quirks and learnings documented
- [ ] Repeatable process established
- [ ] Implementation guide created

## Workspace Management

### **Collaborative Development**
- **Single file**: Use `workspace/workspace.py` for all experimentation
- **Function-based**: Define test functions instead of one-off scripts
- **Version control**: Commit working versions with descriptive messages
- **Clean up**: Remove one-off scripts, keep only workspace.py

### **Example Workspace Structure**
```python
# workspace/workspace.py
import sys
sys.path.insert(0, '..')
from endor_cockpit.api_client import APIClient
from endor_cockpit.resources import projects, findings, namespaces
import os

def test_projects():
    """Test project operations."""
    client = APIClient()
    namespace = os.getenv('ENDOR_NAMESPACE', 'endor-solutions-tgowan.cockpit')
    
    projects_list = projects.list_projects(client, namespace)
    print(f"Found {len(projects_list)} projects")
    return projects_list

def test_findings():
    """Test finding operations."""
    # Implementation here
    pass

if __name__ == "__main__":
    # Run tests
    test_projects()
    test_findings()
```

## Common Resource Types

### **Projects**
- **Service**: `ProjectService`
- **Endpoint**: `/v1/namespaces/{tenant_meta.namespace}/projects`
- **Purpose**: Git repository representation
- **Key fields**: `meta`, `processing_status`, `spec`, `tenant_meta`

### **Findings**
- **Service**: `FindingService` (to be implemented)
- **Endpoint**: `/v1/namespaces/{tenant_meta.namespace}/findings`
- **Purpose**: Security scan results
- **Key fields**: `meta`, `severity`, `status`, `details`

### **Policies**
- **Service**: `PolicyService` (to be implemented)
- **Endpoint**: `/v1/namespaces/{tenant_meta.namespace}/policies`
- **Purpose**: Security policy definitions
- **Key fields**: `meta`, `rules`, `actions`, `scope`

## Troubleshooting Guide

### **Common Issues & Solutions**

#### **Empty Results**
```python
# Check namespace format
namespace = "endor-solutions-tgowan.cockpit"  # Correct
namespace = "namespace-uuid-here"            # Wrong

# Check endpoint format
endpoint = f"v1/namespaces/{namespace}/projects"  # Correct
endpoint = f"v1/namespaces/{uuid}/projects"       # Wrong
```

#### **Validation Errors**
```python
# Check model against live data
endorctl api list -r Project > live_data.json
# Compare with Pydantic model fields
```

#### **Authentication Issues**
```python
# Use resource modules, not direct API calls
projects = list_projects(client, namespace)  # Correct
response = client.get(endpoint)             # May fail
```

## Success Metrics

### **Implementation Success**
- [ ] Resource module created and working
- [ ] All CRUD operations functional
- [ ] Pydantic models validate correctly
- [ ] Documentation complete
- [ ] Knowledge base updated
- [ ] Workspace cleaned up

### **Quality Indicators**
- [ ] No one-off scripts in workspace
- [ ] Single workspace.py file for experimentation
- [ ] All learnings documented
- [ ] Repeatable process established
- [ ] Ready for next resource implementation

---

*This workflow ensures consistent, high-quality implementation of all Endor Labs resources in the Cockpit SDK.*
