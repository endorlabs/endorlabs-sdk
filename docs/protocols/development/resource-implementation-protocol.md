# Resource Implementation Protocol

> **L2 (Task-Specific) - Comprehensive resource implementation workflow using Resource Guide**

## Overview

This protocol provides detailed steps for implementing new Endor Labs resources in the SDK, using the Resource Guide as the canonical source for API patterns, examples, and specifications. This ensures consistency with documented patterns and real-world usage.

## Updated Implementation Phases (Using Resource Guide)

### Phase 0: Resource Guide Analysis (MANDATORY)

**CRITICAL**: This phase must be completed before any implementation begins. The Resource Guide contains validated examples, API patterns, and specifications that ensure consistency with real-world usage.

#### 0.1 Analyze Resource Guide Entry
- [ ] **Review Resource Guide**: Check `Resource-Guide.md` for the resource
- [ ] **Example Output**: Use the JSON example as the canonical data structure
- [ ] **Description**: Understand the resource's purpose and characteristics
- [ ] **Service Name**: Note the related service name (e.g., `FindingService`)
- [ ] **URL Endpoints**: Review all available endpoints and HTTP methods
- [ ] **API Patterns**: Note any resource-specific patterns or requirements

#### 0.2 Validate Against Base Class Architecture
- [ ] **Universal Attributes**: Ensure all universal fields are present in example
- [ ] **Conditional Attributes**: Identify which conditional attributes are used
- [ ] **Base Class Compatibility**: Verify the resource can inherit from BaseResource
- [ ] **API Pattern Support**: Confirm advanced patterns (filtering, masking, pagination) are supported

#### 0.3 Create Implementation Matrix
Document the complete mapping between Resource Guide and base class architecture:
- [ ] **Universal fields**: All universal attributes present and correct
- [ ] **Conditional fields**: Which conditional attributes are used
- [ ] **Resource-specific fields**: Fields unique to this resource type
- [ ] **API operations**: Which CRUD operations are supported
- [ ] **Advanced patterns**: Which advanced API patterns are supported

## Updated Implementation Approach (Using Base Classes)

### Phase 1: Base Class Implementation
**Use the Resource Guide example as the canonical structure and inherit from base classes for consistency.**

#### 1.1 Create Resource-Specific Models
```python
# Use Resource Guide example as canonical structure
# Inherit from base classes for consistency

class ResourceMeta(BaseMeta):
    """Resource metadata extending BaseMeta."""
    # Only add resource-specific fields here
    # Universal fields inherited from BaseMeta

class ResourceSpec(BaseSpec):
    """Resource specification extending BaseSpec."""
    # Add resource-specific spec fields based on Resource Guide example
    # Use Optional for API variations
    # Use Union types for flexible fields

class Resource(BaseResource):
    """Resource entity extending BaseResource."""
    # Resource-specific fields only
    spec: ResourceSpec = Field(..., description="Resource specification")  # type: ignore
    
    # Add conditional attributes if present in Resource Guide example
    # context: Optional[Context] = Field(None, description="Contextual information")
    # processing_status: Optional[ProcessingStatus] = Field(None, description="Processing state")
    # ingested_object: Optional[IngestedObject] = Field(None, description="Ingestion metadata")
    
    def __init__(self, **data):
        # Convert spec to ResourceSpec if it's a dict
        if 'spec' in data and isinstance(data['spec'], dict):
            data['spec'] = ResourceSpec(**data['spec'])
        super().__init__(**data)
```

#### 1.2 Use BaseResourceOperations for CRUD
```python
def _get_resource_ops(client: APIClient) -> BaseResourceOperations:
    """Get BaseResourceOperations instance for this resource."""
    return BaseResourceOperations(client, "ResourceName", Resource)

def list_resources(
    client: APIClient, 
    tenant_meta_namespace: str,
    list_params: Optional[ListParameters] = None,
    **kwargs
) -> List[Resource]:
    """List resources with advanced filtering and pagination."""
    ops = _get_resource_ops(client)
    return ops.list(tenant_meta_namespace, list_params, **kwargs)  # type: ignore

def get_resource(
    client: APIClient, 
    tenant_meta_namespace: str, 
    resource_uuid: str
) -> Optional[Resource]:
    """Get specific resource by UUID."""
    ops = _get_resource_ops(client)
    return ops.get(tenant_meta_namespace, resource_uuid)  # type: ignore

def create_resource(
    client: APIClient,
    tenant_meta_namespace: str,
    payload: CreateResourcePayload
) -> Optional[Resource]:
    """Create new resource."""
    ops = _get_resource_ops(client)
    return ops.create(tenant_meta_namespace, payload)  # type: ignore

def update_resource(
    client: APIClient,
    tenant_meta_namespace: str,
    resource_uuid: str,
    payload: UpdateResourcePayload,
    update_mask: List[str]
) -> Optional[Resource]:
    """Update resource with field masking."""
    ops = _get_resource_ops(client)
    return ops.update(tenant_meta_namespace, resource_uuid, payload, update_mask)  # type: ignore

def delete_resource(
    client: APIClient,
    tenant_meta_namespace: str,
    resource_uuid: str
) -> bool:
    """Delete resource."""
    ops = _get_resource_ops(client)
    return ops.delete(tenant_meta_namespace, resource_uuid)
```

### Phase 2: Legacy Implementation Phase

#### 1.1 Analyze OpenAPI Specification
```bash
# Search for service endpoints
grep -i "{Resource}Service" .workspace/downloads/openapi-swagger.json
grep -A 20 -B 5 "{Resource}Service" .workspace/downloads/openapi-swagger.json

# Extract complete resource schema
grep -A 100 '"v1{Resource}":' .workspace/downloads/openapi-swagger.json
grep -A 100 '"v1{Resource}Spec":' .workspace/downloads/openapi-swagger.json
```

#### 1.2 Test with endorctl
```bash
# Get live data structure
endorctl api list -r {Resource}
# Example: endorctl api list -r Project
```

#### 1.3 Live Data Analysis
```python
# .workspace/validate_{resource}.py
import sys
sys.path.insert(0, '..')
from endor_cockpit.api_client import APIClient
import os
import json

client = APIClient()
namespace = os.getenv('ENDOR_NAMESPACE', 'endor-solutions-tgowan.cockpit')

# Test the endpoint
res = client.get(f"v1/namespaces/{namespace}/{resource}")
data = res.json()

# Print complete structure for analysis
print("=== API Response Structure ===")
print(json.dumps(data, indent=2))

# Extract and analyze objects
objects = data.get("list", {}).get("objects", [])
if objects:
    print("\n=== Sample Object Structure ===")
    print(json.dumps(objects[0], indent=2))
    
    # Analyze field types
    print("\n=== Field Analysis ===")
    sample = objects[0]
    for key, value in sample.items():
        print(f"{key}: {type(value).__name__} = {value}")
```

#### 1.4 Create Validation Matrix
Document the complete mapping between OpenAPI spec and live data:
| Field Name | OpenAPI Type | Live Data Type | Required | Read-Only | Notes |
|------------|--------------|----------------|----------|-----------|-------|
| uuid | string | string | Yes | Yes | Auto-generated |
| meta | object | object | Yes | No | Metadata object |
| spec | object | object | Yes | No | Specification object |
| ... | ... | ... | ... | ... | ... |

### Phase 2: Base Class Implementation Phase

#### 2.1 Create Resource-Specific Models
```python
# Use Resource Guide example as canonical structure
# Inherit from base classes for consistency

class ResourceMeta(BaseMeta):
    """Resource metadata extending BaseMeta."""
    # Only add resource-specific fields here
    # Universal fields inherited from BaseMeta

class ResourceSpec(BaseSpec):
    """Resource specification extending BaseSpec."""
    # Add resource-specific spec fields based on Resource Guide example
    # Use Optional for API variations
    # Use Union types for flexible fields

class Resource(BaseResource):
    """Resource entity extending BaseResource."""
    # Resource-specific fields only
    spec: ResourceSpec = Field(..., description="Resource specification")  # type: ignore
    
    # Add conditional attributes if present in Resource Guide example
    # context: Optional[Context] = Field(None, description="Contextual information")
    # processing_status: Optional[ProcessingStatus] = Field(None, description="Processing state")
    # ingested_object: Optional[IngestedObject] = Field(None, description="Ingestion metadata")
    
    def __init__(self, **data):
        # Convert spec to ResourceSpec if it's a dict
        if 'spec' in data and isinstance(data['spec'], dict):
            data['spec'] = ResourceSpec(**data['spec'])
        super().__init__(**data)
    
    @field_validator("*", mode="before")
    @classmethod
    def detect_schema_drift(cls, v, info):
        """Detect and log schema drift for unknown fields."""
        if info.field_name == "spec" and isinstance(v, dict):
            # Log unknown fields for schema drift detection in spec
            known_fields = {
                # Add resource-specific spec fields here
            }
            unknown_fields = set(v.keys()) - known_fields
            if unknown_fields:
                logger.warning(
                    f"Schema drift detected in {info.field_name}: "
                    f"unknown fields {unknown_fields}"
                )
        return v
```

### Phase 3: Documentation Context Phase

#### 3.1 Query Knowledge Base for Context
```bash
# Query for documentation context and examples
python -m holocron query "How do I implement {Resource} resources?"
python -m holocron query "What are common pitfalls for {resource} implementation?"
python -m holocron query "What are the API patterns for {Resource}Service?"
python -m holocron query "What are the best practices for {resource} operations?"
python -m holocron query "What are the common use cases for {resource} resources?"
```

#### 3.2 Extract Documentation Context
Use holocron results to enhance:
- **Docstrings**: Add context and examples from knowledge base
- **Resource Documentation**: Include best practices and common patterns
- **Error Messages**: Add helpful context from known issues
- **Examples**: Include real-world usage patterns

### Phase 4: CRUD Operations Phase

#### 4.0 Operation Availability Check (MANDATORY)
```python
# Check which operations are available for this resource
# Based on API analysis: POST (97.1%), GET_LIST (82.9%), GET_BY_UUID (81.4%), DELETE (77.1%)
# PATCH operations do NOT exist (0% coverage)

def check_operation_availability(resource_name: str) -> dict:
    """Check which operations are available for a resource."""
    # This should be based on the actual API analysis results
    # For now, assume standard pattern unless resource is in limited list
    
    limited_operations = {
        'ai-embeddings-requests', 'ai-queries', 'artifact-operations', 'batch',
        'certificate-requests', 'client-logs', 'filehash-query-request',
        'ghe-app-registration', 'notification-actions', 'optimized-queries',
        'oss-dependency-requests', 'policy', 'queries', 'sbom-export',
        'scan-log-requests', 'segment-index-request', 'segment-match-validate-request',
        'segment-query-request', 'service-token', 'support-access-requests',
        'telemetries', 'ui-telemetries', 'vector-store-data', 'vex-export'
    }
    
    read_only_resources = {
        'master-toolchain-profiles', 'master-toolchain-versions',
        'supported-toolchain-profiles'
    }
    
    if resource_name in limited_operations:
        return {
            'GET_LIST': False,
            'GET_BY_UUID': False,
            'POST': True,
            'DELETE': False
        }
    elif resource_name in read_only_resources:
        return {
            'GET_LIST': True,
            'GET_BY_UUID': True,
            'POST': False,
            'DELETE': False
        }
    else:
        # Standard resources have most operations
        return {
            'GET_LIST': True,
            'GET_BY_UUID': True,
            'POST': True,
            'DELETE': True
        }
```

#### 4.1 List Operation (Conditional)
```python
def list_resources(client: APIClient, tenant_meta_namespace: str) -> List[Resource]:
    """List all resources in the specified namespace."""
    try:
        headers = client.default_headers
        res = client.get(f"v1/namespaces/{tenant_meta_namespace}/{resources}", headers=headers)
        data = res.json()
        # Handle the actual API response structure: list.objects
        resources_data = data.get("list", {}).get("objects", [])
        return [Resource(**item) for item in resources_data]
    except Exception as e:
        logger.error(f"Error listing {resources}: {e}", exc_info=True)
        return []
```

#### 4.2 Get Operation
```python
def get_resource(client: APIClient, tenant_meta_namespace: str, resource_uuid: str) -> Optional[Resource]:
    """Get a specific resource by UUID."""
    try:
        headers = client.default_headers
        res = client.get(f"v1/namespaces/{tenant_meta_namespace}/{resources}/{resource_uuid}", headers=headers)
        data = res.json()
        return Resource(**data)
    except Exception as e:
        logger.error(f"Error getting {resource} {resource_uuid}: {e}", exc_info=True)
        return None
```

#### 4.3 Create Operation
```python
def create_resource(client: APIClient, tenant_meta_namespace: str, payload: CreateResourcePayload) -> Optional[Resource]:
    """Create a new resource."""
    try:
        headers = client.default_headers
        headers.update({"Accept": "application/json", "Content-Type": "application/json"})
        
        request_data = {
            "object": {
                "tenant_meta": {"namespace": tenant_meta_namespace},
                **payload.model_dump(),
            }
        }
        
        res = client.post(f"v1/namespaces/{tenant_meta_namespace}/{resources}", headers=headers, data=request_data)
        data = res.json()
        return Resource(**data)
    except Exception as e:
        logger.error(f"Error creating {resource}: {e}", exc_info=True)
        return None
```

#### 4.4 Update Operation (POST Upsert Pattern)
```python
def update_resource(client: APIClient, tenant_meta_namespace: str, resource_uuid: str, payload: UpdateResourcePayload) -> Optional[Resource]:
    """Update an existing resource using POST upsert pattern."""
    try:
        headers = client.default_headers
        headers.update({"Accept": "application/json", "Content-Type": "application/json"})
        
        # Get current resource to include required fields
        current_resource = get_resource(client, tenant_meta_namespace, resource_uuid)
        if not current_resource:
            logger.error(f"{Resource} {resource_uuid} not found")
            return None
        
        # Build request data with upsert structure
        request_data = {
            "object": {
                "uuid": resource_uuid,
                "tenant_meta": current_resource.tenant_meta.model_dump(),
                "meta": {
                    "name": current_resource.meta.name,  # Required field
                    **(payload.meta.model_dump(exclude_none=True) if payload.meta else {}),
                },
                "spec": {
                    **current_resource.spec.model_dump(),
                    **(payload.spec.model_dump(exclude_none=True) if payload.spec else {}),
                },
            }
        }
        
        logger.info(f"Updating {resource} {resource_uuid} using POST upsert")
        
        # Use POST for updates (upsert pattern)
        res = client.post(f"v1/namespaces/{tenant_meta_namespace}/{resources}", headers=headers, data=request_data)
        
        if res.status_code == 200:
            data = res.json()
            return Resource(**data)
        else:
            logger.error(f"Failed to update {resource} {resource_uuid}: {res.status_code} - {res.text}")
            return None
    except Exception as e:
        logger.error(f"Error updating {resource} {resource_uuid}: {e}", exc_info=True)
        return None
```

#### 4.5 Delete Operation
```python
def delete_resource(client: APIClient, tenant_meta_namespace: str, resource_uuid: str) -> bool:
    """Delete a resource."""
    try:
        headers = client.default_headers
        res = client.delete(f"v1/namespaces/{tenant_meta_namespace}/{resources}/{resource_uuid}", headers=headers)
        return res.status_code == 200
    except Exception as e:
        logger.error(f"Error deleting {resource} {resource_uuid}: {e}", exc_info=True)
        return False
```

### Phase 5: Testing Phase

#### 5.1 Test Structure
```python
@pytest.mark.integration
class TestResource:
    """Test cases for Resource operations."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test environment."""
        self.client = APIClient()
        self.namespace = os.getenv("ENDOR_NAMESPACE", "endor-solutions-tgowan.cockpit")
        self.resources = resource.list_resources(self.client, self.namespace)
        if not self.resources:
            pytest.skip("No resources available for testing")
    
    def test_resource_get_list(self):
        """Test GET resources operation."""
        resources_list = resource.list_resources(self.client, self.namespace)
        assert isinstance(resources_list, list)
        assert len(resources_list) > 0
    
    def test_resource_get_by_uuid(self):
        """Test GET resource by UUID operation."""
        test_resource = self.resources[0]
        retrieved_resource = resource.get_resource(self.client, self.namespace, test_resource.uuid)
        assert retrieved_resource is not None
        assert retrieved_resource.uuid == test_resource.uuid
    
    def test_resource_post_tags(self):
        """Test POST upsert operations using tag management."""
        # Test tag management operations
        pass
    
    def test_resource_structure_analysis(self):
        """Test and analyze resource structure."""
        # Analyze resource fields
        pass
```

### Phase 6: Documentation Phase

#### 6.1 Resource Documentation Template
Create `docs/endor-data-model/{resource}.md` following project.md template:

```markdown
# {Resource} Resource Deep-Dive

> **Comprehensive guide to {Resource} resources in Endor Labs platform**

## Architecture
### Resource Structure
### Core Concepts
### Lifecycle

## Data Model
### SDK Implementation
### Mutable vs Immutable Fields
### Field Validation

## Operations
### CRUD Operations
### Tag Management
### Relationship Patterns

## Common Issues
### Issue: [Problem Description]
**Cause**: [Root cause]
**Solution**: [How to fix]

## Testing Patterns
### CRUD Testing
### Integration Testing

## Schema Mismatch Prevention & Resolution

### Critical Schema Validation Steps

#### Pre-Implementation Validation (MANDATORY)
Before writing any code, complete these validation steps:

1. **OpenAPI Schema Extraction**
```bash
# Extract complete resource schema
grep -A 100 '"v1{Resource}":' .workspace/downloads/openapi-swagger.json
grep -A 100 '"v1{Resource}Spec":' .workspace/downloads/openapi-swagger.json

# Extract service endpoints
grep -A 30 -B 5 "{Resource}Service" .workspace/downloads/openapi-swagger.json
```

2. **Live Data Analysis**
```python
# .workspace/validate_{resource}.py
import sys
sys.path.insert(0, '..')
from endor_cockpit.api_client import APIClient
import os
import json

client = APIClient()
namespace = os.getenv('ENDOR_NAMESPACE', 'endor-solutions-tgowan.cockpit')

# Test the endpoint
res = client.get(f"v1/namespaces/{namespace}/{resource}")
data = res.json()

# Print complete structure for analysis
print("=== API Response Structure ===")
print(json.dumps(data, indent=2))

# Extract and analyze objects
objects = data.get("list", {}).get("objects", [])
if objects:
    print("\n=== Sample Object Structure ===")
    print(json.dumps(objects[0], indent=2))
    
    # Analyze field types
    print("\n=== Field Analysis ===")
    sample = objects[0]
    for key, value in sample.items():
        print(f"{key}: {type(value).__name__} = {value}")
```

3. **Create Validation Matrix**
| Field Name | OpenAPI Type | Live Data Type | Required | Read-Only | Notes |
|------------|--------------|----------------|----------|-----------|-------|
| uuid | string | string | Yes | Yes | Auto-generated |
| meta | object | object | Yes | No | Metadata object |
| spec | object | object | Yes | No | Specification object |
| ... | ... | ... | ... | ... | ... |

#### Common Schema Mismatches & Solutions

**Issue: Missing Required Fields**
- **Symptoms**: API returns 400/422 errors on create/update
- **Root Cause**: Required fields missing from Pydantic model
- **Solution**: Add all required fields from OpenAPI spec to model
- **Prevention**: Always check `required` array in OpenAPI spec

**Issue: Wrong Field Types**
- **Symptoms**: Validation errors, type mismatches
- **Root Cause**: Field types don't match OpenAPI specification
- **Solution**: Update field types to match spec exactly
- **Prevention**: Compare field types between spec and live data

**Issue: Read-Only Fields Marked Mutable**
- **Symptoms**: Update operations fail, unexpected behavior
- **Root Cause**: Read-only fields included in update payloads
- **Solution**: Mark read-only fields appropriately in Pydantic model
- **Prevention**: Check `readOnly: true` in OpenAPI spec

**Issue: Missing Nested Object Fields**
- **Symptoms**: Incomplete data, missing nested information
- **Root Cause**: Nested objects not fully modeled
- **Solution**: Model all nested object fields from OpenAPI spec
- **Prevention**: Analyze complete nested object structure

**Issue: Non-Existent Operations**
- **Symptoms**: 404 errors, operations not found
- **Root Cause**: Implementing operations that don't exist in API
- **Solution**: Remove non-existent operations, check available endpoints
- **Prevention**: Validate all operations against OpenAPI spec

**Issue: Wrong Endpoint Patterns**
- **Symptoms**: 404 errors, wrong API paths
- **Root Cause**: Using incorrect endpoint patterns
- **Solution**: Use correct endpoint patterns from OpenAPI spec
- **Prevention**: Extract endpoint patterns from OpenAPI spec

#### Schema Validation Checklist

**Pre-Implementation (MANDATORY)**
- [ ] **OpenAPI spec analyzed**: Complete schema extracted and documented
- [ ] **Live data tested**: Real API responses analyzed and documented
- [ ] **Field mapping complete**: All fields mapped between spec and live data
- [ ] **Type validation**: All field types match between spec and live data
- [ ] **Required fields**: All required fields identified and validated
- [ ] **Optional fields**: All optional fields identified and validated
- [ ] **Read-only fields**: All read-only fields identified
- [ ] **Nested objects**: All complex nested structures mapped
- [ ] **Operations validated**: All CRUD operations tested and documented
- [ ] **Error cases documented**: Common error scenarios identified

**During Implementation**
- [ ] **Schema matches**: Pydantic models match OpenAPI spec exactly
- [ ] **Required fields**: All required fields implemented
- [ ] **Optional fields**: All optional fields handled correctly
- [ ] **Read-only fields**: Read-only fields marked appropriately
- [ ] **Nested objects**: Complex nested structures implemented correctly
- [ ] **Operations match**: Only existing operations implemented
- [ ] **Endpoints correct**: Using correct endpoint patterns

**Post-Implementation**
- [ ] **Live data compatibility**: Implementation works with real API data
- [ ] **CRUD operations**: All operations work correctly
- [ ] **Error handling**: Proper error handling implemented
- [ ] **Documentation**: Documentation matches actual API behavior

#### Schema Mismatch Resolution Workflow

1. **Identify the Mismatch**
   - Compare implementation with OpenAPI spec
   - Test with live API data
   - Document specific mismatches

2. **Analyze Root Cause**
   - Missing fields from spec
   - Wrong field types
   - Missing required fields
   - Read-only field issues
   - Nested object problems

3. **Fix the Implementation**
   - Update Pydantic models to match spec
   - Add missing required fields
   - Fix field types
   - Handle read-only fields correctly
   - Implement nested objects properly

4. **Validate the Fix**
   - Test with live API data
   - Verify all operations work
   - Check error handling
   - Update documentation

5. **Prevent Future Issues**
   - Update validation checklist
   - Document lessons learned
   - Update protocols if needed

## Troubleshooting

### Issue: Schema Mismatch
**Date Discovered**: 2025-01-19
**Symptoms**: Implementation doesn't work with real API, validation errors
**Root Cause**: Pydantic models don't match OpenAPI specification
**Solution**: Follow schema mismatch resolution workflow above

### Issue: Missing Required Fields
**Date Discovered**: 2025-01-19
**Symptoms**: API returns 400/422 errors on create/update operations
**Root Cause**: Required fields missing from Pydantic model
**Solution**: Add all required fields from OpenAPI spec to model

### Issue: Wrong Field Types
**Date Discovered**: 2025-01-19
**Symptoms**: Validation errors, type mismatches in API responses
**Root Cause**: Field types don't match OpenAPI specification
**Solution**: Update field types to match spec exactly

### Issue: Non-Existent Operations
**Date Discovered**: 2025-01-19
**Symptoms**: 404 errors, operations not found
**Root Cause**: Implementing operations that don't exist in API
**Solution**: Remove non-existent operations, check available endpoints

## Success Criteria

- ✅ **POST operation implemented** (Universal - 97.1% coverage)
- ⚠️ **GET_LIST operation implemented** (Conditional - 82.9% coverage)
- ⚠️ **GET_BY_UUID operation implemented** (Conditional - 81.4% coverage)
- ⚠️ **DELETE operation implemented** (Conditional - 77.1% coverage)
- ❌ **PATCH operations NOT implemented** (Does not exist - 0% coverage, use POST upsert)
- ✅ **POST upsert pattern for updates** (Correct update approach)
- ✅ **Operation availability checking** (Conditional implementation)
- ✅ **Comprehensive tests written**
- ✅ **Documentation complete**
- ✅ **Schema drift detection configured**
- ✅ **Error handling graceful**
- ✅ **Follows project.py patterns**

## Chunking Guidance

**Note**: If this protocol exceeds 3000 tokens, split at phase boundaries:
- Phase 0-1: API Validation and Research
- Phase 2-3: Data Modeling and Documentation Context
- Phase 4-5: CRUD Operations and Testing
- Phase 6: Documentation

## Related Protocols

- [Testing Protocol](testing-protocol.md) - For testing requirements
- [Development Protocol](development-protocol.md) - For overall workflow
- [Code Commit Protocol](code-commit-protocol.md) - For pre-commit requirements

---

*This protocol ensures consistent, high-quality resource implementation across the SDK.*
