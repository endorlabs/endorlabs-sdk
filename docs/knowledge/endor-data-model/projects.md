# Project Resource Deep-Dive

> **Comprehensive guide to project resources in Endor Labs platform**

## 🏗️ **Project Architecture**

### **Project Structure**
Projects in Endor Labs represent code repositories and applications:

```
Namespace (tenant.namespace)
├── Project (repository-1)
│   ├── Findings (vulnerabilities)
│   ├── Scans (analysis runs)
│   └── Policies (security rules)
└── Project (repository-2)
    ├── Findings (vulnerabilities)
    └── Scans (analysis runs)
```

### **Project Lifecycle**
```
Repository → Project → Scans → Findings → Remediation
```

---

## 📊 **Project Data Model**

### **Core Properties**
```python
class Project(BaseModel):
    uuid: str                    # Unique identifier
    name: str                   # Project name
    description: str            # Project description
    namespace_uuid: str         # Parent namespace UUID
    repository_url: str         # Repository URL
    created_at: datetime        # Creation timestamp
    updated_at: datetime        # Last update timestamp
```

### **Project Metadata**
```python
class ProjectMeta(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str = Field("")
    repository_url: str = Field("")
    language: str = Field("")
    framework: str = Field("")
```

### **Creation Payload**
```python
class CreateProjectPayload(BaseModel):
    meta: ProjectMeta
    namespace_uuid: str
```

---

## 🔧 **Project Operations**

### **List Projects**
```python
def list_projects(client: APIClient, namespace_uuid: str) -> List[Project]:
    """List all projects in a namespace."""
    # Implementation details
```

### **Get Project**
```python
def get_project(client: APIClient, project_uuid: str) -> Optional[Project]:
    """Get a specific project by UUID."""
    # Implementation details
```

### **Create Project**
```python
def create_project(
    client: APIClient, 
    namespace_uuid: str, 
    payload: CreateProjectPayload
) -> Optional[Project]:
    """Create a new project in a namespace."""
    # Implementation details
```

### **Update Project**
```python
def update_project(
    client: APIClient, 
    project_uuid: str, 
    payload: UpdateProjectPayload
) -> Optional[Project]:
    """Update an existing project."""
    # Implementation details
```

### **Delete Project**
```python
def delete_project(client: APIClient, project_uuid: str) -> bool:
    """Delete a project."""
    # Implementation details
```

---

## 🔍 **Project Relationships**

### **Namespace Relationship**
- **Parent**: Namespace contains projects
- **Access**: Projects inherit namespace permissions
- **Isolation**: Projects are isolated within namespaces

### **Finding Relationship**
- **Source**: Projects generate findings through scans
- **Types**: SCA, SAST, Secrets, Compliance findings
- **Lifecycle**: Findings track remediation progress

### **Scan Relationship**
- **Trigger**: Scans analyze projects for vulnerabilities
- **Types**: Full, incremental, targeted scans
- **Results**: Scans produce findings

### **Policy Relationship**
- **Application**: Policies apply to projects
- **Enforcement**: Policies enforce security rules
- **Compliance**: Policies ensure compliance

---

## 🚨 **Common Issues**

### **Repository Access**
**Cause**: Invalid repository URL or access permissions
**Solution**: Verify repository URL and permissions

```python
# ❌ WRONG - Invalid repository URL
project = create_project(client, namespace_uuid, {
    "meta": {"name": "test", "repository_url": "invalid-url"}
})

# ✅ CORRECT - Valid repository URL
project = create_project(client, namespace_uuid, {
    "meta": {"name": "test", "repository_url": "https://github.com/owner/repo"}
})
```

### **Namespace Permissions**
**Cause**: Insufficient permissions to create projects
**Solution**: Verify namespace access permissions

```python
# Check namespace permissions before creating project
permissions = check_namespace_permissions(client, namespace_uuid)
if not permissions.can_create_projects:
    raise PermissionError("Cannot create projects in this namespace")
```

---

## 🧪 **Testing Patterns**

### **Project Creation Testing**
```python
def test_project_creation(api_client, namespace_uuid):
    """Test project creation."""
    payload = CreateProjectPayload(
        meta=ProjectMeta(
            name="test-project",
            description="Test project",
            repository_url="https://github.com/owner/repo"
        ),
        namespace_uuid=namespace_uuid
    )
    
    project = create_project(api_client, namespace_uuid, payload)
    assert project is not None
    assert project.name == "test-project"
```

### **Project Relationships Testing**
```python
def test_project_relationships(api_client, project_uuid):
    """Test project relationships."""
    # Test namespace relationship
    project = get_project(api_client, project_uuid)
    assert project.namespace_uuid is not None
    
    # Test findings relationship
    findings = list_findings(api_client, project_uuid)
    assert isinstance(findings, list)
    
    # Test scans relationship
    scans = list_scans(api_client, project_uuid)
    assert isinstance(scans, list)
```

---

## 📚 **Related Resources**

- **[Findings](./findings.md)** - Finding resource deep-dive
- **[Scans](./scans.md)** - Scan resource deep-dive
- **[Policies](./policies.md)** - Policy resource deep-dive
- **[Relationships](./relationships.md)** - Resource relationships

---

*This resource guide provides comprehensive information about project resources in the Endor Labs platform.*
