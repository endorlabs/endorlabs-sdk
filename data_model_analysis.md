# Endor Labs Data Model Analysis

## Complete Data Model Relationships

Based on extensive `endorctl` exploration and maneuver script development, here's the comprehensive data model for Endor Labs resources:

### **Finding → RepositoryVersion → Project Chain**

```
Finding (68fa4db0b537e079da5f5c36)
    ↓ parent_uuid & target_uuid
RepositoryVersion (68f3b5dde67c6b402406da33)
    ↓ parent_uuid  
Project (68f3b5ddf04afdad6f14be97)
```

### **Key Data Model Insights**

#### **1. Finding Structure**
- **UUID**: `68fa4db0b537e079da5f5c36`
- **Parent**: RepositoryVersion (`68f3b5dde67c6b402406da33`)
- **Target**: RepositoryVersion (`68f3b5dde67c6b402406da33`)
- **Project**: `68f3b5ddf04afdad6f14be97`
- **Categories**: `["FINDING_CATEGORY_SECURITY", "FINDING_CATEGORY_SAST"]`
- **Method**: `SYSTEM_EVALUATION_METHOD_DEFINITION_POLICIES`
- **Level**: `FINDING_LEVEL_CRITICAL`

#### **2. RepositoryVersion Structure**
- **UUID**: `68f3b5dde67c6b402406da33`
- **Name**: `dev`
- **Parent**: Project (`68f3b5ddf04afdad6f14be97`)
- **Version**: `{ref: "dev", sha: "6a1baf07cee1654f722fa0dccaaa9d71fac47c51"}`

#### **3. Project Structure**
- **UUID**: `68f3b5ddf04afdad6f14be97`
- **Name**: `https://github.com/Endor-Solutions-Architecture/endor-cockpit.git`
- **Git Info**: Full GitHub repository details

#### **4. Repository Structure**
- **UUID**: `68f3b5dd37b4931f9722a94d`
- **Name**: `https://github.com/Endor-Solutions-Architecture/endor-cockpit.git`
- **Parent**: Project (`68f3b5ddf04afdad6f14be97`)

### **Critical Discovery for Rego Rules**

The **RepositoryVersion UUID** (`68f3b5dde67c6b402406da33`) is the correct target for Rego rules because:

1. **Finding's `target_uuid`**: Points to RepositoryVersion
2. **Finding's `parent_uuid`**: Points to RepositoryVersion  
3. **API Requirement**: "Finding policies must return the Endor uuid of a Repository, RepositoryVersion, or PackageVersion"

### **Rego Rule Solution**

The correct Rego rule should return the **RepositoryVersion UUID**:

```rego
package endor.cockpit.exceptions

suppress[result] {
  input.resource.spec.project_uuid == "68f3b5ddf04afdad6f14be97"
  input.resource.spec.finding_tags[_] == "false-positive"
  
  result = "68f3b5dde67c6b402406da33"  # RepositoryVersion UUID
}
```

### **Data Model Hierarchy**

```
Project (68f3b5ddf04afdad6f14be97)
├── Repository (68f3b5dd37b4931f9722a94d)
├── RepositoryVersion (68f3b5dde67c6b402406da33)
│   └── Finding (68fa4db0b537e079da5f5c36)
└── Other RepositoryVersions...
```

### **Key Relationships**

1. **Project** → **Repository** (1:1)
2. **Project** → **RepositoryVersion** (1:many)
3. **RepositoryVersion** → **Finding** (1:many)
4. **Finding** → **Project** (many:1, via project_uuid)

### **API Validation Requirements**

- **Finding Policies**: Must return Repository, RepositoryVersion, or PackageVersion UUID
- **RepositoryVersion UUID**: `68f3b5dde67c6b402406da33` ✅ (This is what we need!)
- **Repository UUID**: `68f3b5dd37b4931f9722a94d` (Alternative option)
- **Project UUID**: `68f3b5ddf04afdad6f14be97` ❌ (Not accepted for finding policies)

## **Extended Data Model Relationships**

### **Resource Hierarchy & Cardinality**

```
Project (1)
├── Repository (1) 
├── RepositoryVersion (many) - branches/commits
│   └── Finding (many) - SAST, dependency, policy findings
├── PackageVersion (many) - dependency versions
└── Policy (many) - exception, system, user policies
```

### **Detailed Resource Relationships**

#### **1. Project → Repository (1:1)**
- **Relationship**: Each project has exactly one repository
- **Navigation**: `Project.spec.git` → Repository metadata
- **Key Fields**: 
  - `Project.spec.git.web_url` → Repository URL
  - `Project.spec.git.full_name` → Repository name
  - `Project.spec.git.organization` → Repository organization

#### **2. Project → RepositoryVersion (1:many)**
- **Relationship**: Each project can have multiple repository versions (branches, commits)
- **Navigation**: `RepositoryVersion.parent_uuid` → `Project.uuid`
- **Key Fields**:
  - `RepositoryVersion.spec.version.ref` → Branch name (e.g., "dev", "main")
  - `RepositoryVersion.spec.version.sha` → Commit SHA
  - `RepositoryVersion.meta.name` → Branch/commit identifier

#### **3. RepositoryVersion → Finding (1:many)**
- **Relationship**: Each repository version can have multiple findings
- **Navigation**: `Finding.parent_uuid` & `Finding.spec.target_uuid` → `RepositoryVersion.uuid`
- **Key Fields**:
  - `Finding.spec.project_uuid` → Project reference
  - `Finding.spec.finding_categories` → Finding type (SAST, dependency, policy)
  - `Finding.spec.method` → Analysis method
  - `Finding.spec.level` → Severity level

#### **4. Project → Finding (1:many)**
- **Relationship**: Direct project-to-finding relationship via `project_uuid`
- **Navigation**: `Finding.spec.project_uuid` → `Project.uuid`
- **Use Case**: Cross-branch finding aggregation

### **Resource Lifecycle & States**

#### **Project States**
- **SCAN_STATE_IDLE**: No active scanning
- **SCAN_STATE_SCANNING**: Currently being scanned
- **SCAN_STATE_QUEUED**: Waiting for scan

#### **RepositoryVersion States**
- **STATUS_SCANNED**: Successfully scanned
- **STATUS_SCANNING**: Currently being scanned
- **STATUS_FAILED**: Scan failed

#### **Finding States**
- **FINDING_LEVEL_CRITICAL**: Critical severity
- **FINDING_LEVEL_HIGH**: High severity
- **FINDING_LEVEL_MEDIUM**: Medium severity
- **FINDING_LEVEL_LOW**: Low severity

### **Finding Categories & Methods**

#### **Finding Categories**
- **FINDING_CATEGORY_SECURITY**: Security-related findings
- **FINDING_CATEGORY_SAST**: Static Application Security Testing
- **FINDING_CATEGORY_DEPENDENCY**: Dependency vulnerabilities
- **FINDING_CATEGORY_POLICY**: Policy violations

#### **Analysis Methods**
- **SYSTEM_EVALUATION_METHOD_DEFINITION_POLICIES**: Policy-based analysis
- **SYSTEM_EVALUATION_METHOD_DEFINITION_VULNERABILITIES**: Vulnerability scanning
- **SYSTEM_EVALUATION_METHOD_SAST**: Static analysis

### **API Filtering & Query Patterns**

#### **Project Discovery**
```bash
# By repository URL
endorctl api list -r Project --filter 'spec.git.web_url=="https://github.com/org/repo.git"'

# By repository name
endorctl api list -r Project --filter 'meta.name=="https://github.com/org/repo.git"'
```

#### **Finding Discovery**
```bash
# By project and category
endorctl api list -r Finding --filter 'spec.project_uuid=="PROJECT_UUID" AND spec.finding_categories=="FINDING_CATEGORY_SAST"'

# By repository version
endorctl api list -r Finding --filter 'spec.target_uuid=="REPO_VERSION_UUID"'
```

#### **RepositoryVersion Discovery**
```bash
# By project
endorctl api list -r RepositoryVersion --filter 'spec.project_uuid=="PROJECT_UUID"'

# By branch
endorctl api list -r RepositoryVersion --filter 'spec.version.ref=="main"'
```

### **Policy Integration Patterns**

#### **Exception Policy Requirements**
- **Target Types**: Repository, RepositoryVersion, or PackageVersion UUIDs
- **Rego Rule Pattern**: `match_finding[result]` with structured return
- **Return Format**: `{"Endor": {"Finding": finding.uuid}}`

#### **Policy Scope Options**
1. **Project-level**: All findings in a project
2. **RepositoryVersion-level**: All findings in a specific branch/commit
3. **Finding-level**: Specific finding types or categories

### **Data Model Validation Rules**

#### **Required Fields**
- **Project**: `spec.git.web_url`, `spec.git.full_name`
- **RepositoryVersion**: `spec.version.ref`, `spec.version.sha`, `parent_uuid`
- **Finding**: `spec.project_uuid`, `spec.finding_categories`, `spec.level`

#### **Optional Fields**
- **Project**: `processing_status.scan_time` (can be null)
- **Finding**: `spec.source_code_version`, `spec.finding_metadata`

#### **Schema Drift Handling**
- **Ignored Fields**: `tenant`, `data`, `will_be_deleted_at`, `search_score`, `scan_time`
- **Flexible Fields**: `actions`, `exceptions`, `location_urls` (can be list or dict)

### **Multi-Branch Support**

#### **Branch Isolation**
- **Implicit**: API returns findings from most recent/active branches
- **Explicit**: Filter by `RepositoryVersion.spec.version.ref`
- **Cross-branch**: Use `Project.spec.project_uuid` for all branches

#### **RepositoryVersion UUIDs**
- **Dev Branch**: `68f3b5dde67c6b402406da33`
- **Main Branch**: `68f3e40ce563d66b71e6d4c2`
- **Other Branches**: Dynamic based on repository activity

### **Tagging & Metadata Patterns**

#### **Finding Tags**
- **System Tags**: `FINDING_TAGS_POLICY`, `FINDING_TAGS_NORMAL`, `FINDING_TAGS_EXCEPTION`
- **Custom Tags**: `meta.tags` (user-defined, persistent)
- **System Tags**: `spec.finding_tags` (system-managed, non-persistent for custom)

#### **Metadata Fields**
- **Finding Metadata**: `spec.finding_metadata.custom` for SAST-specific data
- **Source Policy Info**: `spec.finding_metadata.source_policy_info` for policy details
- **Location URLs**: `spec.location_urls` for file/line references

### **API Response Patterns**

#### **Pagination**
- **Page Size**: 50 items per page (recommended)
- **Page Token**: Use for subsequent pages
- **Total Count**: Available in response metadata

#### **Filtering**
- **Exact Match**: `field=="value"`
- **Array Contains**: `field[_]=="value"`
- **Multiple Conditions**: `field1=="value1" AND field2=="value2"`

#### **Sorting**
- **Default**: By creation time (newest first)
- **Custom**: By severity level, finding category, etc.
- **Fields**: `spec.level`, `meta.create_time`, `spec.finding_categories`

### **Error Handling Patterns**

#### **Common Validation Errors**
- **Missing Required Fields**: Ensure all required fields are present
- **Type Mismatches**: Handle list vs dict schema drift
- **Null Values**: Make optional fields nullable when appropriate

#### **API Error Responses**
- **400 Bad Request**: Invalid filter syntax or missing required fields
- **403 Forbidden**: Insufficient permissions
- **404 Not Found**: Resource doesn't exist
- **500 Internal Server Error**: Server-side issues

### **Performance Considerations**

#### **Query Optimization**
- **Indexed Fields**: `project_uuid`, `finding_categories`, `level`
- **Filter Order**: Most selective filters first
- **Page Size**: Balance between performance and memory usage

#### **Rate Limiting**
- **API Limits**: Respect rate limits for bulk operations
- **Retry Logic**: Implement exponential backoff
- **Batch Operations**: Group related operations when possible

### **Integration Patterns**

#### **SDK Usage**
- **Resource Classes**: Use typed resource classes for type safety
- **List Parameters**: Use `ListParameters` for filtering and pagination
- **Error Handling**: Implement comprehensive error handling

#### **Raw API Access**
- **Bypass Pydantic**: Use raw API client for complex operations
- **Custom Headers**: Set appropriate content-type and accept headers
- **Update Masks**: Use update masks for partial updates

### **Next Steps**

1. ✅ **Maneuver Script**: Successfully implemented with multi-branch support
2. ✅ **Policy Creation**: Working with simplified Rego rules
3. ✅ **Finding Tagging**: Using `meta.tags` for persistence
4. ✅ **Schema Drift**: Handled with flexible field types
5. 🔄 **Future Enhancements**: 
   - Advanced filtering by branch
   - Bulk operations optimization
   - Real-time finding updates
