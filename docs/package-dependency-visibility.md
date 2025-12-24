# Package vs Dependency Visibility in Endor Labs API

## Summary

**Key Finding**: The API does **NOT** track private/public visibility at the **PackageVersion** level. Visibility is tracked at the **dependency relationship** level in two places:

1. **PackageVersion.resolved_dependencies** (embedded BOM structure)
2. **DependencyMetadata** (standalone relationship resource)

## Data Model Overview

### PackageVersion Resource

**Location**: `src/endor_cockpit/resources/package_version.py`

```python
class PackageVersion(BaseResource):
    spec: PackageVersionSpec
    # NO public/private field at package level
```

**Key Points**:
- Represents a **package itself** (e.g., `npm://my-package@1.0.0`)
- **Does NOT have** a `public` or `private` field
- Contains dependency information in `spec.resolved_dependencies`

### PackageVersion.resolved_dependencies Structure

**Location**: `src/endor_cockpit/resources/package_version.py:114-130`

```python
class Bom(BaseModel):
    """Bill of Materials for resolved dependencies."""
    dependencies: Optional[List[Union[PackageVersionDependency, dict]]]
    # Each dependency in this list can have a 'public' field
```

**OpenAPI Definition**: `BomDependency` (line 53357-53368 in openapi-swagger.json)

```json
{
  "BomDependency": {
    "properties": {
      "name": { "type": "string" },
      "public": {
        "type": "boolean",
        "description": "A boolean to know if the dependency is public or not. This field might not be set."
      }
    }
  }
}
```

**Key Points**:
- `public` field exists **within each dependency** in the BOM
- Path: `PackageVersion.spec.resolved_dependencies.dependencies[].public`
- Indicates whether **that specific dependency** is public or private
- This is **not** about the PackageVersion itself

### DependencyMetadata Resource

**Location**: `src/endor_cockpit/resources/dependency_metadata.py`

```python
class DependencyMetadata(BaseResource):
    spec: DependencyMetadataSpec

class DependencyMetadataSpec(BaseSpec):
    dependency_data: Optional[DependencyData]  # Has public field
    importer_data: Optional[ImporterData]
```

**OpenAPI Definition**: `DependencyMetadataDependencyData` (line 54804-54808)

```json
{
  "DependencyMetadataDependencyData": {
    "properties": {
      "public": {
        "type": "boolean",
        "description": "True if the dependency is public."
      }
    }
  }
}
```

**Key Points**:
- Represents the **relationship** between two PackageVersions:
  - **Importer**: The package that depends on another
  - **Dependency**: The package being depended upon
- Has `spec.dependency_data.public` field (in API, but not explicitly modeled in SDK)
- One DependencyMetadata object per dependency per PackageVersion
- Path: `DependencyMetadata.spec.dependency_data.public`
- **Note**: The SDK's `DependencyData` model doesn't explicitly include `public`, but it will be present in API responses (accessible via dict access or `model_dump()`)

## Data Model Correlation

### Relationship Diagram

```
PackageVersion (importer)
├── spec.resolved_dependencies
│   └── dependencies[]
│       └── public: boolean  ← Visibility of THIS dependency
│
└── (parent of) DependencyMetadata[]
    └── spec.dependency_data
        ├── package_version_uuid  ← Links to dependency PackageVersion
        └── public: boolean       ← Same visibility info, normalized
```

### Key Correlations

1. **Same Information, Different Structures**:
   - `PackageVersion.spec.resolved_dependencies.dependencies[].public`
   - `DependencyMetadata.spec.dependency_data.public`
   - Both indicate if a **dependency** is public/private

2. **DependencyMetadata is Normalized**:
   - Each dependency relationship gets its own DependencyMetadata resource
   - Easier to query and filter dependencies by visibility
   - Links to dependency PackageVersion via `package_version_uuid`

3. **PackageVersion BOM is Embedded**:
   - Dependencies are embedded in the PackageVersion resource
   - More convenient for getting all dependencies of a package
   - Less normalized, harder to query across packages

### Example Data Flow

**Scenario**: Package `npm://my-app@1.0.0` depends on `npm://lodash@4.17.21` (public) and `@my-org/private-lib@1.0.0` (private)

**PackageVersion (my-app)**:
```json
{
  "spec": {
    "package_name": "npm://my-app",
    "resolved_dependencies": {
      "dependencies": [
        {
          "name": "lodash@4.17.21",
          "public": true
        },
        {
          "name": "@my-org/private-lib@1.0.0",
          "public": false
        }
      ]
    }
  }
}
```

**DependencyMetadata Objects** (2 separate resources):
```json
// DependencyMetadata #1: my-app → lodash
{
  "spec": {
    "importer_data": {
      "package_version_uuid": "<my-app-uuid>"
    },
    "dependency_data": {
      "package_version_uuid": "<lodash-uuid>",
      "public": true
    }
  }
}

// DependencyMetadata #2: my-app → private-lib
{
  "spec": {
    "importer_data": {
      "package_version_uuid": "<my-app-uuid>"
    },
    "dependency_data": {
      "package_version_uuid": "<private-lib-uuid>",
      "public": false
    }
  }
}
```

## Why This Design?

### PackageVersion Has No Public Field

- A **package** can be used as both a public and private dependency depending on context
- The same package might be:
  - Public when used from public package managers (npm, PyPI)
  - Private when used from private registries
- Visibility is a **relationship property**, not an intrinsic package property

### Dependency-Level Visibility Makes Sense

- Visibility depends on:
  - Where the dependency is resolved from (public vs private registry)
  - The context of the dependency relationship
  - Package manager configuration
- The same PackageVersion can have different visibility in different dependency contexts

## Usage Patterns

### Query Dependencies by Visibility

**Using DependencyMetadata** (recommended):
```python
from endor_cockpit.resources import dependency_metadata

# List all private dependencies
# Note: public field is in API but not explicitly modeled in DependencyData
all_deps = dependency_metadata.list_dependency_metadata(
    client, namespace
)
private_deps = [
    d for d in all_deps
    if d.spec.dependency_data
    and d.spec.dependency_data.model_dump().get("public") == False
]
```

**Using PackageVersion BOM**:
```python
from endor_cockpit.resources import package_version

pkg = package_version.get_package_version(client, namespace, pkg_uuid)
if pkg.spec.resolved_dependencies:
    deps = pkg.spec.resolved_dependencies.get("dependencies", [])
    private_deps = [d for d in deps if d.get("public") == False]
```

### Check if a Package Itself is Public/Private

**Answer**: You **cannot** determine this from the PackageVersion resource alone.

**Workaround**: Check if the package appears as a dependency:
- If it appears as a dependency with `public: true` → likely public
- If it appears as a dependency with `public: false` → likely private
- But this is **inferred**, not explicit

## Summary Table

| Resource | Has Public Field? | Location | Purpose |
|----------|------------------|---------|---------|
| **PackageVersion** | ❌ No | N/A | Represents the package itself |
| **PackageVersion.resolved_dependencies** | ✅ Yes | `dependencies[].public` | Embedded BOM with dependency visibility |
| **DependencyMetadata** | ✅ Yes | `spec.dependency_data.public` | Normalized dependency relationship |

## References

- OpenAPI Spec: `external_docs/openapi-swagger.json`
  - `BomDependency` (line 53357)
  - `DependencyMetadataDependencyData` (line 54689)
- User Documentation: `external_docs/user-docs/managing-projects-packages.md`
- SDK Implementation:
  - `src/endor_cockpit/resources/package_version.py`
  - `src/endor_cockpit/resources/dependency_metadata.py`

