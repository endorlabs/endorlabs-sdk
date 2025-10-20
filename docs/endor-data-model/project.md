# Project Resource Deep-Dive

> **Comprehensive guide to Project resources in Endor Labs platform**

<!-- RAG METADATA
resource_type: project
sdk_module: src/endor_cockpit/resources/project.py
last_reviewed: 2025-10-19
-->

## Architecture

<!-- ~500 tokens | Query: "What is project architecture?" -->

### Resource Structure

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

### Core Concepts

- **1:1 with Git repositories**: One Project = One Git Repository
- **Namespace-scoped**: Projects belong to a specific namespace
- **Scan-driven finding generation**: Projects generate findings through security scans
- **Repository naming**: Project name is the HTTP clone URL (e.g., `https://github.com/org/repo.git`)

### Lifecycle

```
Repository → Project → Scans → Findings → Remediation
```

**Lifecycle States**:
- **Created**: Project created in namespace
- **Scanned**: Security scans analyze repository
- **Findings Generated**: Vulnerabilities and issues discovered
- **Remediated**: Issues fixed and verified

---

## Data Model

<!-- ~700 tokens | Query: "What fields does project have?" -->

### SDK Implementation

**Location**: `src/endor_cockpit/resources/project.py:215-231`

```python
# Direct reference - see SDK for full definition
class Project(BaseModel):
    meta: ProjectMeta
    processing_status: ProcessingStatus
    spec: ProjectSpec
    tenant_meta: TenantMeta
    uuid: str
```

**To explore fields**:
- View `ProjectMeta` in SDK (lines 74-91)
- View `ProjectSpec` in SDK (lines 193-199)
- View `ProcessingStatus` in SDK (lines 201-207)

### Mutable Fields

**Via PATCH operations**:
- `meta.description`: str - Project description
- `meta.tags`: List[str] - List of tags for categorization
- `meta.repository_url`: str - Repository URL
- `meta.language`: str - Primary programming language
- `meta.framework`: str - Framework used

### Immutable Fields

**Read-only, API-managed**:
- `uuid`: Unique identifier (set at creation)
- `meta.name`: Project name (set at creation)
- `meta.create_time`, `meta.created_by`: Creation metadata
- `spec.git.*`: Git information (synced from repository)
- `processing_status.*`: Scan state (managed by scan service)
- `tenant_meta.namespace`: Namespace assignment

### Field Validation

**Validators** (see `ProjectMetaUpdate:130-144`):
- `tags`: No empty strings, whitespace stripped
- `description`: No whitespace-only values

---

## Operations

<!-- ~800 tokens | Query: "How do I [operation] project?" -->

### List Projects

**Function**: `project.list_projects(client, tenant_meta_namespace)`  
**Location**: `src/endor_cockpit/resources/project.py:337`  
**Status**: ✅ IMPLEMENTED

```python
from endor_cockpit.resources import project

# List all projects in namespace
all_projects = project.list_projects(
    client=client,
    tenant_meta_namespace="tenant.namespace"
)
```

**Returns**: `List[Project]` - Empty list on error

### Get Project

**Function**: `project.get_project(client, tenant_meta_namespace, project_uuid)`  
**Location**: `src/endor_cockpit/resources/project.py:367`  
**Status**: ✅ IMPLEMENTED

```python
# Get specific project
project_obj = project.get_project(
    client=client,
    tenant_meta_namespace="tenant.namespace",
    project_uuid="project-uuid-here"
)
```

**Returns**: `Optional[Project]` - None on error

### Create Project

**Function**: `project.create_project(client, tenant_meta_namespace, payload)`  
**Location**: `src/endor_cockpit/resources/project.py:399`  
**Status**: ✅ IMPLEMENTED

```python
from endor_cockpit.resources.project import (
    CreateProjectPayload,
    ProjectMetaCreate
)

# Create new project
payload = CreateProjectPayload(
    meta=ProjectMetaCreate(
        name="project-name",
        description="Project description",
        repository_url="https://github.com/org/repo"
    )
)

project_obj = project.create_project(
    client=client,
    tenant_meta_namespace="tenant.namespace",
    payload=payload
)
```

**Required Fields**: `meta.name` (project name)  
**Auto-populated**: `spec.git.*` from repository_url

### Update Project

**Function**: `project.update_project(client, tenant_meta_namespace, project_uuid, payload, update_mask)`  
**Location**: `src/endor_cockpit/resources/project.py:433`  
**Status**: ✅ IMPLEMENTED

```python
from endor_cockpit.resources.project import (
    UpdateProjectPayload,
    ProjectMetaUpdate
)

# Update project tags and description
payload = UpdateProjectPayload(
    meta=ProjectMetaUpdate(
        description="Updated description",
        tags=["production", "backend"]
    )
)

project_obj = project.update_project(
    client=client,
    tenant_meta_namespace="tenant.namespace",
    project_uuid="project-uuid",
    payload=payload,
    update_mask="meta.description,meta.tags"
)
```

**update_mask**: REQUIRED for tag persistence  
**Mutable Fields**: See Data Model > Mutable Fields

### Delete Project

**Function**: `project.delete_project(client, tenant_meta_namespace, project_uuid)`  
**Location**: `src/endor_cockpit/resources/project.py:546`  
**Status**: ✅ IMPLEMENTED

```python
# Delete project
success = project.delete_project(
    client=client,
    tenant_meta_namespace="tenant.namespace",
    project_uuid="project-uuid"
)
```

**Behavior**: Immediate deletion  
**Cascade**: Findings and scans are also deleted

---

## Relationships

<!-- ~500 tokens | Query: "How does project relate to X?" -->

### Project-Namespace

- **Parent-Child**: Projects belong to a specific namespace
- **Permission Inheritance**: Projects inherit namespace permissions
- **Isolation**: Projects are isolated within namespaces
- **Cannot Move**: Projects cannot be moved between namespaces

### Project-Finding

- **Source**: Projects generate findings through security scans
- **Types**: SCA, SAST, Secrets, Compliance findings
- **Lifecycle**: Findings track remediation progress
- **Cascade**: Deleting project deletes all associated findings

### Project-Policy

- **Application**: Policies apply to projects via `project_selector`
- **Enforcement**: Policies enforce security rules on projects
- **Compliance**: Policies ensure compliance requirements
- **Scope**: Project-specific policies vs namespace policies

---

## Common Issues

<!-- ~600 tokens | Query: "What are common project issues?" -->

### Issue: Tags Not Persisting After Update

**Cause**: Missing `update_mask` parameter in PATCH requests  
**Solution**: Always include `update_mask` for field updates

```python
# ❌ WRONG - Tags won't persist
project.update_project(client, namespace, uuid, payload)

# ✅ CORRECT - Tags persist with update_mask
project.update_project(
    client, namespace, uuid, payload, 
    update_mask="meta.tags"
)
```

### Issue: 403 Forbidden When Creating Projects

**Cause**: Using UUID instead of canonical namespace name  
**Solution**: Use canonical namespace format

```python
# ❌ WRONG - Will fail with 403 Forbidden
project.create_project(client, namespace_uuid, payload)

# ✅ CORRECT - Use canonical namespace name
project.create_project(client, "tenant.namespace", payload)
```

### Issue: Repository URL Not Auto-Populating Git Info

**Cause**: Invalid repository URL format  
**Solution**: Use proper Git clone URLs

```python
# ❌ WRONG - Invalid URL format
repository_url = "github.com/org/repo"

# ✅ CORRECT - Full Git clone URL
repository_url = "https://github.com/org/repo.git"
```

---

## Testing Patterns

<!-- ~400 tokens -->

### CRUD Testing

**Test File**: `tests/test_project.py`

```python
# Reference actual test patterns from test_project.py
# See lines 45-65 for list/get testing
# See lines 67-95 for create/update testing
# See lines 97-125 for tag management testing
```

### Integration Testing

**Test File**: `tests/test_project.py`

```python
# Reference integration test patterns
# See lines 127-155 for relationship testing
# See lines 157-185 for error handling testing
```

---

## Troubleshooting

### Issue: Project Not Found (404 Error)

**Date Discovered**: 2025-10-19

**Symptoms**: 
- `get_project()` returns 404 Not Found
- Project appears in `list_projects()` but cannot be retrieved individually

**Root Cause**: 
- Using UUID instead of canonical name for project identification
- Incorrect namespace parameter in API calls

**Solution**: 
```python
# ❌ INCORRECT - Using UUID
project = get_project(client, project_uuid)

# ✅ CORRECT - Using canonical name
project = get_project(client, "tenant.namespace.project-name")
```

**Prevention**: Always use canonical names for project operations, not UUIDs.

---

### Issue: Tag Updates Not Persisting

**Date Discovered**: 2025-10-19

**Symptoms**: 
- PATCH request returns 200 OK with updated tags
- Subsequent GET request shows original tags (not updated)
- Tags appear to be updated but don't persist

**Root Cause**: 
- Missing `update_mask` parameter in PATCH requests
- API requires explicit field specification for updates

**Solution**: 
```python
# ❌ INCORRECT - Missing update_mask
payload = UpdateProjectPayload(tags=["new-tag"])

# ✅ CORRECT - Include update_mask
payload = UpdateProjectPayload(
    tags=["new-tag"],
    update_mask=["tags"]
)
```

**Prevention**: Always include `update_mask` parameter when updating specific fields.

---

### Issue: Permission Denied (403 Error)

**Date Discovered**: 2025-10-19

**Symptoms**: 
- 403 Forbidden when creating or updating projects
- Cross-tenant operations fail

**Root Cause**: 
- Attempting cross-tenant operations
- Using incorrect namespace format

**Solution**: 
```python
# ❌ INCORRECT - Cross-tenant operation
namespace = "other-tenant.namespace"

# ✅ CORRECT - Same tenant namespace
namespace = "your-tenant.namespace"
```

**Prevention**: Ensure all operations use the same tenant namespace.

---

## Related Resources

- [Finding](./finding.md) - Findings generated by project scans
- [Policy](./policy.md) - Policies applied to projects
- [Namespace](./namespace.md) - Parent namespace container

---

<!-- VALIDATION METADATA
last_reviewed: 2025-10-19
reviewed_by: human
validation_status: needs_review
known_issues: []
-->

*Documentation references SDK implementation. See `src/endor_cockpit/resources/project.py` for complete details.*

