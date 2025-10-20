# Repository Version Resource Deep-Dive

> **Comprehensive guide to Repository Version resources in Endor Labs platform**

<!-- RAG METADATA
resource_type: repository_version
sdk_module: src/endor_cockpit/resources/repository_version.py
last_reviewed: 2025-10-19
-->

## Architecture

<!-- ~500 tokens | Query: "What is repository version architecture?" -->

### Resource Structure

Repository versions in Endor Labs represent specific versions (branches/tags) of repositories:

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

- **1:N with Repository**: One Repository can have multiple RepositoryVersions
- **Version tracking**: Represents specific commits, branches, or tags
- **Scan target**: RepositoryVersions are scanned for security issues
- **Git integration**: Tracks commit SHA, branch, and tag information
- **Hierarchical naming**: RepositoryVersion name includes repository context

### Lifecycle

```
Repository → RepositoryVersion → Scans → Findings
```

**Lifecycle States**:
- **Created**: RepositoryVersion created for branch/tag
- **Scanned**: Security scans analyze specific version
- **Findings Generated**: Vulnerabilities discovered in version
- **Updated**: New commits create new versions

---

## Data Model

<!-- ~800 tokens | Query: "What are repository version data structures?" -->

### SDK Implementation

**Location**: `src/endor_cockpit/resources/repository_version.py:50-200`

```python
# Direct reference - see SDK for full definition
class RepositoryVersion(BaseModel):
    uuid: str = Field(..., description="Unique identifier for the repository version")
    meta: RepositoryVersionMeta = Field(..., description="Repository version metadata")
    spec: RepositoryVersionSpec = Field(..., description="Repository version specification")
    tenant_meta: TenantMeta = Field(..., description="Tenant metadata")
```

### Core Properties

**RepositoryVersionMeta** (`src/endor_cockpit/resources/repository_version.py:52-80`):
- `name`: Repository version name (branch/tag name)
- `description`: Repository version description
- `tags`: General resource tags
- `create_time`, `created_by`: Creation metadata
- `update_time`, `updated_by`: Auto-managed timestamps

**RepositoryVersionSpec** (`src/endor_cockpit/resources/repository_version.py:82-100`):
- `repository_uuid`: Parent repository UUID
- `commit_sha`: Git commit SHA
- `branch`: Git branch name
- `tag`: Git tag name
- `source_code_info`: Source code information and metadata

### Mutable vs Immutable Fields

**MUTABLE FIELDS** (can be updated via PATCH):
- `meta.description`: Repository version description
- `meta.tags`: General resource tags

**IMMUTABLE FIELDS** (read-only, managed by API):
- `uuid`: Unique identifier (set at creation)
- `meta.name`: Repository version name (set at creation)
- `spec.repository_uuid`: Parent repository (set at creation)
- `spec.commit_sha`, `spec.branch`, `spec.tag`: Git information (set at creation)
- `meta.create_time`, `meta.created_by`: Creation metadata
- `meta.update_time`, `meta.updated_by`: Auto-managed timestamps
- `tenant_meta.namespace`: Namespace assignment

---

## Operations

<!-- ~600 tokens | Query: "How to work with repository versions?" -->

### CRUD Operations

**Location**: `src/endor_cockpit/resources/repository_version.py:200-400`

#### List Repository Versions
```python
from endor_cockpit.resources import repository_version

# List all versions for a repository
versions = repository_version.list_repository_versions(client, namespace, repository_uuid)
```

#### Get Repository Version
```python
# Get specific repository version
version = repository_version.get_repository_version(client, namespace, repository_uuid, version_uuid)
```

#### Create Repository Version
```python
from endor_cockpit.resources.repository_version import CreateRepositoryVersionPayload, RepositoryVersionMeta, RepositoryVersionSpec

# Create new repository version
payload = CreateRepositoryVersionPayload(
    meta=RepositoryVersionMeta(
        name="main",
        description="Main development branch"
    ),
    spec=RepositoryVersionSpec(
        repository_uuid="repository-uuid-123",
        commit_sha="abc123def456",
        branch="main"
    )
)
new_version = repository_version.create_repository_version(client, namespace, repository_uuid, payload)
```

#### Update Repository Version
```python
from endor_cockpit.resources.repository_version import UpdateRepositoryVersionPayload, RepositoryVersionMeta

# Update repository version description
payload = UpdateRepositoryVersionPayload(
    meta=RepositoryVersionMeta(description="Updated version description")
)
updated_version = repository_version.update_repository_version(
    client, namespace, repository_uuid, version_uuid, payload, "meta.description"
)
```

#### Delete Repository Version
```python
# Delete repository version
success = repository_version.delete_repository_version(client, namespace, repository_uuid, version_uuid)
```

### Tag Management

**Location**: `src/endor_cockpit/resources/tag_management.py`

```python
from endor_cockpit.resources import tag_management

# Add repository version tag
tag_management.add_repository_version_tag(client, namespace, repository_uuid, version_uuid, "production")

# Remove repository version tag
tag_management.remove_repository_version_tag(client, namespace, repository_uuid, version_uuid, "staging")

# List repository version tags
tags = tag_management.list_repository_version_tags(client, namespace, repository_uuid, version_uuid)
```

---

## Relationships

<!-- ~400 tokens | Query: "How do repository versions relate to other resources?" -->

### Parent Resources
- **Repository**: RepositoryVersion belongs to exactly one Repository
- **Namespace**: RepositoryVersion belongs to a specific namespace

### Child Resources
- **Findings**: Generated from scans of repository versions
- **Scans**: Analyze repository versions for security issues
- **Metrics**: Analytics data for repository versions

### Related Resources
- **Project**: Through parent Repository
- **PackageVersions**: Dependencies found in repository versions

### Relationship Patterns
```python
# Get repository version with related data
version = repository_version.get_repository_version(client, namespace, repository_uuid, version_uuid)

# Get parent repository
repository = repository.get_repository(client, namespace, version.spec.repository_uuid)

# Get project that owns this version
project = project.get_project(client, namespace, repository.spec.project_uuid)

# Get findings for this version
findings = finding.list_findings(client, namespace)
version_findings = [f for f in findings if f.spec.repository_version_uuid == version_uuid]
```

---

## Common Issues

<!-- ~300 tokens | Query: "What are common repository version issues?" -->

### Version Not Found
**Issue**: Repository version doesn't exist
**Solution**: Check if repository has versions, create version for branch/tag

### Update Failures
**Issue**: Repository version updates fail with validation errors
**Solution**: Ensure required fields are included, use update_mask for partial updates

### Schema Drift
**Issue**: Unknown fields in API responses
**Solution**: Schema drift detection logs warnings, models handle gracefully

### Tag Management
**Issue**: Tags not persisting after updates
**Solution**: Use update_mask parameter, ensure tags field is included in model

---

## Troubleshooting

<!-- ~200 tokens | Query: "How to troubleshoot repository version issues?" -->

### Debug Repository Version Operations
```python
import logging
logging.basicConfig(level=logging.DEBUG)

# List repository versions with debug logging
versions = repository_version.list_repository_versions(client, namespace, repository_uuid)
```

### Validate Repository Version Data
```python
# Check repository version structure
version = repository_version.get_repository_version(client, namespace, repository_uuid, version_uuid)
print(f"Version: {version.meta.name}")
print(f"Repository UUID: {version.spec.repository_uuid}")
print(f"Commit SHA: {version.spec.commit_sha}")
print(f"Branch: {version.spec.branch}")
print(f"Tags: {version.meta.tags}")
```

### Common Error Messages
- **404 Not Found**: Repository version doesn't exist
- **400 Bad Request**: Invalid payload or missing required fields
- **403 Forbidden**: Insufficient permissions
- **Schema Drift Warnings**: Unknown fields detected (non-blocking)

---

*This resource provides comprehensive repository version management capabilities for Endor Labs platform integration.*
