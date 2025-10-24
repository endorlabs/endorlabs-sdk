# Tag Findings and Create Exception Policy - Example Usage

This document shows how to use the two new maneuvers to tag secrets findings in the `create_auth_policy.py` file and create an exception policy to suppress them.

## Overview

The workflow consists of two steps:
1. **Tag Findings**: Tag specific findings as 'false-positive'
2. **Create Exception Policy**: Create a policy to automatically suppress tagged findings

## Step 1: Tag Secrets Findings

Tag all secrets findings in the `create_auth_policy.py` file:

```bash
uv run python maneuvers/tag_findings.py \
  --namespace "endor-solutions-tgowan.cockpit" \
  --repository-url "https://github.com/Endor-Solutions-Architecture/endor-cockpit" \
  --finding-categories "FINDING_CATEGORY_SECRETS" \
  --file-path "maneuvers/create_auth_policy.py" \
  --tag "false-positive" \
  --dry-run
```

**Expected Output**: Should find 3 secrets findings in the create_auth_policy.py file.

**What this does:**
- Finds the project by repository URL
- Filters findings to only secrets findings in the specific file
- Tags them with 'false-positive'
- Shows what would be tagged (with --dry-run)

## Step 2: Create Exception Policy

Create a policy to suppress all findings tagged as 'false-positive':

```bash
uv run python maneuvers/create_exception_policy.py \
  --namespace "endor-solutions-tgowan.cockpit" \
  --repository-url "https://github.com/Endor-Solutions-Architecture/endor-cockpit" \
  --policy-name "Endor Cockpit - False Positive Exceptions" \
  --tag "false-positive" \
  --description "Suppresses findings tagged as false-positive during manual triage for create_auth_policy.py secrets" \
  --dry-run
```

**What this does:**
- Finds the same project by repository URL
- Creates an exception policy with a Rego rule
- The rule suppresses any finding with the 'false-positive' tag
- Shows the policy payload (with --dry-run)

## Complete Workflow (Without Dry Run)

```bash
# Step 1: Tag the findings
uv run python maneuvers/tag_findings.py \
  --namespace "endor-solutions-tgowan.cockpit" \
  --repository-url "https://github.com/Endor-Solutions-Architecture/endor-cockpit" \
  --finding-categories "FINDING_CATEGORY_SECRETS" \
  --file-path "maneuvers/create_auth_policy.py" \
  --tag "false-positive"

# Step 2: Create the exception policy
uv run python maneuvers/create_exception_policy.py \
  --namespace "endor-solutions-tgowan.cockpit" \
  --repository-url "https://github.com/Endor-Solutions-Architecture/endor-cockpit" \
  --policy-name "Endor Cockpit - False Positive Exceptions" \
  --tag "false-positive" \
  --description "Suppresses findings tagged as false-positive during manual triage for create_auth_policy.py secrets"
```

**Expected Results**:
- Step 1: Should tag 3 findings with 'false-positive'
- Step 2: Should create an exception policy that suppresses those tagged findings

## Alternative: Using Project UUID

If you already know the project UUID, you can use it directly:

```bash
# Step 1: Tag findings using project UUID
uv run python maneuvers/tag_findings.py \
  --namespace "endor-solutions-tgowan.cockpit" \
  --project-uuid "your-project-uuid-here" \
  --finding-categories "FINDING_CATEGORY_SECRETS" \
  --file-path "maneuvers/create_auth_policy.py" \
  --tag "false-positive"

# Step 2: Create exception policy using project UUID
uv run python maneuvers/create_exception_policy.py \
  --namespace "endor-solutions-tgowan.cockpit" \
  --project-uuid "your-project-uuid-here" \
  --policy-name "Endor Cockpit - False Positive Exceptions" \
  --tag "false-positive"
```

## What the Exception Policy Does

The created exception policy uses this Rego rule:

```rego
package exceptions

match_finding[result] {
  finding := input.resource
  finding.spec.project_uuid == "your-project-uuid"
  finding.meta.tags[_] == "false-positive"
  result = {"Endor": {"Finding": finding.uuid}}
}
```

This rule:
- Targets the specific project
- Matches any finding with the 'false-positive' tag
- Suppresses those findings automatically

## Verification

After running both maneuvers:

1. **Check tagged findings**: The findings should now have the 'false-positive' tag
2. **Check exception policy**: The policy should be created and active
3. **Verify suppression**: The tagged findings should no longer appear in security reports

## Troubleshooting

- **No findings found**: Check that the project UUID is correct and findings exist
- **Tagging fails**: Verify API permissions and finding UUIDs
- **Policy creation fails**: Check Rego syntax and policy permissions
- **Findings not suppressed**: Verify the policy is active and the tag matches exactly
