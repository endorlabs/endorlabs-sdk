# Developer Persona Guide

> **SDK Development, Testing, and Contribution**

## 🚀 **Quick Start**

### **5-Minute Setup**
1. **Environment**: Set `ENDOR_API`, `ENDOR_API_CREDENTIALS_KEY`, `ENDOR_API_CREDENTIALS_SECRET`
2. **Virtual Environment**: `uv venv` and activate
3. **Install**: `uv pip install -e .`
4. **Knowledge Base**: Initialize RAG capabilities with `uv run python workflow/init_vector_db.py`
5. **Test**: `uv run pytest tests/test_integration.py -v`
6. **Security**: `endorctl scan` before any changes
7. **Lint**: `uv run ruff check . --fix`

### **Development Workflow**
```bash
# 1. Pre-development checklist
uv run ruff check .          # Lint
uv run ruff check . --fix    # Auto-fix
uv run ruff format .         # Format
uv run pytest               # Test
endorctl scan               # Security

# 2. Resource implementation workflow
#    a. Query RAG knowledge base first
#    b. Analyze OpenAPI spec for {Resource}Service endpoints
#    c. Implement GET operations first to understand structure
#    d. Create Pydantic models from live data + API spec
#    e. Document all quirks and learnings

# 3. Make changes
# 4. Repeat checklist
# 5. Commit with conventional commits
```

---

## 🏗️ **Architecture & Design Principles**

### **Project Structure**
```
endor_cockpit/
├── api_client.py          # Core API client with retry, rate limiting, logging
├── resources/            # Resource-specific modules
│   ├── __init__.py
│   ├── namespaces.py     # Namespace operations
│   └── [other_resources] # Additional resources
└── models/               # Pydantic data models
    └── [model_files]
```

### **Resource Module Pattern**
Each resource module follows this pattern:
- **List operations**: `list_{resource}()`
- **Get operations**: `get_{resource}()`
- **Create operations**: `create_{resource}()`
- **Update operations**: `update_{resource}()`
- **Delete operations**: `delete_{resource}()`

### **Function Signatures**
```python
def create_resource(
    client: APIClient,
    tenant_meta_namespace: str,  # Use canonical namespace, not UUID
    payload: CreateResourcePayload
) -> Optional[Resource]:
    """Create resource with proper error handling."""
```

### **Critical API Patterns**
- **Path parameters**: Use `tenant_meta.namespace` (canonical namespace) not `namespace_uuid`
- **Response structure**: API returns `{"list": {"objects": [...]}}` not direct arrays
- **Authentication**: Use resource modules, not direct API calls
- **OpenAPI analysis**: Look for `{Resource}Service` endpoints in spec

### **API Implementation Patterns**

**Endpoint Pattern**:
```
GET    /v1/namespaces/{tenant_meta.namespace}/projects
POST   /v1/namespaces/{tenant_meta.namespace}/projects
GET    /v1/namespaces/{tenant_meta.namespace}/projects/{uuid}
DELETE /v1/namespaces/{tenant_meta.namespace}/projects/{uuid}
```

**Critical Parameters**:
- **Path parameter**: `tenant_meta.namespace` (canonical namespace name)
- **NOT**: `namespace_uuid` or `tenant_namespace`
- **Example**: `endor-solutions-tgowan.cockpit`

**Response Structure**:
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

---

## 🧭 **API Navigation & Resource Implementation**

### **OpenAPI Specification Analysis**
```bash
# Find service endpoints in OpenAPI spec
grep -i "{Resource}Service" tmp/openapiv2.swagger.json
# Examples: ProjectService, FindingService, PolicyService

# Extract endpoint patterns
grep -A 20 -B 5 "{Resource}Service" tmp/openapiv2.swagger.json
```

### **Critical API Patterns**
- **Endpoint pattern**: `/v1/namespaces/{tenant_meta.namespace}/{resource}`
- **Path parameter**: Use `tenant_meta.namespace` (canonical namespace) not `namespace_uuid`
- **Response structure**: `{"list": {"objects": [...]}}` not direct arrays
- **Authentication**: Use resource modules, not direct API calls

### **Resource Implementation Workflow**

#### **Step 1: Research Phase (10 minutes)**

**1.1 Query Knowledge Base**
```python
# Check for existing patterns
results = query_vector_db("How do I implement {Resource} resources?")
results = query_vector_db("What are the common pitfalls for {resource} implementation?")
```

**1.2 Analyze OpenAPI Specification**
```bash
# Search for service endpoints
grep -i "{Resource}Service" tmp/openapiv2.swagger.json
grep -A 20 -B 5 "{Resource}Service" tmp/openapiv2.swagger.json
```

**1.3 Test with endorctl**
```bash
# Get live data structure
endorctl api list -r {Resource}
# Example: endorctl api list -r Project
```

#### **Step 2: Live Data Analysis (15 minutes)**

**2.1 Get Live API Data**
```python
# workspace/workspace.py
import sys
sys.path.insert(0, '..')
from endor_cockpit.api_client import APIClient
import os

client = APIClient()
namespace = os.getenv('ENDOR_NAMESPACE', 'endor-solutions-tgowan.cockpit')

# Test the endpoint
headers = client.default_headers
res = client.get(f"v1/namespaces/{namespace}/{resource}", headers=headers)
print(res.json())
```

**2.2 Create Pydantic Models**
```python
# Model from live data + API spec
class Resource(BaseModel):
    meta: ResourceMeta
    spec: ResourceSpec
    tenant_meta: TenantMeta
    uuid: str
```

#### **Step 3: Resource Module Implementation**
```python
def list_resources(client: APIClient, tenant_meta_namespace: str) -> List[Resource]:
    """List all resources in the specified namespace."""
    res = client.get(f"v1/namespaces/{tenant_meta_namespace}/{resources}")
    data = res.json()
    resources_data = data.get("list", {}).get("objects", [])
    return [Resource(**item) for item in resources_data]
```

#### **Step 4: Testing Strategy**

**4.1 Collaborative Workspace**
```python
# workspace/workspace.py - Single file for experimentation
import sys
sys.path.insert(0, '..')
from endor_cockpit.api_client import APIClient
from endor_cockpit.resources import resource

client = APIClient()
namespace = os.getenv('ENDOR_NAMESPACE', 'endor-solutions-tgowan.cockpit')

# Test operations
resources_list = resource.list_resources(client, namespace)
print(f"Found {len(resources_list)} resources")
```

**4.2 Validation Steps**
1. **Check namespace exists**: Verify canonical namespace format
2. **Test GET operations**: Ensure endpoints return data
3. **Validate models**: Confirm Pydantic models match API response
4. **Test CRUD operations**: Verify create, update, delete work
5. **Document quirks**: Record any API discrepancies

### **Common Pitfalls & Solutions**

**❌ Wrong Path Parameter**
```python
# WRONG - This will fail
client.get(f"v1/namespaces/{namespace_uuid}/projects")

# CORRECT - Use canonical namespace
client.get(f"v1/namespaces/{tenant_meta_namespace}/projects")
```

**❌ Wrong Response Parsing**
```python
# WRONG - This will fail
data = res.json().get("projects", [])

# CORRECT - Use list.objects structure
data = res.json().get("list", {}).get("objects", [])
```

**❌ Direct API Calls**
```python
# WRONG - Direct calls may fail due to auth issues
response = client.get("v1/namespaces/...")

# CORRECT - Use resource modules
projects = list_projects(client, namespace)
```

**❌ Missing Update Mask**
```python
# WRONG - Missing update_mask parameter
payload = UpdateProjectPayload(tags=["new-tag"])

# CORRECT - Include update_mask
payload = UpdateProjectPayload(
    tags=["new-tag"],
    update_mask=["tags"]
)
```

**❌ Unicode Encoding Issues (Windows)**
```python
# WRONG - Unicode emojis cause encoding errors
print(f"✅ Success")

# CORRECT - Use ASCII characters
print(f"[SUCCESS] Success")
```

**❌ Import Path Issues**
```python
# WRONG - Imports before path setup
from endor_cockpit.api_client import APIClient
sys.path.insert(0, '..')

# CORRECT - Set up paths before imports
sys.path.insert(0, '..')
from endor_cockpit.api_client import APIClient
```

### **Success Pattern**
```python
# CORRECT: Use canonical namespace and resource modules
projects = list_projects(client, "endor-solutions-tgowan.cockpit")

# WRONG: Direct API calls with wrong parameters
response = client.get("v1/namespaces/uuid-here/projects")
```

---

## 🔧 **Code Standards & Quality**

### **Python Version Support**
- **Minimum**: Python 3.11
- **Maximum**: Python 3.13 (exclusive)
- **Testing**: Test on 3.11, 3.12, 3.13

### **Dependencies**
- **Core**: `requests==2.32.5`, `pydantic==2.12.3`
- **Development**: `pytest==8.4.2`, `ruff==0.14.1`, `pytest-cov==6.0.0`
- **Security**: `endorctl` (for scanning)

### **Pre-Development Checklist**
- [ ] Line length ≤ 88 characters
- [ ] Imports sorted and unused removed
- [ ] No trailing whitespace or blank line whitespace
- [ ] F-strings only with placeholders
- [ ] Dependencies pinned (no `latest`)

### **Common Linting Fixes**
- **E501**: Break long lines with parentheses/backslashes
- **F401**: Remove unused imports
- **W291/W293**: Remove trailing/blank line whitespace
- **F541**: Remove `f` prefix from strings without placeholders
- **I001**: Sort import blocks

---

## 🧪 **Testing Standards**

### **Test Structure**
```python
def test_create_namespace_success():
    """Test successful namespace creation."""
    
def test_create_namespace_validation_error():
    """Test validation error handling."""
    
def test_create_namespace_api_error():
    """Test API error handling."""
```

### **Test Categories**
- **Unit tests**: Individual function testing
- **Integration tests**: API interaction testing
- **Security tests**: Security scan validation
- **Performance tests**: Load and stress testing

### **Test Markers**
```python
@pytest.mark.slow
def test_large_dataset_processing():
    """Test with large datasets."""

@pytest.mark.integration
def test_api_integration():
    """Test real API integration."""
```

### **Integration Test Patterns**
```python
def test_namespace_hierarchy(api_client, tenant_namespace):
    """Test namespace hierarchy operations."""
    parent_name = f"integration-test-parent-{int(time.time())}"
    
    # Create parent namespace
    parent_namespace = create_test_namespace(
        api_client, tenant_namespace, parent_name, "Parent namespace"
    )
    
    # Create canonical parent name
    canonical_parent = f"{tenant_namespace}.{parent_name}"
    
    # Create child namespace using canonical parent
    child_namespace = create_test_namespace(
        api_client, canonical_parent, child_name, "Child namespace"
    )
    
    # List namespaces under canonical parent
    child_namespaces = namespaces.list_namespaces(api_client, canonical_parent)
    assert len(child_namespaces) > 0
```

---

## 🔒 **Security Integration**

### **Security-First Development**
- **Always scan**: `endorctl scan` before any code changes
- **Scan scenarios**: Package changes, first-party code, dependency updates
- **No PII**: This project handles no PII data
- **Secure logging**: Filter sensitive data from logs

### **Security Scanning Requirements**
```bash
# Required before any code changes
endorctl scan

# For dependency changes
endorctl scan --dependencies

# For first-party code changes
endorctl scan --sast
```

### **Environment Security**
- **Credentials**: Use environment variables only
- **No hardcoded secrets**: All secrets via env vars
- **Secure logging**: No sensitive data in logs
- **Input validation**: Validate all inputs

---

## 📚 **API Client Design**

### **Authentication**
```python
class APIClient:
    def __init__(self):
        # Auto-authentication via environment variables
        # Token refresh handling
        # Rate limiting
```

### **Error Handling**
- **HTTP errors**: Proper status code handling
- **Retries**: Exponential backoff for transient failures
- **Rate limiting**: Respect API limits
- **Validation**: Pydantic model validation

### **Logging**
- **Secure filters**: No PII or sensitive data
- **Structured logging**: JSON format for production
- **Context preservation**: Operation context in logs

---

## 🛠️ **Development Tools**

### **Code Quality Tools**
- **Linting**: `ruff check .`
- **Formatting**: `ruff format .`
- **Testing**: `pytest --cov=endor_cockpit`
- **Security**: `endorctl scan`

### **CI/CD Integration**
- **Automated testing**: Multi-version Python testing
- **Security scanning**: Integrated endorctl scans
- **Caching**: Efficient dependency caching
- **Parallel jobs**: Optimized build times

### **Quality Gates**
- **Linting**: Must pass ruff checks
- **Formatting**: Must pass black checks
- **Testing**: Must pass all tests
- **Security**: Must pass endorctl scan

---

## 📖 **Documentation Standards**

### **Function Documentation**
```python
def create_namespace(
    client: APIClient,
    parent_namespace: str,
    payload: CreateNamespacePayload
) -> Optional[Namespace]:
    """
    Create a new namespace within the specified parent namespace.
    
    Args:
        client: Authenticated API client
        parent_namespace: Parent namespace name (canonical format)
        payload: Namespace creation payload
        
    Returns:
        Created namespace or None if failed
        
    Raises:
        ValidationError: If payload is invalid
        HTTPError: If API request fails
    """
```

### **Example Usage**
```python
# Example: Creating a namespace
from endor_cockpit.api_client import APIClient
from endor_cockpit.resources.namespace import CreateNamespacePayload, NamespaceMeta

client = APIClient()
payload = CreateNamespacePayload(
    meta=NamespaceMeta(
        name="my-namespace",
        description="Created by developer"
    )
)
namespace = create_namespace(client, "tenant.namespace", payload)
```

---

## 🎯 **Contributing Guidelines**

### **Development Process**
1. **Fork the repository**
2. **Create a feature branch**
3. **Make your changes**
4. **Run tests and linting**
5. **Submit a pull request**

### **Code Review Checklist**
- [ ] All tests passing
- [ ] No linting errors
- [ ] Security scan clean
- [ ] Documentation updated
- [ ] Examples provided

### **Commit Message Format**
```
feat(namespaces): add update_namespace function
fix(api_client): handle 403 errors gracefully
docs(readme): update installation instructions
test(integration): add namespace hierarchy tests
```

---

## 🔍 **Troubleshooting**

### **Common Issues**

#### **403 Forbidden Errors**
1. Check if using canonical naming instead of UUIDs
2. Verify API key has required permissions
3. Confirm parent namespace exists and is accessible

#### **Empty Results (0 resources found)**
1. **Check path parameter**: Use `tenant_meta.namespace` not `namespace_uuid`
2. **Check response parsing**: Use `list.objects` not direct array
3. **Check namespace format**: Use canonical format like `endor-solutions-tgowan.cockpit`
4. **Use resource modules**: Don't bypass with direct API calls

#### **Import Errors**
1. Ensure all required classes are imported
2. Check if SDK classes are missing
3. Verify package installation

#### **Validation Errors**
1. Check Pydantic field definitions
2. Ensure optional fields are properly defined
3. Handle empty values gracefully
4. **Model from live data**: Use `endorctl api list -r Resource` for reference

### **Debugging Tools**
- **API Client Logging**: Enable debug logging for API calls
- **Integration Tests**: Use real API endpoints for validation
- **Security Scans**: Run `endorctl scan` to identify issues

---

## 📚 **Related Documentation**

- **[Architecture Guide](./architecture.md)**: Endor Data Model deep-dive
- **[API Quirks](./api-quirks.md)**: Known API discrepancies and workarounds
- **[Testing Guide](./testing-guide.md)**: Comprehensive testing patterns
- **[Contributing Guide](./contributing.md)**: How to extend the SDK
- **[Project Implementation Guide](../../knowledge/endor-data-model/project-implementation-guide.md)**: Complete Project resource implementation
- **[Resource Implementation Workflow](../../agents/resource-implementation-workflow.md)**: Step-by-step process for any resource

---

## 🎉 **Success Metrics**

When everything is working correctly, you should see:
- ✅ All integration tests passing
- ✅ Namespace hierarchy operations working
- ✅ Security scanning integration working
- ✅ Error handling working gracefully
- ✅ Rate limiting compliance

**The Endor Cockpit SDK is production-ready and fully validated against the live Endor Labs API!** 🚀
