# Endor Labs Rego Reference Guide

> **Complete Reference for Rego Policy Development in Endor Labs**

## Policy Types & Data Access

| Type | Purpose | Data Access | Output | Query Pattern |
|------|---------|-------------|--------|---------------|
| **Finding** | Create custom findings | `data.resources.<ResourceKind>` | Custom finding objects | `data.<package>.<function>` |
| **Action** | Trigger actions on findings | `data.resources.Finding` + `data.baseline.Finding` | Finding UUIDs | `data.<package>.<function>` |
| **Exception** | Suppress findings | `input.resource` | Finding UUIDs | `data.<package>.<function>` |

## Resource Kinds & Requirements

| Policy Type | Required Resources | Optional Resources |
|-------------|-------------------|-------------------|
| **Finding** | `PackageVersion`, `Metric` | `RepositoryVersion`, `DependencyMetadata` |
| **Action** | `Finding` | `DependencyMetadata` |
| **Exception** | `Finding` | None |

## Field Mappings

### Finding Fields
- `spec.project_uuid` - Project UUID
- `spec.level` - Severity level
- `spec.finding_categories` - Categories array
- `spec.finding_tags` - Tags array
- `spec.ecosystem` - Ecosystem type
- `spec.extra_key` - Unique finding identifier
- `spec.finding_metadata` - Finding metadata object
- `meta.name` - Finding name
- `meta.description` - Finding description
- `meta.tags` - Custom tags array
- `meta.parent_kind` - Parent resource kind
- `meta.parent_uuid` - Parent resource UUID

### Metric Fields
- `meta.name` - Metric name (e.g., "package_version_scorecard")
- `meta.parent_kind` - Parent resource kind
- `meta.parent_uuid` - Parent resource UUID
- `spec.metric_values.scorecard.score_card.overall_score` - Scorecard score

### PackageVersion Fields
- `uuid` - Package version UUID
- `spec.package_name` - Package name
- `spec.version` - Package version

## Enums & Constants (OpenAPI Sourced)

### Finding Categories (v1FindingCategory)
- `FINDING_CATEGORY_UNSPECIFIED`
- `FINDING_CATEGORY_VULNERABILITY`
- `FINDING_CATEGORY_SUPPLY_CHAIN`
- `FINDING_CATEGORY_LICENSE_RISK`
- `FINDING_CATEGORY_SCPM`
- `FINDING_CATEGORY_SECURITY`
- `FINDING_CATEGORY_OPERATIONAL`
- `FINDING_CATEGORY_SECRETS`
- `FINDING_CATEGORY_MALWARE`
- `FINDING_CATEGORY_CICD`
- `FINDING_CATEGORY_TOOLS`
- `FINDING_CATEGORY_GHACTIONS`
- `FINDING_CATEGORY_CONTAINER`
- `FINDING_CATEGORY_SAST`
- `FINDING_CATEGORY_AI_MODELS`
- `FINDING_CATEGORY_SECURITY_REVIEW`
- `FINDING_CATEGORY_SCA`

### Finding Tags (v1FindingTags)
- `FINDING_TAGS_UNSPECIFIED`
- `FINDING_TAGS_DIRECT`
- `FINDING_TAGS_TRANSITIVE`
- `FINDING_TAGS_PROJECT_INTERNAL`
- `FINDING_TAGS_NAMESPACE_INTERNAL`
- `FINDING_TAGS_REACHABLE_DEPENDENCY`
- `FINDING_TAGS_UNREACHABLE_DEPENDENCY`
- `FINDING_TAGS_POTENTIALLY_REACHABLE_DEPENDENCY`
- `FINDING_TAGS_REACHABLE_FUNCTION`
- `FINDING_TAGS_UNREACHABLE_FUNCTION`
- `FINDING_TAGS_POTENTIALLY_REACHABLE_FUNCTION`
- `FINDING_TAGS_FIXABLE`
- `FINDING_TAGS_UNFIXABLE`
- `FINDING_TAGS_PRODUCTION`
- `FINDING_TAGS_TEST`
- `FINDING_TAGS_NORMAL`
- `FINDING_TAGS_FIX_AVAILABLE`
- `FINDING_TAGS_SELF`
- `FINDING_TAGS_POLICY`
- `FINDING_TAGS_CI_BLOCKER`
- `FINDING_TAGS_VALID_SECRET`
- `FINDING_TAGS_INVALID_SECRET`
- `FINDING_TAGS_PATH_EXTERNAL`
- `FINDING_TAGS_MALWARE`
- `FINDING_TAGS_UNDER_REVIEW`
- `FINDING_TAGS_PHANTOM`
- `FINDING_TAGS_EXCEPTION`
- `FINDING_TAGS_CI_WARNING`
- `FINDING_TAGS_NOTIFICATION`
- `FINDING_TAGS_EXPLOITED`
- `FINDING_TAGS_DISPUTED`
- `FINDING_TAGS_WITHDRAWN`
- `FINDING_TAGS_FALSE_POSITIVE`
- `FINDING_TAGS_TRUE_POSITIVE`

### Severity Levels (SpecFindingLevel)
- `FINDING_LEVEL_UNSPECIFIED`
- `FINDING_LEVEL_CRITICAL`
- `FINDING_LEVEL_HIGH`
- `FINDING_LEVEL_MEDIUM`
- `FINDING_LEVEL_LOW`

### Ecosystems (Common Patterns)
- `ECOSYSTEM_PYPI`
- `ECOSYSTEM_MAVEN`
- `ECOSYSTEM_NPM`
- `ECOSYSTEM_RUBYGEMS`
- `ECOSYSTEM_PACKAGIST`

## Package Naming Patterns

### Standard Patterns
- **Finding Policies**: `package examples`, `package custom_findings`, `package security_checks`
- **Action Policies**: `package sast_notification`, `package vulnerability_alerts`, `package pr_comments`
- **Exception Policies**: `package exceptions`, `package endor.cockpit.exceptions`, `package false_positives`

### Function Naming Patterns
- **Finding**: `match_package_version_score[result]`, `match_low_score_dependencies[result]`
- **Action**: `match_sast_findings[result]`, `match_vulnerability_findings[result]`
- **Exception**: `match_finding[result]`, `match_false_positive[result]`

## Output Format Patterns

### Finding Policies
```rego
result = {
    "Endor": {
        "PackageVersion": data.resources.Metric[i].meta.parent_uuid
    },
    "Score": sprintf("%v", [score])
}
```

### Action/Exception Policies
```rego
result = {
    "Endor": {
        "Finding": data.resources.Finding[i].uuid
    }
}
```

## Data Access Patterns

### Finding Policies
```rego
data.resources.Metric[i].meta.name == "package_version_scorecard"
data.resources.PackageVersion[i].uuid
```

### Action Policies
```rego
data.resources.Finding[i].spec.finding_categories[_] == "FINDING_CATEGORY_SAST"
data.baseline.Finding[i].spec.extra_key == finding.spec.extra_key
```

### Exception Policies
```rego
finding := input.resource
finding.spec.project_uuid == "your-project-uuid"
```

## Baseline Matching Patterns

### SAST/Secrets
```rego
match_baseline(finding) {
    some i
    data.baseline.Finding[i].spec.extra_key == finding.spec.extra_key
    count(data.baseline.Finding[i].spec.finding_metadata.source_policy_info.results) == count(finding.spec.finding_metadata.source_policy_info.results)
}
```

### PackageVersion
```rego
match_baseline(finding) {
    finding.meta.parent_kind == "PackageVersion"
    some i
    data.baseline.Finding[i].meta.description == finding.meta.description
    data.baseline.Finding[i].spec.target_dependency_package_name == finding.spec.target_dependency_package_name
}
```

## Common Patterns

### Array Operations
```rego
# Check if any element matches
data.resources.Finding[i].spec.finding_categories[_] == "FINDING_CATEGORY_SAST"

# Check if any element is in list
data.resources.Finding[i].spec.finding_categories[_] in ["FINDING_CATEGORY_SAST", "FINDING_CATEGORY_SECRETS"]
```

### Conditional Logic
```rego
# AND conditions
condition1
condition2
condition3

# NOT conditions
not match_baseline(data.resources.Finding[i])
```

### Variable Assignment
```rego
score := data.resources.Metric[i].spec.metric_values.scorecard.score_card.overall_score
finding := input.resource
ids := ["CVE-2020-10683", "CVE-2019-0231"]
```

## Validation Commands

```bash
# Basic validation
endorctl validate policy --policy test.rego --query data.example.match_function

# Test with real data
endorctl validate policy --policy test.rego --query data.example.match_function --uuid $PROJECT_UUID

# JSON output
endorctl validate policy --policy test.rego --query data.example.match_function --uuid $PROJECT_UUID --output-type json > output.json
```

## Query Statement Format

**Pattern**: `data.<package-name>.<function-name>`

**Examples**:
- `data.examples.match_package_version_score`
- `data.sast_notification.match_sast_findings`
- `data.exceptions.match_finding`

---

*Complete reference for Endor Labs Rego policy development - all essential mappings, enums, and patterns in one place.*
