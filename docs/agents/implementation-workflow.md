# Resource Implementation Workflow

> **Universal Guide**: Step-by-step process for implementing any Endor Labs resource in the Cockpit SDK

## 🎯 **Quick Start**

### **Pre-Implementation Checklist**
- [ ] Virtual environment activated (`uv venv` + `source .venv/bin/activate`)
- [ ] Environment variables set (`ENDOR_API`, `ENDOR_API_CREDENTIALS_KEY`, `ENDOR_API_CREDENTIALS_SECRET`, `ENDOR_NAMESPACE`)
- [ ] OpenAPI spec downloaded (`.workspace/downloads/openapi-swagger.json`)
- [ ] Workspace ready (`.workspace/workspace.py`)

### **Knowledge Base First**
```python
from endor_cockpit.rag import query_vector_db

# Always start with knowledge base
results = query_vector_db("What does the resource guide tell me about {Resource} ?")

```

## 📋 **Step-by-Step Implementation Process**

### **Step 1: Research Phase (10 minutes)**

#### **1.1 Query Knowledge Base**
```python
# Check for existing patterns
results = query_vector_db("What does the resource guide tell me about {Resource} ?")
```

#### **1.2 Analyze OpenAPI Specification**
```bash
# Search for service endpoints
grep -i "{Resource}Service" .workspace/downloads/openapi-swagger.json
grep -A 20 -B 5 "{Resource}Service" .workspace/downloads/openapi-swagger.json
```

#### **1.3 Test with endorctl**
```bash
# Get live data structure
endorctl api list -r {Resource}
# Example: endorctl api list -r Project
```

### **Step 2: Live Data Analysis (15 minutes)**

#### **2.1 Get Live API Data**
```python
# .workspace/workspace.py
import sys
sys.path.insert(0, '..')
from endor_cockpit.api_client import APIClient
import os

client = APIClient()
namespace = os.getenv('ENDOR_NAMESPACE', 'endor-solutions-tgowan.cockpit')

# Test the endpoint
headers = client.default_headers
res = client.get(f"v1/namespaces/{namespace}/{resource}", headers=headers)
data = res.json()
objects = data.get("list", {}).get("objects", [])

if objects:
    sample = objects[0]
    print("Sample object keys:", list(sample.keys()))
    print("Sample object spec keys:", list(sample.get('spec', {}).keys()))
    print("Sample object meta keys:", list(sample.get('meta', {}).keys()))
```

#### **2.2 Document Field Structure**
- **Count fields**: Count fields in each nested object
- **Identify types**: Note field types and variations
- **Find enums**: Identify enum values from live data

### **Step 3: Model Implementation (20 minutes)**

#### **3.1 Create Base Models with Schema Drift Detection**
```python
class {Resource}Meta(BaseModel):
    """Metadata for {Resource}."""
    # Add fields based on live data analysis
    
class {Resource}Spec(BaseModel):
    """Specification for {Resource}."""
    # Add fields based on live data analysis
    
class {Resource}(BaseModel):
    """An Endor Labs {resource} entity."""
    meta: {Resource}Meta
    spec: {Resource}Spec
    tenant_meta: TenantMeta
    uuid: str
    
    @field_validator('*', mode='before')
    @classmethod
    def detect_schema_drift(cls, v, info):
        """Detect and log schema drift for unknown fields."""
        # Schema drift detection implementation
        return v
```

#### **3.2 Implement CRUD Operations with Universal Pattern**
```python
def list_{resource}s(client: APIClient, tenant_meta_namespace: str) -> List[{Resource}]:
    """List all {resource}s in the specified namespace."""
    try:
        headers = client.default_headers
        res = client.get(f"v1/namespaces/{tenant_meta_namespace}/{resource}s", headers=headers)
        data = res.json()
        objects = data.get("list", {}).get("objects", [])
        return [{Resource}(**item) for item in objects]
    except Exception as e:
        logger.error(f"Error listing {resource}s: {e}", exc_info=True)
        return []
```

### **Step 4: Testing and Refinement (15 minutes)**

#### **4.1 Test with Live Data**
```python
# Test the implementation
{resource}s = list_{resource}s(client, namespace)
print(f"Found {len({resource}s)} {resource}s")
if {resource}s:
    sample = {resource}s[0]
    print(f"Sample {resource}: {sample.uuid}")
```

#### **4.2 Handle Validation Errors**
- **Missing fields**: Add to model based on validation errors
- **Type mismatches**: Adjust field types based on actual data
- **Schema drift**: Update model fields based on warnings

## 🔧 **Quality Assurance Checklist**

### **✅ Implementation Complete When:**
- [ ] GET operations return actual data (not empty lists)
- [ ] Pydantic models validate without errors
- [ ] All CRUD operations work correctly
- [ ] Resource module follows established patterns
- [ ] Documentation updated with learnings
- [ ] Tests pass for all operations
- [ ] .workspace/workspace.py demonstrates working functionality

### **✅ Knowledge Base Updated When:**
- [ ] API patterns documented
- [ ] Common pitfalls recorded
- [ ] Workflow steps captured
- [ ] Quirks and learnings documented
- [ ] Repeatable process established
- [ ] Implementation guide created

## 📚 **Common Resource Types**

### **Projects**
- **Service**: `ProjectService`
- **Endpoint**: `/v1/namespaces/{tenant_meta.namespace}/projects`
- **Purpose**: Git repository representation
- **Key fields**: `meta`, `processing_status`, `spec`, `tenant_meta`

### **Findings**
- **Service**: `FindingService`
- **Endpoint**: `/v1/namespaces/{tenant_meta.namespace}/findings`
- **Purpose**: Security scan results
- **Key fields**: `meta`, `severity`, `status`, `details`

### **Policies**
- **Service**: `PolicyService`
- **Endpoint**: `/v1/namespaces/{tenant_meta.namespace}/policies`
- **Purpose**: Security policy definitions
- **Key fields**: `meta`, `rules`, `actions`, `scope`

## 🚨 **Common Issues & Solutions**

### **Empty Results**
```python
# Check namespace format
namespace = "endor-solutions-tgowan.cockpit"  # Correct
namespace = "namespace-uuid-here"            # Wrong

# Check endpoint format
endpoint = f"v1/namespaces/{namespace}/projects"  # Correct
endpoint = f"v1/namespaces/{uuid}/projects"       # Wrong
```

### **Validation Errors**
```python
# Check model against live data
endorctl api list -r Project > live_data.json
# Compare with Pydantic model fields
```

### **Authentication Issues**
```python
# Use resource modules, not direct API calls
projects = list_projects(client, namespace)  # Correct
response = client.get(endpoint)             # May fail
```

## 📊 **Success Metrics**

### **Implementation Success**
- [ ] Resource module created and working
- [ ] All CRUD operations functional
- [ ] Pydantic models validate correctly
- [ ] Documentation complete
- [ ] Knowledge base updated
- [ ] .workspace cleaned up

### **Quality Indicators**
- [ ] No one-off scripts in .workspace
- [ ] Single .workspace/workspace.py file for experimentation
- [ ] All learnings documented
- [ ] Repeatable process established
- [ ] Ready for next resource implementation

---

*This workflow ensures consistent, high-quality implementation of all Endor Labs resources in the Cockpit SDK.*
