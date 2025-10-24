# Resource Implementation Rules of Engagement

> **Tactical Operations**: These rules guide comprehensive resource implementation for the Endor Cockpit SDK.

## Overview

These rules provide detailed steps for implementing new Endor Labs resources in the SDK, ensuring consistency with documented patterns and real-world usage.

## Implementation Phases

### Phase 0: API Analysis (MANDATORY)

**CRITICAL**: This phase must be completed before any implementation begins. Use the OpenAPI specification and live API data as canonical sources.

#### 0.1 Analyze OpenAPI Specification
- [ ] **Review OpenAPI Spec**: Check `external_docs/openapi-swagger.json` for the resource
- [ ] **Example Output**: Use live API responses as the canonical data structure
- [ ] **Description**: Understand the resource's purpose and characteristics
- [ ] **Service Name**: Note the related service name (e.g., `FindingService`)
- [ ] **URL Endpoints**: Review all available endpoints and HTTP methods
- [ ] **API Patterns**: Note any resource-specific patterns or requirements

#### 0.2 Validate Against Base Class Architecture
- [ ] **Universal Attributes**: Ensure all universal fields are present in live data
- [ ] **Conditional Attributes**: Identify which conditional attributes are used
- [ ] **Base Class Compatibility**: Verify the resource can inherit from BaseResource
- [ ] **API Pattern Support**: Confirm advanced patterns (filtering, masking, pagination) are supported

#### 0.3 Create Implementation Matrix
Document the complete mapping between OpenAPI spec and live data:
- [ ] **Universal fields**: All universal attributes present and correct
- [ ] **Conditional fields**: Which conditional attributes are used
- [ ] **Resource-specific fields**: Fields unique to this resource type
- [ ] **API operations**: Which CRUD operations are supported
- [ ] **Advanced patterns**: Which advanced API patterns are supported

## Implementation Patterns

### 1. Basic Resource Structure

#### **Pydantic Models**
```python
class {Resource}Meta(BaseModel):
    """Metadata for {Resource}."""
    name: str
    description: Optional[str] = None
    create_time: Optional[str] = None
    update_time: Optional[str] = None
    upsert_time: Optional[str] = None
    tags: Optional[List[str]] = None

class {Resource}Spec(BaseModel):
    """Specification for {Resource}."""
    # Add fields based on live data analysis
    # Use Optional for API variations
    # Use Union types for flexible fields

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

#### **CRUD Operations**
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

def get_{resource}(client: APIClient, tenant_meta_namespace: str, {resource}_uuid: str) -> Optional[{Resource}]:
    """Get a specific {resource} by UUID."""
    try:
        headers = client.default_headers
        res = client.get(f"v1/namespaces/{tenant_meta_namespace}/{resource}s/{resource}_uuid", headers=headers)
        data = res.json()
        return {Resource}(**data)
    except Exception as e:
        logger.error(f"Error getting {resource} {resource}_uuid}: {e}", exc_info=True)
        return None
```

### 2. Advanced Resource Patterns

#### **Schema Drift Detection**
```python
class {Resource}(BaseModel):
    meta: {Resource}Meta
    spec: {Resource}Spec
    tenant_meta: TenantMeta
    uuid: str
    
    @field_validator('*', mode='before')
    @classmethod
    def detect_schema_drift(cls, v, info):
        """Detect and log schema drift for unknown fields."""
        if info.field_name and isinstance(v, dict):
            model_fields = {
                'meta': {'create_time', 'update_time', 'name', 'description', ...},
                'spec': {'project_uuid', 'level', 'method', 'ecosystem', ...},
                'context': {'id', 'type', 'scan_uuid', 'tags', ...}
            }
            
            if info.field_name in model_fields:
                SchemaDriftDetector.extract_unknown_fields(
                    v, model_fields[info.field_name], f"{Resource}.{info.field_name}"
                )
        return v
```

#### **Flexible Enum Implementation**
```python
class FlexibleEnum(str, Enum):
    """Base class for flexible enums that can handle unknown values."""
    
    @classmethod
    def _missing_(cls, value):
        """Handle unknown enum values gracefully."""
        logger.warning(f"Unknown {cls.__name__} value: {value}. Adding as dynamic enum.")
        obj = str.__new__(cls, value)
        obj._name_ = value
        obj._value_ = value
        return obj

class FindingLevel(FlexibleEnum):
    CRITICAL = "FINDING_LEVEL_CRITICAL"
    HIGH = "FINDING_LEVEL_HIGH"
    # Handles unknown values gracefully
```

#### **Type Flexibility for API Variations**
```python
class FindingSpec(BaseModel):
    finding_categories: Optional[List[str]] = None
    location_urls: Optional[Union[List[str], dict]] = None  # Can be list or empty object
    references: Optional[Union[List[dict], dict]] = None    # Can be list or empty object
```

### 3. PATCH Operations with Update Mask

#### **Update Operations**
```python
def update_{resource}(client: APIClient, tenant_meta_namespace: str, {resource}_uuid: str, payload: Update{Resource}Payload, update_mask: Optional[str] = None) -> Optional[{Resource}]:
    """Update an existing {resource}."""
    try:
        headers = client.default_headers
        headers.update({"Accept": "application/json", "Content-Type": "application/json"})
        
        request_data = {
            "object": {
                "uuid": {resource}_uuid,
                "tenant_meta": {"namespace": tenant_meta_namespace},
                **payload.model_dump(exclude_unset=True)
            }
        }
        if update_mask:
            request_data["request"] = {"update_mask": update_mask}
        
        res = client.patch(f"v1/namespaces/{tenant_meta_namespace}/{resource}s", headers=headers, data=request_data)
        data = res.json()
        return {Resource}(**data)
    except Exception as e:
        logger.error(f"Error updating {resource} {resource}_uuid}: {e}", exc_info=True)
        return None
```

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

---

*These rules ensure consistent, high-quality resource implementation across the Endor Cockpit SDK.*
