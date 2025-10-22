# Package Version Resource Deep-Dive

> **Comprehensive guide to Package Version resources in Endor Labs platform**

<!-- RAG METADATA
resource_type: package_version
sdk_module: src/endor_cockpit/resources/package_version.py
last_reviewed: 2025-01-19
implementation_status: fully_implemented_base_class
base_class_inheritance: true
-->

## Architecture

<!-- ~500 tokens | Query: "What is package version architecture?" -->

### Base Class Implementation

PackageVersion now inherits from the enhanced base class architecture:

```python
class PackageVersionMeta(BaseMeta):
    """PackageVersion metadata extending BaseMeta."""
    # PackageVersion-specific fields only (universal fields inherited from BaseMeta)
    pass

class PackageVersionSpec(BaseSpec):
    """PackageVersion specification extending BaseSpec."""
    # PackageVersion-specific spec fields based on Resource Guide example
    call_graph_available: bool = Field(..., description="Whether call graph analysis is available")
    ecosystem: str = Field(..., description="Package ecosystem (NPM, PyPI, Maven, etc.)")
    language: str = Field(..., description="Programming language")
    package_name: str = Field(..., description="Package name")
    project_uuid: str = Field(..., description="UUID of the project this package belongs to")
    relative_path: str = Field(..., description="Relative path to the package")
    release_timestamp: str = Field(..., description="Package release timestamp")
    resolution_errors: List[str] = Field(default_factory=list, description="Resolution errors")
    resolved_dependencies: List[dict] = Field(default_factory=list, description="Resolved dependencies")
    source_code_reference: Optional[dict] = Field(None, description="Source code reference")
    unresolved_dependencies: List[str] = Field(default_factory=list, description="Unresolved dependencies")

class PackageVersion(BaseResource):
    """PackageVersion resource model extending BaseResource."""
    # PackageVersion-specific fields (universal fields inherited from BaseResource)
    spec: PackageVersionSpec = Field(..., description="PackageVersion specification")  # type: ignore
    # Conditional attributes from Resource Guide example
    context: Optional[dict] = Field(None, description="Contextual information", alias="context")
    processing_status: Optional[dict] = Field(None, description="Processing status information", alias="processing_status")
```

**Key Benefits:**
- **Universal Attributes**: Inherits all universal fields from BaseMeta and BaseResource
- **Conditional Attributes**: Supports context and processing_status when present
- **BaseResourceOperations**: Uses consistent CRUD operations with advanced filtering
- **Schema Drift Detection**: Automatically detects unknown fields in spec
- **Type Safety**: Full type safety with Pydantic validation

### Resource Structure

Package versions in Endor Labs represent specific versions of packages found in repositories:

```
Namespace (tenant.namespace)
├── Project (repository-1)
│   └── Repository (source-code-info)
│       └── RepositoryVersion (main)
│           ├── PackageVersion (lodash@4.17.21)
│           ├── PackageVersion (react@18.2.0)
│           └── PackageVersion (express@4.18.2)
└── Project (repository-2)
    └── Repository (source-code-info)
        └── RepositoryVersion (main)
            └── PackageVersion (requests@2.28.1)
```

### Core Concepts

- **1:N with RepositoryVersion**: One RepositoryVersion can have multiple PackageVersions
- **Dependency tracking**: Represents specific package versions found in code
- **Ecosystem aware**: Tracks package ecosystem (NPM, PyPI, Maven, etc.)
- **Vulnerability target**: PackageVersions are analyzed for security issues
- **Version specific**: Each package version is tracked separately

### Lifecycle

```
RepositoryVersion → PackageVersion → Vulnerability Analysis → Findings
```

**Lifecycle States**:
- **Discovered**: Package version found in repository version
- **Analyzed**: Security analysis performed on package
- **Findings Generated**: Vulnerabilities discovered in package version
- **Updated**: New package versions discovered in scans

---

## Data Model

<!-- ~800 tokens | Query: "What are package version data structures?" -->

### SDK Implementation

**Location**: `src/endor_cockpit/resources/package_version.py:50-200`

```python
# Direct reference - see SDK for full definition
class PackageVersion(BaseModel):
    uuid: str = Field(..., description="Unique identifier for the package version")
    meta: PackageVersionMeta = Field(..., description="Package version metadata")
    spec: PackageVersionSpec = Field(..., description="Package version specification")
    tenant_meta: TenantMeta = Field(..., description="Tenant metadata")
```

### Core Properties

**PackageVersionMeta** (`src/endor_cockpit/resources/package_version.py:52-80`):
- `name`: Package version name (package@version)
- `description`: Package version description
- `tags`: General resource tags
- `create_time`, `created_by`: Creation metadata
- `update_time`, `updated_by`: Auto-managed timestamps

**PackageVersionSpec** (`src/endor_cockpit/resources/package_version.py:82-100`):
- `package_name`: Package name (e.g., "lodash")
- `version`: Package version (e.g., "4.17.21")
- `ecosystem`: Package ecosystem (NPM, PyPI, Maven, etc.)
- `repository_version_uuid`: Associated repository version UUID
- `dependency_info`: Dependency information and metadata

### Mutable vs Immutable Fields

**MUTABLE FIELDS** (can be updated via PATCH):
- `meta.description`: Package version description
- `meta.tags`: General resource tags

**IMMUTABLE FIELDS** (read-only, managed by API):
- `uuid`: Unique identifier (set at creation)
- `meta.name`: Package version name (set at creation)
- `spec.package_name`, `spec.version`: Package identity (set at creation)
- `spec.ecosystem`: Package ecosystem (set at creation)
- `spec.repository_version_uuid`: Associated repository version (set at creation)
- `meta.create_time`, `meta.created_by`: Creation metadata
- `meta.update_time`, `meta.updated_by`: Auto-managed timestamps
- `tenant_meta.namespace`: Namespace assignment

---

## Operations

<!-- ~600 tokens | Query: "How to work with package versions?" -->

### CRUD Operations

**Location**: `src/endor_cockpit/resources/package_version.py:70-90`

#### List Package Versions
```python
from endor_cockpit.resources import package_version
from endor_cockpit.types import ListParameters

# List all package versions in namespace
package_versions = package_version.list_package_versions(client, namespace)

# Advanced filtering with BaseResourceOperations
filtered_packages = package_version.list_package_versions(
    client,
    namespace,
    list_params=ListParameters(
        filter="spec.ecosystem==ECOSYSTEM_NPM",
        mask="meta.name,spec.package_name,spec.ecosystem",
        page_size=50,
        sort_field="meta.create_time",
        sort_order="desc"
    )
)
```

#### Get Package Version
```python
# Get specific package version
package_version_obj = package_version.get_package_version(client, namespace, package_version_uuid)
```

#### BaseResourceOperations Benefits

The PackageVersion resource now uses BaseResourceOperations for consistent CRUD operations:

- **Advanced Filtering**: Support for complex filter expressions
- **Field Masking**: Return only specific fields to reduce payload size
- **Pagination**: Built-in pagination support with page_size and page_token
- **Sorting**: Sort results by any field in ascending or descending order
- **Counting**: Get count of resources matching filter criteria
- **Error Handling**: Consistent error handling across all operations

#### Create Package Version
```python
from endor_cockpit.resources.package_version import CreatePackageVersionPayload, PackageVersionMeta, PackageVersionSpec

# Create new package version
payload = CreatePackageVersionPayload(
    meta=PackageVersionMeta(
        name="lodash@4.17.21",
        description="JavaScript utility library"
    ),
    spec=PackageVersionSpec(
        package_name="lodash",
        version="4.17.21",
        ecosystem="NPM",
        repository_version_uuid="repository-version-uuid-123"
    )
)
new_package_version = package_version.create_package_version(client, namespace, payload)
```

#### Update Package Version
```python
from endor_cockpit.resources.package_version import UpdatePackageVersionPayload, PackageVersionMeta

# Update package version description
payload = UpdatePackageVersionPayload(
    meta=PackageVersionMeta(description="Updated package description")
)
updated_package_version = package_version.update_package_version(
    client, namespace, package_version_uuid, payload, "meta.description"
)
```

#### Delete Package Version
```python
# Delete package version
success = package_version.delete_package_version(client, namespace, package_version_uuid)
```

### Tag Management

**Location**: `src/endor_cockpit/resources/tag_management.py`

```python
from endor_cockpit.resources import tag_management

# Add package version tag
tag_management.add_package_version_tag(client, namespace, package_version_uuid, "production")

# Remove package version tag
tag_management.remove_package_version_tag(client, namespace, package_version_uuid, "staging")

# List package version tags
tags = tag_management.list_package_version_tags(client, namespace, package_version_uuid)
```

---

## Relationships

<!-- ~400 tokens | Query: "How do package versions relate to other resources?" -->

### Parent Resources
- **RepositoryVersion**: PackageVersion belongs to exactly one RepositoryVersion
- **Namespace**: PackageVersion belongs to a specific namespace

### Child Resources
- **Findings**: Generated from vulnerability analysis of package versions
- **DependencyMetadata**: Additional dependency information

### Related Resources
- **Project**: Through parent RepositoryVersion and Repository
- **Repository**: Through parent RepositoryVersion

### Relationship Patterns
```python
# Get package version with related data
package_version = package_version.get_package_version(client, namespace, package_version_uuid)

# Get parent repository version
repository_version = repository_version.get_repository_version(
    client, namespace, package_version.spec.repository_version_uuid
)

# Get repository that owns this package version
repository = repository.get_repository(client, namespace, repository_version.spec.repository_uuid)

# Get project that owns this package version
project = project.get_project(client, namespace, repository.spec.project_uuid)

# Get findings for this package version
findings = finding.list_findings(client, namespace)
package_findings = [f for f in findings if f.spec.package_version_uuid == package_version_uuid]
```

---

## Common Issues

<!-- ~300 tokens | Query: "What are common package version issues?" -->

### Package Version Not Found
**Issue**: Package version doesn't exist
**Solution**: Check if repository version has package versions, create version for package

### Update Failures
**Issue**: Package version updates fail with validation errors
**Solution**: Ensure required fields are included, use update_mask for partial updates

### Schema Drift
**Issue**: Unknown fields in API responses
**Solution**: Schema drift detection logs warnings, models handle gracefully

### Tag Management
**Issue**: Tags not persisting after updates
**Solution**: Use update_mask parameter, ensure tags field is included in model

---

## Troubleshooting

<!-- ~200 tokens | Query: "How to troubleshoot package version issues?" -->

### Debug Package Version Operations
```python
import logging
logging.basicConfig(level=logging.DEBUG)

# List package versions with debug logging
package_versions = package_version.list_package_versions(client, namespace)
```

### Validate Package Version Data
```python
# Check package version structure
package_version_obj = package_version.get_package_version(client, namespace, package_version_uuid)
print(f"Package: {package_version_obj.spec.package_name}")
print(f"Version: {package_version_obj.spec.version}")
print(f"Ecosystem: {package_version_obj.spec.ecosystem}")
print(f"Repository Version UUID: {package_version_obj.spec.repository_version_uuid}")
print(f"Tags: {package_version_obj.meta.tags}")
```

### Common Error Messages
- **404 Not Found**: Package version doesn't exist
- **400 Bad Request**: Invalid payload or missing required fields
- **403 Forbidden**: Insufficient permissions
- **Schema Drift Warnings**: Unknown fields detected (non-blocking)

---

*This resource provides comprehensive package version management capabilities for Endor Labs platform integration.*
