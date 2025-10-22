# Endor Labs Resource Guide

> **Comprehensive guide for all Endor Labs resources with examples, descriptions, and API specifications**

## Overview

This guide provides detailed information about all Endor Labs resources, including example outputs, descriptions, service names, and API endpoints. This document serves as the canonical reference for implementing resource operations in the Endor Cockpit SDK.

> **⚠️ AUTHORITY NOTICE**: This Resource Guide is the **authoritative source** for determining which HTTP methods are supported by each resource type. Always consult this guide before implementing tests or operations to ensure compatibility with the actual API capabilities.

### API Operations Support Matrix

| Resource | GET | POST | PATCH | DELETE |
|----------|-----|------|-------|--------|
| **Project** | ✅ | ✅ | ✅ | ✅ |
| **Policy** | ✅ | ✅ | ✅ | ❌ |
| **Namespace** | ✅ | ✅ | ✅ | ❌ |
| **Finding** | ✅ | ❌ | ✅ | ❌ |
| **PackageVersion** | ✅ | ❌ | ❌ | ❌ |
| **Repository** | ✅ | ❌ | ❌ | ❌ |
| **RepositoryVersion** | ✅ | ❌ | ❌ | ❌ |

> **Note**: Not all resources support all HTTP methods. Always check this matrix before implementing operations or tests.

## Implementation Status

### ✅ **FULLY IMPLEMENTED (Base Class Inheritance)**
- **Finding** - ✅ Refactored to inherit from BaseResource
- **Policy** - ✅ Refactored to inherit from BaseResource  
- **Project** - ✅ Refactored to inherit from BaseResource
- **Namespace** - ✅ Refactored to inherit from BaseResource
- **PackageVersion** - ✅ Refactored to inherit from BaseResource
- **Repository** - ✅ Refactored to inherit from BaseResource
- **RepositoryVersion** - ✅ Refactored to inherit from BaseResource

### 🔄 **PARTIALLY IMPLEMENTED (Legacy Structure)**
- **AgentTool** - Legacy implementation (cancelled)
- **AgentConfig** - Legacy implementation (cancelled)
- **AnalyticsExecutionRecord** - Legacy implementation (cancelled)

**Note**: All fully implemented resources now inherit from BaseResource and use BaseResourceOperations for consistent CRUD operations with advanced filtering, masking, and pagination support.

---

## Finding

### Example Output
```json
{
  "context": {
    "id": "default",
    "type": "CONTEXT_TYPE_MAIN"
  },
  "meta": {
    "create_time": "2025-09-30T01:18:31.493Z",
    "created_by": "tgowan@endor.ai@google@api-key",
    "description": "GHSA-cchq-frgv-rjh5: vm2 Sandbox Escape vulnerability",
    "index_data": {
      "data": [
        "@ancestor=endor-solutions-tgowan",
        "spec.finding_tags=FINDING_TAGS_TRANSITIVE",
        "spec.finding_tags=FINDING_TAGS_NORMAL",
        "spec.finding_tags=FINDING_TAGS_POTENTIALLY_REACHABLE_FUNCTION",
        "spec.finding_tags=FINDING_TAGS_REACHABLE_DEPENDENCY",
        "spec.finding_tags=FINDING_TAGS_UNFIXABLE",
        "spec.finding_tags=FINDING_TAGS_CI_WARNING"
      ],
      "tenant": "endor-solutions-tgowan"
    },
    "kind": "Finding",
    "name": "dependency_with_critical_vulnerabilities",
    "parent_kind": "PackageVersion",
    "parent_uuid": "68db2e83c0f65038c5d27484",
    "update_time": "2025-10-21T03:27:55.057913208Z",
    "updated_by": "endor-solutions-tgowan/endorctl-analytics-68db2e21f07ce67cceb7ab0a-87ea89b3-t2mgh@k8s",
    "upsert_time": "2025-10-21T03:27:55.057913208Z",
    "version": "v1"
  },
  "spec": {
    "actions": {
      "policy_uuids": [
        "68f0fcb1b9e7809560d96878"
      ]
    },
    "approximation": false,
    "call_graph_analysis_type": "CALL_GRAPH_ANALYSIS_TYPE_FULL",
    "dependency_file_paths": [
      "package.json",
      "package-lock.json"
    ],
    "ecosystem": "ECOSYSTEM_NPM",
    "explanation": "A critical severity known vulnerability has been assessed against this version of the software package according to the information in OSV.dev",
    "extra_key": "GHSA-cchq-frgv-rjh5",
    "finding_categories": [
      "FINDING_CATEGORY_SECURITY",
      "FINDING_CATEGORY_VULNERABILITY"
    ],
    "finding_tags": [
      "FINDING_TAGS_TRANSITIVE",
      "FINDING_TAGS_NORMAL",
      "FINDING_TAGS_POTENTIALLY_REACHABLE_FUNCTION",
      "FINDING_TAGS_REACHABLE_DEPENDENCY",
      "FINDING_TAGS_UNFIXABLE",
      "FINDING_TAGS_CI_WARNING"
    ],
    "last_processed": "2025-10-21T03:27:55.057913208Z",
    "level": "FINDING_LEVEL_CRITICAL",
    "location_urls": [
      "https://github.com/tim-gowan/juice-shop/blob/develop/package.json"
    ],
    "method": "SYSTEM_EVALUATION_METHOD_DEFINITION_VULNERABILITIES",
    "project_uuid": "68db2e21f07ce67cceb7ab0a",
    "remediation": "Update to a version that is not vulnerable. If no such version exists, then no fix is currently possible.",
    "remediation_action": "UPDATE",
    "source_code_version": {
      "commit_sha": "a1b2c3d4e5f6789012345678901234567890abcd",
      "repository_version_uuid": "68db2e83c0f65038c5d27484"
    },
    "summary": "Critical vulnerability in vm2 package",
    "target_dependency_name": "vm2",
    "target_dependency_package_name": "vm2",
    "target_dependency_version": "3.9.19",
    "target_uuid": "68db2e83c0f65038c5d27484"
  },
  "tenant_meta": {
    "namespace": "endor-solutions-tgowan"
  },
  "uuid": "68db2e83c0f65038c5d27484"
}
```

### Description
Findings represent security vulnerabilities, compliance violations, and other issues discovered during security scans. They are the core output of Endor Labs' security analysis, containing detailed information about vulnerabilities, their severity, remediation guidance, and affected components.

**Key Characteristics:**
- **Security Focus**: Primary output of security scanning operations
- **Severity Levels**: CRITICAL, HIGH, MEDIUM, LOW, INFO
- **Categories**: VULNERABILITY, SECRETS, MALWARE, SCPM, etc.
- **Remediation**: Includes fix guidance and update recommendations
- **Context Aware**: Linked to specific projects, packages, and code locations

### Related Resource Service Name
**FindingService**

### URL Endpoints
- **Base Path**: `/v1/namespaces/{tenant_meta.namespace}/findings`

#### HTTP Methods and Specifications

**GET /v1/namespaces/{tenant_meta.namespace}/findings**
- **Purpose**: List all findings in namespace
- **Parameters**: 
  - `list_parameters.filter` - Filter expressions
  - `list_parameters.mask` - Field masking
  - `list_parameters.page_size` - Pagination size
  - `list_parameters.page_token` - Pagination token
  - `list_parameters.sort.path` - Sort field
  - `list_parameters.sort.order` - Sort order
- **Response**: `{"list": {"objects": [Finding]}}`

**GET /v1/namespaces/{tenant_meta.namespace}/findings/{finding_uuid}**
- **Purpose**: Get specific finding by UUID
- **Parameters**: None
- **Response**: `Finding` object

**PATCH /v1/namespaces/{tenant_meta.namespace}/findings/{finding_uuid}**
- **Purpose**: Update finding (tags, dismissal status)
- **Body**: `UpdateFindingPayload`
- **Parameters**: `update_mask` - Fields to update
- **Response**: Updated `Finding` object

---

## PackageVersion

### Example Output
```json
{
  "context": {
    "id": "default",
    "type": "CONTEXT_TYPE_MAIN"
  },
  "meta": {
    "create_time": "2025-09-30T01:18:31.493Z",
    "created_by": "tgowan@endor.ai@google@api-key",
    "index_data": {
      "data": [
        "@ancestor=endor-solutions-tgowan"
      ],
      "tenant": "endor-solutions-tgowan"
    },
    "kind": "PackageVersion",
    "name": "lodash@4.17.21",
    "update_time": "2025-10-21T03:27:55.057913208Z",
    "updated_by": "endor-solutions-tgowan/endorctl-analytics-68db2e21f07ce67cceb7ab0a-87ea89b3-t2mgh@k8s",
    "upsert_time": "2025-10-21T03:27:55.057913208Z",
    "version": "v1"
  },
  "processing_status": {
    "analytic_time": "2025-10-21T03:26:11.943546859Z",
    "disable_automated_scan": false,
    "scan_state": "SCAN_STATE_IDLE",
    "scan_time": "2025-10-03T05:24:45.164421100Z"
  },
  "spec": {
    "call_graph_available": true,
    "ecosystem": "ECOSYSTEM_NPM",
    "language": "JavaScript",
    "package_name": "lodash",
    "project_uuid": "68db2e21f07ce67cceb7ab0a",
    "relative_path": "node_modules/lodash",
    "release_timestamp": "2021-04-14T00:00:00Z",
    "resolution_errors": [],
    "resolved_dependencies": [
      {
        "name": "lodash",
        "version": "4.17.21",
        "ecosystem": "NPM"
      }
    ],
    "source_code_reference": {
      "commit_sha": "a1b2c3d4e5f6789012345678901234567890abcd",
      "repository_version_uuid": "68db2e83c0f65038c5d27484"
    },
    "unresolved_dependencies": []
  },
  "tenant_meta": {
    "namespace": "endor-solutions-tgowan"
  },
  "uuid": "68db2e83c0f65038c5d27484"
}
```

### Description
PackageVersion represents a specific version of a software package or dependency within a project. It contains detailed information about the package, its dependencies, ecosystem, and relationship to source code.

**Key Characteristics:**
- **Dependency Management**: Tracks package dependencies and versions
- **Ecosystem Support**: NPM, PyPI, Maven, NuGet, RubyGems
- **Call Graph Analysis**: Supports reachability analysis
- **Source Code Linking**: Connected to specific code commits
- **Vulnerability Tracking**: Linked to security findings

### Related Resource Service Name
**PackageVersionService**

### URL Endpoints
- **Base Path**: `/v1/namespaces/{tenant_meta.namespace}/package-versions`

#### HTTP Methods and Specifications

**GET /v1/namespaces/{tenant_meta.namespace}/package-versions**
- **Purpose**: List all package versions in namespace
- **Parameters**: Standard list parameters
- **Response**: `{"list": {"objects": [PackageVersion]}}`

**GET /v1/namespaces/{tenant_meta.namespace}/package-versions/{package_version_uuid}**
- **Purpose**: Get specific package version by UUID
- **Parameters**: None
- **Response**: `PackageVersion` object

---

## Policy

### Example Output
```json
{
  "meta": {
    "create_time": "2025-09-29T20:17:46.926Z",
    "created_by": "apiserver@endor.ai@x509",
    "description": "Requiring linear commit history ensures a clear record of activity for code changes making your code easier to troubleshoot and audit. Raise findings for repositories that do not enforce this.",
    "index_data": {
      "data": [
        "@ancestor=endor-solutions-tgowan"
      ],
      "tenant": "endor-solutions-tgowan"
    },
    "kind": "Policy",
    "name": "Linear commit history should be required",
    "tags": [
      "policy_category=misconfiguration",
      "platform=github",
      "compliance=cis_github_benchmark",
      "module=ci_cd_security",
      "compliance=pci_dss_4.0",
      "policy_category=compliance",
      "policyid_pci_dss=pci_dss_6.1.1",
      "policyid_pci_dss=pci_dss_6.2.3",
      "compliance=fedramp_low",
      "policyid_fedramp_low=sr-3",
      "compliance=fedramp_moderate",
      "policyid_fedramp_moderate=sr-3",
      "policyid_fedramp_moderate=sa-10",
      "compliance=ssdf_1.1",
      "policyid_ssdf=ssdf_pw_4.4",
      "policyid_ssdf=ssdf_pw_9.1",
      "policyid_ssdf=ssdf_pw_9.2",
      "compliance=cis_github_1.1.0",
      "policyid_cis_github=cis_github_level2_1.1.13"
    ],
    "update_time": "2025-09-29T20:17:46.926416051Z",
    "updated_by": "apiserver@endor.ai@x509",
    "version": "v1"
  },
  "propagate": true,
  "spec": {
    "disable": false,
    "finding": {
      "categories": [
        "FINDING_CATEGORY_SCPM"
      ],
      "explanation": "Enforcing linear history produces a clear record of activity, and as such it offers specific advantages; it is easier to follow, it is easier to revert a change, and bugs can be found more easily.",
      "external_name": "Linear commit history is not required",
      "level": "FINDING_LEVEL_MEDIUM",
      "remediation": "Enable linear commit history in your repository settings."
    },
    "finding_level": "FINDING_LEVEL_MEDIUM",
    "policy_type": "POLICY_TYPE_SCPM",
    "query_statements": [
      "SELECT * FROM repositories WHERE linear_history_required = false"
    ],
    "resource_kinds": [
      "Repository"
    ],
    "rule": "package security\n\nconfigure[result] {\n  result = {\n    \"security_method\": {\n      \"disable\": false,\n      \"parameters\": {\n        \"enable_security\": {\n          \"bool_value\": true\n        }\n      }\n    }\n  }\n}",
    "template_uuid": "68f0fcb1b9e7809560d96878",
    "template_version": "v1"
  },
  "tenant_meta": {
    "namespace": "endor-solutions-tgowan"
  },
  "uuid": "68f0fcb1b9e7809560d96878"
}
```

### Description
Policies define security rules, compliance requirements, and governance standards that are evaluated against resources. They contain rule logic, finding definitions, and compliance mappings.

**Key Characteristics:**
- **Rule Engine**: Uses OPA (Open Policy Agent) for rule evaluation
- **Compliance Mapping**: Links to standards like PCI DSS, FedRAMP, CIS
- **Finding Generation**: Creates findings when violations are detected
- **Hierarchical**: Can be propagated to child namespaces
- **Template Based**: Built from policy templates

### Related Resource Service Name
**PolicyService**

### URL Endpoints
- **Base Path**: `/v1/namespaces/{tenant_meta.namespace}/policies`

#### HTTP Methods and Specifications

**GET /v1/namespaces/{tenant_meta.namespace}/policies**
- **Purpose**: List all policies in namespace
- **Parameters**: Standard list parameters
- **Response**: `{"list": {"objects": [Policy]}}`

**GET /v1/namespaces/{tenant_meta.namespace}/policies/{policy_uuid}**
- **Purpose**: Get specific policy by UUID
- **Parameters**: None
- **Response**: `Policy` object

**POST /v1/namespaces/{tenant_meta.namespace}/policies**
- **Purpose**: Create new policy
- **Body**: `CreatePolicyPayload`
- **Response**: Created `Policy` object

**PATCH /v1/namespaces/{tenant_meta.namespace}/policies/{policy_uuid}**
- **Purpose**: Update policy
- **Body**: `UpdatePolicyPayload`
- **Parameters**: `update_mask` - Fields to update
- **Response**: Updated `Policy` object

**DELETE /v1/namespaces/{tenant_meta.namespace}/policies/{policy_uuid}**
- **Purpose**: Delete policy
- **Parameters**: None
- **Response**: Success confirmation

---

## AgentTool

### Example Output
```json
{
  "meta": {
    "description": "Tool for analyzing code and generating security findings",
    "name": "code_analyzer_tool"
  },
  "spec": {
    "input_schema": {
      "type": "object",
      "properties": {
        "code_path": {
          "type": "string",
          "description": "Path to the code file to analyze"
        },
        "analysis_type": {
          "type": "string",
          "enum": ["sast", "secrets", "dependencies"],
          "description": "Type of analysis to perform"
        }
      },
      "required": ["code_path", "analysis_type"]
    }
  }
}
```

### Description
AgentTool represents AI agent capabilities and tools available for automated analysis. These tools extend the functionality of AI agents with specific analysis capabilities.

**Key Characteristics:**
- **AI Integration**: Extends AI agent capabilities
- **Schema Defined**: Input/output schemas for tool usage
- **Analysis Focus**: Security, code quality, dependency analysis
- **Automated Execution**: Can be triggered by AI agents
- **Extensible**: New tools can be added dynamically

### Related Resource Service Name
**AgentToolService**

### URL Endpoints
- **Base Path**: `/v1/namespaces/{tenant_meta.namespace}/agent-tools`

#### HTTP Methods and Specifications

**GET /v1/namespaces/{tenant_meta.namespace}/agent-tools**
- **Purpose**: List all agent tools in namespace
- **Parameters**: Standard list parameters
- **Response**: `{"list": {"objects": [AgentTool]}}`

**GET /v1/namespaces/{tenant_meta.namespace}/agent-tools/{agent_tool_uuid}**
- **Purpose**: Get specific agent tool by UUID
- **Parameters**: None
- **Response**: `AgentTool` object

---

## RepositoryVersion

### Example Output
```json
{
  "context": {
    "id": "default",
    "type": "CONTEXT_TYPE_MAIN"
  },
  "meta": {
    "create_time": "2025-09-30T01:18:31.493Z",
    "created_by": "tgowan@endor.ai@google@api-key",
    "index_data": {
      "data": [
        "@ancestor=endor-solutions-tgowan"
      ],
      "tenant": "endor-solutions-tgowan"
    },
    "kind": "RepositoryVersion",
    "name": "develop",
    "parent_kind": "Repository",
    "parent_uuid": "68db2e21f07ce67cceb7ab0a",
    "update_time": "2025-10-21T03:27:55.057913208Z",
    "updated_by": "endor-solutions-tgowan/endorctl-analytics-68db2e21f07ce67cceb7ab0a-87ea89b3-t2mgh@k8s",
    "upsert_time": "2025-10-21T03:27:55.057913208Z",
    "version": "v1"
  },
  "scan_object": {
    "scan_id": "scan_12345",
    "scan_time": "2025-10-21T03:27:55.057913208Z",
    "scan_type": "full_scan"
  },
  "spec": {
    "version": "a1b2c3d4e5f6789012345678901234567890abcd"
  },
  "tenant_meta": {
    "namespace": "endor-solutions-tgowan"
  },
  "uuid": "68db2e83c0f65038c5d27484"
}
```

### Description
RepositoryVersion represents a specific snapshot or version of a repository (commit, branch, or tag). It provides the context for security scans and analysis at a specific point in time.

**Key Characteristics:**
- **Version Control Integration**: Linked to Git commits, branches, tags
- **Scan Context**: Provides context for security analysis
- **Source Code Access**: Enables analysis of specific code versions
- **Hierarchical**: Belongs to a parent Repository
- **Immutable**: Represents a fixed point in time

### Related Resource Service Name
**RepositoryVersionService**

### URL Endpoints
- **Base Path**: `/v1/namespaces/{tenant_meta.namespace}/repository-versions`

#### HTTP Methods and Specifications

**GET /v1/namespaces/{tenant_meta.namespace}/repository-versions**
- **Purpose**: List all repository versions in namespace
- **Parameters**: Standard list parameters
- **Response**: `{"list": {"objects": [RepositoryVersion]}}`

**GET /v1/namespaces/{tenant_meta.namespace}/repository-versions/{repository_version_uuid}**
- **Purpose**: Get specific repository version by UUID
- **Parameters**: None
- **Response**: `RepositoryVersion` object

---

## Project

### Example Output
```json
{
  "meta": {
    "create_time": "2025-09-30T01:10:57.727Z",
    "created_by": "tgowan@endor.ai@google@api-key",
    "index_data": {
      "data": [
        "@ancestor=endor-solutions-tgowan"
      ],
      "tenant": "endor-solutions-tgowan"
    },
    "kind": "Project",
    "name": "https://github.com/tim-gowan/juice-shop.git",
    "update_time": "2025-10-21T03:27:58.065171141Z",
    "updated_by": "scheduler@endor.ai@x509",
    "version": "v1"
  },
  "processing_status": {
    "analytic_time": "2025-10-21T03:26:11.943546859Z",
    "disable_automated_scan": true,
    "scan_state": "SCAN_STATE_IDLE",
    "scan_time": "2025-10-03T05:24:45.164421100Z"
  },
  "spec": {
    "git": {
      "full_name": "tim-gowan/juice-shop",
      "git_clone_url": "git@github.com:tim-gowan/juice-shop.git",
      "http_clone_url": "https://github.com/tim-gowan/juice-shop.git",
      "organization": "tim-gowan",
      "path": "juice-shop",
      "web_url": "https://api.github.com/tim-gowan/juice-shop"
    },
    "internal_reference_key": "https://github.com/tim-gowan/juice-shop.git",
    "platform_source": "PLATFORM_SOURCE_GITHUB"
  },
  "tenant_meta": {
    "namespace": "endor-solutions-tgowan"
  },
  "uuid": "68db2e21f07ce67cceb7ab0a"
}
```

### Description
Project represents a Git repository or source code project that is being analyzed for security issues. It serves as the root entity for organizing security scans and findings.

**Key Characteristics:**
- **Source Control Integration**: Connected to Git repositories
- **Platform Support**: GitHub, GitLab, Bitbucket, etc.
- **Scan Management**: Controls automated scanning operations
- **Hierarchical**: Contains repositories, versions, and findings
- **Processing Status**: Tracks scan state and timing

### Related Resource Service Name
**ProjectService**

### URL Endpoints
- **Base Path**: `/v1/namespaces/{tenant_meta.namespace}/projects`

#### HTTP Methods and Specifications

**GET /v1/namespaces/{tenant_meta.namespace}/projects**
- **Purpose**: List all projects in namespace
- **Parameters**: Standard list parameters
- **Response**: `{"list": {"objects": [Project]}}`

**GET /v1/namespaces/{tenant_meta.namespace}/projects/{project_uuid}**
- **Purpose**: Get specific project by UUID
- **Parameters**: None
- **Response**: `Project` object

**POST /v1/namespaces/{tenant_meta.namespace}/projects**
- **Purpose**: Create new project
- **Body**: `CreateProjectPayload`
- **Response**: Created `Project` object

**PATCH /v1/namespaces/{tenant_meta.namespace}/projects/{project_uuid}**
- **Purpose**: Update project
- **Body**: `UpdateProjectPayload`
- **Parameters**: `update_mask` - Fields to update
- **Response**: Updated `Project` object

**DELETE /v1/namespaces/{tenant_meta.namespace}/projects/{project_uuid}**
- **Purpose**: Delete project
- **Parameters**: None
- **Response**: Success confirmation

---

## Repository

### Example Output
```json
{
  "ingested_object": {
    "ingestion_time": "2025-09-30T01:10:57.727Z",
    "raw": {
      "clone_url": "https://github.com/tim-gowan/juice-shop.git",
      "default_branch": "develop",
      "full_name": "tim-gowan/juice-shop",
      "id": 123456789,
      "name": "juice-shop",
      "private": false
    }
  },
  "meta": {
    "create_time": "2025-09-30T01:10:57.727Z",
    "created_by": "tgowan@endor.ai@google@api-key",
    "index_data": {
      "data": [
        "@ancestor=endor-solutions-tgowan"
      ],
      "tenant": "endor-solutions-tgowan"
    },
    "kind": "Repository",
    "name": "juice-shop",
    "parent_kind": "Project",
    "parent_uuid": "68db2e21f07ce67cceb7ab0a",
    "update_time": "2025-10-21T03:27:58.065171141Z",
    "updated_by": "scheduler@endor.ai@x509",
    "upsert_time": "2025-10-21T03:27:58.065171141Z",
    "version": "v1"
  },
  "spec": {
    "create_time": "2025-09-30T01:10:57.727Z",
    "default_branch": "develop",
    "http_clone_url": "https://github.com/tim-gowan/juice-shop.git",
    "platform_source": "PLATFORM_SOURCE_GITHUB"
  },
  "tenant_meta": {
    "namespace": "endor-solutions-tgowan"
  },
  "uuid": "68db2e21f07ce67cceb7ab0a"
}
```

### Description
Repository represents a specific repository within a project, containing metadata about the repository structure, branches, and source code organization.

**Key Characteristics:**
- **Repository Metadata**: Contains repository-specific information
- **Branch Management**: Tracks default branches and structure
- **Platform Integration**: Connected to source control platforms
- **Hierarchical**: Belongs to a parent Project
- **Ingestion Support**: Can contain raw platform data

### Related Resource Service Name
**RepositoryService**

### URL Endpoints
- **Base Path**: `/v1/namespaces/{tenant_meta.namespace}/repositories`

#### HTTP Methods and Specifications

**GET /v1/namespaces/{tenant_meta.namespace}/repositories**
- **Purpose**: List all repositories in namespace
- **Parameters**: Standard list parameters
- **Response**: `{"list": {"objects": [Repository]}}`

**GET /v1/namespaces/{tenant_meta.namespace}/repositories/{repository_uuid}**
- **Purpose**: Get specific repository by UUID
- **Parameters**: None
- **Response**: `Repository` object

---

## AnalyticsExecutionRecord

### Example Output
```json
{
  "context": {
    "id": "default",
    "type": "CONTEXT_TYPE_MAIN"
  },
  "meta": {
    "create_time": "2025-10-21T03:26:11.943546859Z",
    "created_by": "scheduler@endor.ai@x509",
    "description": "Analytics execution for project security analysis",
    "index_data": {
      "data": [
        "@ancestor=endor-solutions-tgowan"
      ],
      "tenant": "endor-solutions-tgowan"
    },
    "kind": "AnalyticsExecutionRecord",
    "name": "analytics_execution_68db2e21f07ce67cceb7ab0a",
    "parent_kind": "Project",
    "parent_uuid": "68db2e21f07ce67cceb7ab0a",
    "update_time": "2025-10-21T03:27:55.057913208Z",
    "updated_by": "scheduler@endor.ai@x509",
    "upsert_time": "2025-10-21T03:27:55.057913208Z",
    "version": "v1"
  },
  "spec": {
    "analytics_state": "ANALYTICS_STATE_COMPLETED",
    "analytics_time": "2025-10-21T03:26:11.943546859Z",
    "execution_stats": {
      "duration_ms": 45000,
      "findings_generated": 15,
      "packages_analyzed": 120,
      "vulnerabilities_found": 3
    },
    "platform_source": "PLATFORM_SOURCE_GITHUB",
    "project_name": "juice-shop",
    "project_uuid": "68db2e21f07ce67cceb7ab0a"
  },
  "tenant_meta": {
    "namespace": "endor-solutions-tgowan"
  },
  "uuid": "68db2e83c0f65038c5d27484"
}
```

### Description
AnalyticsExecutionRecord tracks the execution of analytics operations on projects, providing insights into processing performance, results, and operational metrics.

**Key Characteristics:**
- **Execution Tracking**: Records analytics processing runs
- **Performance Metrics**: Duration, findings generated, packages analyzed
- **State Management**: Tracks execution state and completion
- **Operational Insights**: Provides visibility into system performance
- **Project Linked**: Associated with specific projects

### Related Resource Service Name
**AnalyticsExecutionRecordService**

### URL Endpoints
- **Base Path**: `/v1/namespaces/{tenant_meta.namespace}/analytics-execution-records`

#### HTTP Methods and Specifications

**GET /v1/namespaces/{tenant_meta.namespace}/analytics-execution-records**
- **Purpose**: List all analytics execution records in namespace
- **Parameters**: Standard list parameters
- **Response**: `{"list": {"objects": [AnalyticsExecutionRecord]}}`

**GET /v1/namespaces/{tenant_meta.namespace}/analytics-execution-records/{analytics_execution_record_uuid}**
- **Purpose**: Get specific analytics execution record by UUID
- **Parameters**: None
- **Response**: `AnalyticsExecutionRecord` object

---

## AgentConfig

### Example Output
```json
{
  "meta": {
    "create_time": "2025-10-21T03:26:11.943546859Z",
    "created_by": "tgowan@endor.ai@google@api-key",
    "description": "Configuration for AI agent security analysis",
    "index_data": {
      "data": [
        "@ancestor=endor-solutions-tgowan"
      ],
      "tenant": "endor-solutions-tgowan"
    },
    "kind": "AgentConfig",
    "name": "security_analysis_agent",
    "update_time": "2025-10-21T03:27:55.057913208Z",
    "updated_by": "tgowan@endor.ai@google@api-key",
    "version": "v1"
  },
  "spec": {
    "llm": {
      "model": "gpt-4",
      "temperature": 0.1,
      "max_tokens": 4000
    },
    "system_prompt": "You are a security analysis AI agent. Analyze code for vulnerabilities and provide detailed findings.",
    "tool_names": [
      "code_analyzer",
      "vulnerability_scanner",
      "dependency_checker"
    ]
  },
  "tenant_meta": {
    "namespace": "endor-solutions-tgowan"
  },
  "uuid": "68db2e83c0f65038c5d27484"
}
```

### Description
AgentConfig defines the configuration and capabilities of AI agents used for automated security analysis and code review.

**Key Characteristics:**
- **AI Configuration**: LLM settings, prompts, and parameters
- **Tool Integration**: Defines available analysis tools
- **System Prompts**: Customizes agent behavior and focus
- **Tenant Specific**: Configurations are namespace-isolated
- **Extensible**: Supports custom tools and configurations

### Related Resource Service Name
**AgentConfigService**

### URL Endpoints
- **Base Path**: `/v1/namespaces/{tenant_meta.namespace}/agent-configs`

#### HTTP Methods and Specifications

**GET /v1/namespaces/{tenant_meta.namespace}/agent-configs**
- **Purpose**: List all agent configurations in namespace
- **Parameters**: Standard list parameters
- **Response**: `{"list": {"objects": [AgentConfig]}}`

**GET /v1/namespaces/{tenant_meta.namespace}/agent-configs/{agent_config_uuid}**
- **Purpose**: Get specific agent configuration by UUID
- **Parameters**: None
- **Response**: `AgentConfig` object

**POST /v1/namespaces/{tenant_meta.namespace}/agent-configs**
- **Purpose**: Create new agent configuration
- **Body**: `CreateAgentConfigPayload`
- **Response**: Created `AgentConfig` object

**PATCH /v1/namespaces/{tenant_meta.namespace}/agent-configs/{agent_config_uuid}**
- **Purpose**: Update agent configuration
- **Body**: `UpdateAgentConfigPayload`
- **Parameters**: `update_mask` - Fields to update
- **Response**: Updated `AgentConfig` object

---

## Namespace

### Example Output
```json
{
  "meta": {
    "create_time": "2025-09-30T01:10:57.727Z",
    "created_by": "tgowan@endor.ai@google@api-key",
    "description": "Main namespace for endor-solutions-tgowan organization",
    "index_data": {
      "data": [
        "@ancestor=endor-solutions-tgowan"
      ],
      "tenant": "endor-solutions-tgowan"
    },
    "kind": "Namespace",
    "name": "endor-solutions-tgowan",
    "tags": [
      "organization=endor-solutions",
      "environment=production"
    ],
    "update_time": "2025-10-21T03:27:58.065171141Z",
    "updated_by": "tgowan@endor.ai@google@api-key",
    "version": "v1"
  },
  "spec": {
    "full_name": "endor-solutions-tgowan"
  },
  "tenant_meta": {
    "namespace": "endor-solutions-tgowan"
  },
  "uuid": "68db2e21f07ce67cceb7ab0a"
}
```

### Description
Namespace represents a tenant namespace that provides isolation and organization for resources. It serves as the root container for all other resources.

**Key Characteristics:**
- **Tenant Isolation**: Provides resource isolation and organization
- **Hierarchical**: Can contain child namespaces
- **Resource Container**: All other resources belong to a namespace
- **Access Control**: Defines permissions and access boundaries
- **Organization**: Groups related resources together

### Related Resource Service Name
**NamespaceService**

### URL Endpoints
- **Base Path**: `/v1/namespaces/{tenant_meta.namespace}/namespaces`

#### HTTP Methods and Specifications

**GET /v1/namespaces/{tenant_meta.namespace}/namespaces**
- **Purpose**: List all namespaces in parent namespace
- **Parameters**: Standard list parameters
- **Response**: `{"list": {"objects": [Namespace]}}`

**GET /v1/namespaces/{tenant_meta.namespace}/namespaces/{namespace_uuid}**
- **Purpose**: Get specific namespace by UUID
- **Parameters**: None
- **Response**: `Namespace` object

**POST /v1/namespaces/{tenant_meta.namespace}/namespaces`
- **Purpose**: Create new child namespace
- **Body**: `CreateNamespacePayload`
- **Response**: Created `Namespace` object

**PATCH /v1/namespaces/{tenant_meta.namespace}/namespaces/{namespace_uuid}`
- **Purpose**: Update namespace
- **Body**: `UpdateNamespacePayload`
- **Parameters**: `update_mask` - Fields to update
- **Response**: Updated `Namespace` object

---

## Universal API Patterns

### Standard List Parameters
All list endpoints support these universal parameters:
- `list_parameters.filter` - Filter expressions
- `list_parameters.mask` - Field masking
- `list_parameters.page_size` - Pagination size
- `list_parameters.page_token` - Pagination token
- `list_parameters.sort.path` - Sort field
- `list_parameters.sort.order` - Sort order (asc/desc)
- `list_parameters.count` - Count only mode
- `list_parameters.disable_pagination` - Disable pagination

### Standard Response Format
All list endpoints return:
```json
{
  "list": {
    "objects": [ResourceObject],
    "response": {}
  }
}
```

### Standard HTTP Methods
Most resources support:
- **GET** - List and retrieve operations
- **POST** - Create operations (where applicable)
- **PATCH** - Update operations (where applicable)
- **DELETE** - Delete operations (where applicable)

---

*This Resource Guide provides comprehensive information for implementing all Endor Labs resources in the Cockpit SDK. Each resource follows consistent patterns while providing resource-specific functionality.*
