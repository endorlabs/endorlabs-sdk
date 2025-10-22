# API Validation Protocol

> **L2 (Task-Specific) - Mandatory API validation before implementation**

## Overview

This protocol ensures that all resource implementations are validated against the actual API specification and live data before any code is written. This prevents schema mismatches and ensures implementations work with the real API.

## Mandatory Validation Steps

### Phase 1: OpenAPI Specification Analysis (MANDATORY)

#### 1.1 Find Service Endpoints
```bash
# Search for the specific service in OpenAPI spec
grep -i "{Resource}Service" .workspace/downloads/openapi-swagger.json
grep -A 30 -B 5 "{Resource}Service" .workspace/downloads/openapi-swagger.json
```

#### 1.2 Extract Complete Schema Definition
```bash
# Find the main resource schema
grep -A 50 '"v1{Resource}":' .workspace/downloads/openapi-swagger.json
grep -A 100 '"v1{Resource}Spec":' .workspace/downloads/openapi-swagger.json
```

#### 1.3 Document Required vs Optional Fields
Create a validation checklist:
- [ ] **Required fields**: List all required fields from OpenAPI spec
- [ ] **Optional fields**: List all optional fields
- [ ] **Read-only fields**: Identify fields marked as `readOnly: true`
- [ ] **Field types**: Document correct types (string, object, array, etc.)
- [ ] **Nested objects**: Identify complex nested structures

### Phase 2: Live API Data Validation (MANDATORY)

#### 2.1 Test with endorctl
```bash
# Get live data structure
endorctl api list -r {Resource}
# Example: endorctl api list -r Project
```

#### 2.2 Create Validation Script
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

#### 2.3 Validate Against OpenAPI Spec
Compare live data with OpenAPI specification:
- [ ] **Field presence**: All OpenAPI fields present in live data?
- [ ] **Field types**: Types match OpenAPI specification?
- [ ] **Required fields**: All required fields present?
- [ ] **Nested structures**: Complex objects match spec?

### Phase 3: CRUD Operations Validation (MANDATORY)

#### 3.1 Test All Available Operations
```bash
# List operation
endorctl api list -r {Resource}

# Get operation (if UUIDs available)
endorctl api get -r {Resource} {uuid}

# Create operation (if supported)
endorctl api create -r {Resource} --help

# Update operation (if supported)
endorctl api update -r {Resource} --help

# Delete operation (if supported)
endorctl api delete -r {Resource} --help
```

#### 3.2 Document Available Operations
Create operation checklist:
- [ ] **List**: `GET /v1/namespaces/{tenant_meta.namespace}/{resource}`
- [ ] **Get**: `GET /v1/namespaces/{tenant_meta.namespace}/{resource}/{uuid}`
- [ ] **Create**: `POST /v1/namespaces/{tenant_meta.namespace}/{resource}`
- [ ] **Update**: `POST /v1/namespaces/{tenant_meta.namespace}/{resource}` (upsert pattern)
- [ ] **Delete**: `DELETE /v1/namespaces/{tenant_meta.namespace}/{resource}/{uuid}`

### Phase 4: Schema Validation (MANDATORY)

#### 4.1 Create Validation Matrix
| Field Name | OpenAPI Type | Live Data Type | Required | Read-Only | Notes |
|------------|--------------|----------------|----------|-----------|-------|
| uuid | string | string | Yes | Yes | Auto-generated |
| meta | object | object | Yes | No | Metadata object |
| spec | object | object | Yes | No | Specification object |
| ... | ... | ... | ... | ... | ... |

#### 4.2 Validate Nested Objects
For each nested object (meta, spec, etc.):
- [ ] **Structure matches**: Nested object structure matches OpenAPI spec
- [ ] **Field types**: All nested fields have correct types
- [ ] **Required fields**: All required nested fields present
- [ ] **Optional fields**: Optional fields handled correctly

### Phase 5: Error Case Validation (MANDATORY)

#### 5.1 Test Error Scenarios
```python
# Test invalid namespace
res = client.get("v1/namespaces/invalid-namespace/{resource}")
print(f"Invalid namespace: {res.status_code}")

# Test invalid UUID
res = client.get(f"v1/namespaces/{namespace}/{resource}/invalid-uuid")
print(f"Invalid UUID: {res.status_code}")

# Test invalid payload (if create/update supported)
# ... test invalid field types, missing required fields, etc.
```

#### 5.2 Document Error Responses
- [ ] **404 errors**: Resource not found
- [ ] **400 errors**: Invalid request
- [ ] **403 errors**: Permission denied
- [ ] **422 errors**: Validation errors

## Validation Checklist

### Pre-Implementation Validation
- [ ] **OpenAPI spec analyzed**: Complete schema extracted
- [ ] **Live data tested**: Real API responses analyzed
- [ ] **Field mapping complete**: All fields mapped between spec and live data
- [ ] **Operations validated**: All CRUD operations tested
- [ ] **Error cases documented**: Common error scenarios identified

### Implementation Validation
- [ ] **Schema matches**: Pydantic models match OpenAPI spec exactly
- [ ] **Required fields**: All required fields implemented
- [ ] **Optional fields**: All optional fields handled correctly
- [ ] **Read-only fields**: Read-only fields marked appropriately
- [ ] **Nested objects**: Complex nested structures implemented correctly

### Post-Implementation Validation
- [ ] **Live data compatibility**: Implementation works with real API data
- [ ] **CRUD operations**: All operations work correctly
- [ ] **Error handling**: Proper error handling implemented
- [ ] **Documentation**: Documentation matches actual API behavior

## Common Validation Failures

### Schema Mismatches
- **Field type mismatches**: String vs object, array vs single value
- **Missing required fields**: Fields marked required in spec but missing in implementation
- **Extra fields**: Fields in implementation but not in spec
- **Nested object mismatches**: Complex objects not matching spec structure

### Operation Mismatches
- **Non-existent operations**: Implementing operations that don't exist in API
- **Missing operations**: Not implementing operations that do exist
- **Wrong endpoints**: Using incorrect endpoint patterns
- **Wrong parameters**: Using wrong parameter types or names

### Data Flow Mismatches
- **Response parsing**: Wrong response structure parsing
- **Request formatting**: Wrong request payload structure
- **Authentication**: Wrong authentication patterns
- **Error handling**: Wrong error response handling

## Validation Tools

### OpenAPI Analysis Tools
```bash
# Extract service endpoints
grep -i "{Resource}Service" .workspace/downloads/openapi-swagger.json

# Extract schema definitions
grep -A 100 '"v1{Resource}":' .workspace/downloads/openapi-swagger.json
grep -A 100 '"v1{Resource}Spec":' .workspace/downloads/openapi-swagger.json

# Extract operation definitions
grep -A 20 "/v1/namespaces/{tenant_meta.namespace}/{resource}" .workspace/downloads/openapi-swagger.json
```

### Live Data Analysis Tools
```python
# Complete API response analysis
def analyze_api_response(resource_name):
    client = APIClient()
    namespace = os.getenv('ENDOR_NAMESPACE', 'endor-solutions-tgowan.cockpit')
    
    # Test list endpoint
    res = client.get(f"v1/namespaces/{namespace}/{resource_name}")
    data = res.json()
    
    # Analyze structure
    objects = data.get("list", {}).get("objects", [])
    if objects:
        sample = objects[0]
        print(f"=== {resource_name} Structure Analysis ===")
        for key, value in sample.items():
            print(f"{key}: {type(value).__name__} = {value}")
    
    return data
```

## Success Criteria

### Validation Passes When:
- [ ] **Schema matches**: Implementation matches OpenAPI spec exactly
- [ ] **Live data works**: Implementation works with real API data
- [ ] **All operations work**: CRUD operations function correctly
- [ ] **Error handling works**: Proper error handling implemented
- [ ] **Documentation accurate**: Documentation matches actual behavior

### Validation Fails When:
- [ ] **Schema mismatches**: Any field type or structure mismatch
- [ ] **Missing operations**: Required operations not implemented
- [ ] **Wrong endpoints**: Using incorrect API endpoints
- [ ] **Data flow issues**: Request/response handling problems

## Integration with Other Protocols

### Resource Implementation Protocol
- **Before Phase 1**: Run API Validation Protocol
- **During Phase 2**: Use validation results for data modeling
- **After Phase 3**: Re-validate against live data

### Development Protocol
- **Step 1**: Include API validation in research phase
- **Step 2**: Use validation results in planning phase
- **Step 3**: Validate implementation against spec

### Testing Protocol
- **Pre-testing**: Validate test data against live API
- **During testing**: Use real API endpoints for validation
- **Post-testing**: Verify tests work with live data

---

**CRITICAL**: This protocol must be completed before any resource implementation begins. Skipping this validation will result in schema mismatches and non-functional implementations.
