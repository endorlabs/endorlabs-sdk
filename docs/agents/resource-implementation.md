# Resource Implementation Patterns

> **Comprehensive patterns for implementing Endor Labs resources in the Cockpit SDK**

## 🎯 **Resource Implementation Overview**

This guide provides comprehensive patterns for implementing any Endor Labs resource in the Cockpit SDK, based on successful implementation of Project and Finding resources.

## 📋 **Common Resource Types**

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

## 🔧 **Implementation Patterns**

### **1. Basic Resource Structure**

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

### **2. Advanced Resource Patterns**

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

### **3. PATCH Operations with Update Mask**

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

#### **Tag Management**
```python
def add_{resource}_tag(client: APIClient, tenant_meta_namespace: str, {resource}_uuid: str, tag: str) -> Optional[{Resource}]:
    """Add a tag to a {resource}."""
    # Get current {resource}
    {resource} = get_{resource}(client, tenant_meta_namespace, {resource}_uuid)
    if not {resource}:
        return None
    
    # Add tag to existing tags
    current_tags = {resource}.meta.tags or []
    if tag not in current_tags:
        current_tags.append(tag)
    
    # Update with new tags
    payload = Update{Resource}Payload(meta={Resource}MetaUpdate(tags=current_tags))
    return update_{resource}(client, tenant_meta_namespace, {resource}_uuid, payload, "meta.tags")
```

## 🚨 **Common Implementation Pitfalls**

### **1. API Endpoint Issues**
- **Wrong URL Pattern**: Check OpenAPI spec for actual endpoints
- **Authentication Failures**: Use resource modules instead of direct API calls
- **Response Parsing**: Use consistent pattern across all resource modules

### **2. Pydantic Model Issues**
- **Missing Fields**: Compare with live API data
- **Type Mismatches**: Use `Union` types for flexible fields
- **Validation Errors**: Make fields optional for API variations

### **3. Test Structure Issues**
- **Redundant Files**: Consolidate by resource type
- **Naming Inconsistency**: Follow existing patterns
- **Class References**: Maintain consistency between names and references

## 🔧 **Implementation Best Practices**

### **1. Live Data Analysis First**
```python
# Analyze live data before creating models
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

### **2. Schema Drift Detection from Start**
```python
# Implement schema drift detection from the start
class {Resource}(BaseModel):
    meta: {Resource}Meta
    spec: {Resource}Spec
    
    @field_validator('*', mode='before')
    @classmethod
    def detect_schema_drift(cls, v, info):
        """Detect and log schema drift for unknown fields."""
        # Implementation here
        return v
```

### **3. Universal API Pattern**
```python
# Use universal pattern for all resources
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

## 📊 **Resource Complexity Classification**

### **Simple Resources** (Basic CRUD, minimal nested structures)
- `Namespace`: Basic metadata, minimal nesting
- `User`: Simple user information
- `Token`: Authentication tokens

### **Medium Resources** (Some complexity, moderate nesting)
- `Project`: Git repository information, processing status
- `Scan`: Scan results and metadata
- `Policy`: Security policies and rules

### **Complex Resources** (High complexity, extensive nesting)
- `Finding`: 30+ fields, multiple categories, complex enums
- `Secret`: Secret detection with complex metadata
- `Vulnerability`: Vulnerability details with remediation

## 🎯 **Success Metrics**

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

## 📚 **Resource-Specific Examples**

### **Project Resource Implementation**
```python
class ProjectMeta(BaseModel):
    name: str
    description: Optional[str] = None
    create_time: Optional[str] = None
    update_time: Optional[str] = None
    upsert_time: Optional[str] = None
    tags: Optional[List[str]] = None

class ProjectSpec(BaseModel):
    git: Optional[GitInfo] = None
    language: Optional[str] = None
    framework: Optional[str] = None
    # ... other fields based on live data

class Project(BaseModel):
    meta: ProjectMeta
    processing_status: ProcessingStatus
    spec: ProjectSpec
    tenant_meta: TenantMeta
    uuid: str
```

### **Finding Resource Implementation**
```python
class FindingMeta(BaseModel):
    name: str
    description: Optional[str] = None
    create_time: Optional[str] = None
    update_time: Optional[str] = None
    tags: Optional[List[str]] = None

class FindingSpec(BaseModel):
    project_uuid: str
    level: FindingLevel
    method: Optional[AnalysisMethod] = None
    ecosystem: Optional[Ecosystem] = None
    # ... 30+ fields based on live data

class Finding(BaseModel):
    meta: FindingMeta
    spec: FindingSpec
    context: Context
    tenant_meta: TenantMeta
    uuid: str
```

---

*This resource implementation guide ensures consistent, high-quality implementation of all Endor Labs resources in the Cockpit SDK.*
