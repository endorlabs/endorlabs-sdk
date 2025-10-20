# Design Patterns for LLM-Friendly Development

> **Common patterns and best practices for building LLM-intuitive code**

## 🎯 **Core Patterns**

### **1. Consistent Naming Convention**

#### **Resource Names**
- **Singular Form**: `Project`, `Finding`, `Policy`, `Namespace`
- **Clear Purpose**: Names indicate what the resource represents
- **Hierarchical**: Names reflect the resource hierarchy

#### **Operation Names**
- **Verb-Noun Pattern**: `list_projects`, `get_finding`, `create_policy`
- **Consistent Verbs**: `list_*`, `get_*`, `create_*`, `update_*`, `delete_*`
- **Clear Intent**: Operation names clearly indicate what they do

#### **Field Names**
- **Hierarchical**: `meta.name`, `spec.level`, `tenant_meta.namespace`
- **Descriptive**: Field names describe their purpose
- **Consistent**: Same field names across all resources

### **2. Type Safety Patterns**

#### **Pydantic Models**
```python
class Project(BaseModel):
    """Project resource model with type safety."""
    uuid: str = Field(..., description="Unique identifier")
    meta: ProjectMeta = Field(..., description="Project metadata")
    spec: ProjectSpec = Field(..., description="Project specification")
    tenant_meta: TenantMeta = Field(..., description="Tenant metadata")
```

#### **Type Hints**
```python
def list_projects(
    client: APIClient, 
    namespace: str
) -> List[Project]:
    """List all projects in the specified namespace."""
```

### **3. Error Handling Patterns**

#### **Graceful Degradation**
```python
try:
    result = api_call()
    return result
except APIError as e:
    logger.error(f"API error: {e}")
    return None
except ValidationError as e:
    logger.error(f"Validation error: {e}")
    return None
```

#### **Schema Drift Detection**
```python
@field_validator('*', mode='before')
@classmethod
def detect_schema_drift(cls, v, info):
    """Detect and log schema drift for unknown fields."""
    if info.field_name and isinstance(v, dict):
        SchemaDriftDetector.extract_unknown_fields(
            v, model_fields, f"{cls.__name__}.{info.field_name}"
        )
    return v
```

### **4. Documentation Patterns**

#### **Comprehensive Docstrings**
```python
def create_project(
    client: APIClient,
    namespace: str,
    payload: CreateProjectPayload
) -> Optional[Project]:
    """
    Create a new project in the specified namespace.
    
    Args:
        client: APIClient instance for API communication
        namespace: Canonical namespace name (e.g., 'tenant.namespace')
        payload: Project creation payload with required fields
        
    Returns:
        Created Project instance if successful, None otherwise
        
    Raises:
        ValidationError: If payload validation fails
        APIError: If API request fails
        
    Example:
        >>> client = APIClient()
        >>> payload = CreateProjectPayload(...)
        >>> project = create_project(client, "tenant.namespace", payload)
    """
```

#### **Type Documentation**
```python
# Clear type definitions
ResourceType = Literal["Project", "Finding", "Policy", "Namespace"]
OperationType = Literal["list", "get", "create", "update", "delete"]
```

### **5. Validation Patterns**

#### **Multi-Layer Validation**
```python
# 1. Pydantic model validation
class Project(BaseModel):
    uuid: str = Field(..., min_length=24, max_length=24)
    
# 2. Business logic validation
def validate_project_creation(payload: CreateProjectPayload) -> bool:
    """Validate project creation payload."""
    return ValidationUtils.validate_resource_creation(payload, required_fields)
    
# 3. API format validation
def validate_namespace_format(namespace: str) -> bool:
    """Validate namespace follows canonical format."""
    return ValidationUtils.validate_namespace_format(namespace)
```

### **6. Testing Patterns**

#### **Comprehensive Fixtures**
```python
@pytest.fixture
def sample_project_data():
    """Sample project data for testing."""
    return {
        "uuid": "project-uuid-123",
        "meta": {"name": "test-project", "description": "Test project"},
        "spec": {"platform_source": "PLATFORM_SOURCE_GITHUB"},
        "tenant_meta": {"namespace": "test.namespace"}
    }
```

#### **Mock Patterns**
```python
@pytest.fixture
def mock_client():
    """Create a mock APIClient for testing."""
    client = Mock(spec=APIClient)
    client.default_headers = {"Authorization": "Bearer test-token"}
    return client
```

### **7. Logging Patterns**

#### **Structured Logging**
```python
logger.info(f"Creating project in namespace: {namespace}")
logger.warning(f"Schema drift detected: {unknown_fields}")
logger.error(f"API request failed: {error}", exc_info=True)
```

#### **Context-Aware Logging**
```python
logger.info(f"Operation: {operation}, Resource: {resource_type}, Namespace: {namespace}")
```

### **8. Configuration Patterns**

#### **Environment-Based Configuration**
```python
class Config:
    """Configuration management for the SDK."""
    API_BASE_URL: str = os.getenv("ENDOR_API", "https://api.endor.ai")
    API_KEY: str = os.getenv("ENDOR_API_CREDENTIALS_KEY", "")
    API_SECRET: str = os.getenv("ENDOR_API_CREDENTIALS_SECRET", "")
```

### **9. Performance Patterns**

#### **Lazy Loading**
```python
@property
def findings(self) -> List[Finding]:
    """Lazy load findings for this project."""
    if not hasattr(self, '_findings'):
        self._findings = list_findings(self.client, self.namespace)
    return self._findings
```

#### **Caching**
```python
@lru_cache(maxsize=128)
def get_project(client: APIClient, namespace: str, project_uuid: str) -> Optional[Project]:
    """Get project with caching."""
```

### **10. Security Patterns**

#### **Input Sanitization**
```python
def sanitize_tags(tags: List[str]) -> List[str]:
    """Sanitize tags by removing empty strings and duplicates."""
    return [tag.strip() for tag in tags if tag and tag.strip()]
```

#### **Credential Protection**
```python
class RedactingFilter(logging.Filter):
    """Filter to redact sensitive information from logs."""
    def filter(self, record):
        # Redact API keys, tokens, etc.
        return True
```

---

*These patterns ensure that the codebase is intuitive for both human developers and AI agents, with clear structure and comprehensive documentation.*
