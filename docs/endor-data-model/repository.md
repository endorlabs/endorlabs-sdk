# Repository Resource Deep-Dive

> **Comprehensive guide to Repository resources in Endor Labs platform**

<!-- RAG METADATA
resource_type: repository
sdk_module: src/endor_cockpit/resources/repository.py
last_reviewed: 2025-10-19
-->

## Architecture

<!-- ~500 tokens | Query: "What is repository architecture?" -->

### Resource Structure

Repositories in Endor Labs represent source code information for projects:

```
Namespace (tenant.namespace)
├── Project (repository-1)
│   └── Repository (source-code-info)
│       ├── RepositoryVersion (main)
│       ├── RepositoryVersion (develop)
│       └── RepositoryVersion (v1.0.0)
└── Project (repository-2)
    └── Repository (source-code-info)
        └── RepositoryVersion (main)
```

### Core Concepts

- **1:1 with Projects**: One Repository = One Project (at most)
- **Source code container**: Contains information about source code for a project
- **Version parent**: Parent of RepositoryVersion resources
- **No context association**: Like Project, does not belong to a context
- **Same naming as Project**: Repository name is the same as the Project name

### Lifecycle

```
Project → Repository → RepositoryVersion → Scans → Findings
```

**Lifecycle States**:
- **Created**: Repository created when project has source code
- **Versioned**: RepositoryVersion resources created for branches/tags
- **Scanned**: Security scans analyze repository versions
- **Findings Generated**: Vulnerabilities and issues discovered

---

## Data Model

<!-- ~800 tokens | Query: "What are repository data structures?" -->

### SDK Implementation

**Location**: `src/endor_cockpit/resources/repository.py:50-200`

```python
# Direct reference - see SDK for full definition
class Repository(BaseModel):
    uuid: str = Field(..., description="Unique identifier for the repository")
    meta: RepositoryMeta = Field(..., description="Repository metadata")
    spec: RepositorySpec = Field(..., description="Repository specification")
    tenant_meta: TenantMeta = Field(..., description="Tenant metadata")
```

### Core Properties

**RepositoryMeta** (`src/endor_cockpit/resources/repository.py:52-80`):
- `name`: Repository name (same as Project name)
- `description`: Repository description
- `tags`: General resource tags
- `create_time`, `created_by`: Creation metadata
- `update_time`, `updated_by`: Auto-managed timestamps

**RepositorySpec** (`src/endor_cockpit/resources/repository.py:82-100`):
- `project_uuid`: Associated project UUID
- `source_code_info`: Source code information and metadata

### Mutable vs Immutable Fields

**MUTABLE FIELDS** (can be updated via PATCH):
- `meta.description`: Repository description
- `meta.tags`: General resource tags

**IMMUTABLE FIELDS** (read-only, managed by API):
- `uuid`: Unique identifier (set at creation)
- `meta.name`: Repository name (same as Project, set at creation)
- `spec.project_uuid`: Associated project (set at creation)
- `meta.create_time`, `meta.created_by`: Creation metadata
- `meta.update_time`, `meta.updated_by`: Auto-managed timestamps
- `tenant_meta.namespace`: Namespace assignment

---

## Operations

<!-- ~600 tokens | Query: "How to work with repositories?" -->

### CRUD Operations

**Location**: `src/endor_cockpit/resources/repository.py:200-400`

#### List Repositories
```python
from endor_cockpit.resources import repository

# List all repositories in namespace
repositories = repository.list_repositories(client, namespace)
```

#### Get Repository
```python
# Get specific repository
repository_obj = repository.get_repository(client, namespace, repository_uuid)
```

#### Create Repository
```python
from endor_cockpit.resources.repository import CreateRepositoryPayload, RepositoryMeta, RepositorySpec

# Create new repository
payload = CreateRepositoryPayload(
    meta=RepositoryMeta(
        name="https://github.com/org/repo.git",
        description="Main application repository"
    ),
    spec=RepositorySpec(
        project_uuid="project-uuid-123"
    )
)
new_repository = repository.create_repository(client, namespace, payload)
```

#### Update Repository
```python
from endor_cockpit.resources.repository import UpdateRepositoryPayload, RepositoryMeta

# Update repository description
payload = UpdateRepositoryPayload(
    meta=RepositoryMeta(description="Updated repository description")
)
updated_repository = repository.update_repository(
    client, namespace, repository_uuid, payload, "meta.description"
)
```

#### Delete Repository
```python
# Delete repository
success = repository.delete_repository(client, namespace, repository_uuid)
```

### Tag Management

**Location**: `src/endor_cockpit/resources/tag_management.py`

```python
from endor_cockpit.resources import tag_management

# Add repository tag
tag_management.add_repository_tag(client, namespace, repository_uuid, "production")

# Remove repository tag
tag_management.remove_repository_tag(client, namespace, repository_uuid, "staging")

# List repository tags
tags = tag_management.list_repository_tags(client, namespace, repository_uuid)
```

---

## Relationships

<!-- ~400 tokens | Query: "How do repositories relate to other resources?" -->

### Parent Resources
- **Project**: Repository belongs to exactly one Project
- **Namespace**: Repository belongs to a specific namespace

### Child Resources
- **RepositoryVersion**: Repository can have multiple versions (branches, tags)

### Related Resources
- **Findings**: Generated from scans of repository versions
- **Scans**: Analyze repository versions for security issues
- **Metrics**: Analytics data for repository versions

### Relationship Patterns
```python
# Get repository with related data
repository = repository.get_repository(client, namespace, repository_uuid)

# Get project that owns this repository
project = project.get_project(client, namespace, repository.spec.project_uuid)

# Get repository versions
versions = repository_version.list_repository_versions(client, namespace, repository_uuid)
```

---

## Common Issues

<!-- ~300 tokens | Query: "What are common repository issues?" -->

### Repository Not Found
**Issue**: Repository doesn't exist for a project
**Solution**: Check if project has source code, repository is created automatically

### Update Failures
**Issue**: Repository updates fail with validation errors
**Solution**: Ensure required fields are included, use update_mask for partial updates

### Schema Drift
**Issue**: Unknown fields in API responses
**Solution**: Schema drift detection logs warnings, models handle gracefully

### Tag Management
**Issue**: Tags not persisting after updates
**Solution**: Use update_mask parameter, ensure tags field is included in model

---

## Troubleshooting

<!-- ~200 tokens | Query: "How to troubleshoot repository issues?" -->

### Debug Repository Operations
```python
import logging
logging.basicConfig(level=logging.DEBUG)

# List repositories with debug logging
repositories = repository.list_repositories(client, namespace)
```

### Validate Repository Data
```python
# Check repository structure
repository_obj = repository.get_repository(client, namespace, repository_uuid)
print(f"Repository: {repository_obj.meta.name}")
print(f"Project UUID: {repository_obj.spec.project_uuid}")
print(f"Tags: {repository_obj.meta.tags}")
```

### Common Error Messages
- **404 Not Found**: Repository doesn't exist
- **400 Bad Request**: Invalid payload or missing required fields
- **403 Forbidden**: Insufficient permissions
- **Schema Drift Warnings**: Unknown fields detected (non-blocking)

---

*This resource provides comprehensive repository management capabilities for Endor Labs platform integration.*
