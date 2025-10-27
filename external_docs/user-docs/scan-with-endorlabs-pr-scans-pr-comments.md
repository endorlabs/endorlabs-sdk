---
url: https://docs.endorlabs.com/scan-with-endorlabs/pr-scans/pr-comments/
title: Pull Request comments | Endor Labs Docs
downloaded: 2025-10-27 12:58:07
---

Pull Request comments | Endor Labs Docs



* Type to search...
* ---

[Print entire section](/scan-with-endorlabs/pr-scans/pr-comments/_print.html)



# Pull Request comments

Learn how to enable and configure automated PR comments.

PR comments are automated comments added to pull requests when Endor Labs detects policy violations or security issues during scans. When a PR is raised or updated, Endor Labs runs scans on the proposed changes and adds a comment if any violations are detected based on the configured action policies.

## Types of PR comments

Endor Labs generates the following types of PR comments based on the nature of the findings in a scan:

* **PR comments for Secrets**: For findings of type `FINDING_CATEGORY_SECRETS`, Endor Labs adds a comment directly on the specific line where the secret is detected, using the line number provided in the finding object. These comments remain visible even if the secret is removed in a later scan.
* **PR comments for SCA**: For SCA findings, Endor Labs adds a single comment that applies to the entire PR. It summarizes all findings from the policy evaluation results. The comment is updated with each scan run to reflect only the latest findings.
* **PR comments for SAST**: For findings of type `FINDING_CATEGORY_SAST`, Endor Labs adds a single comment that applies to the entire PR. It summarizes all SAST-related policy violations detected during the scan. The comment is updated with each run and reflects only the latest findings.

## Enable PR comments

You can enable PR comments through one of the following methods.

* [Using Endor Labs GitHub App](#github-app)
* [Using GitHub Actions](#github-actions)
* [Using the CLI](#endor-labs-cli)

After enabling PR comments, you must [Configure an action policy](#configure-action-policy-for-pr-comments) to allow comments to be posted on pull requests.

### GitHub App

You can enable PR comments during the initial setup of the [GitHub App](../../../deployment/monitoring-scans/github-app/) or [GitHub App (Pro)](../../../deployment/monitoring-scans/github-app/github-app-pro/), or by editing an existing integration. Once enabled, Endor Labs automatically adds comments to pull requests when policy violations are detected.

### GitHub Actions

You can configure GitHub Actions to comment on PRs if there are any policy violations. Make sure that your GitHub Actions workflow includes the following configuration.

* The workflow must have a `with` clause including: `enable_pr_comments` to `true` to publish new findings as review comments and `github_token: ${{ secrets.GITHUB_TOKEN }}`. This token is automatically provisioned by GitHub when using GitHub Actions. See [GitHub configuration parameters](../../../deployment/ci-scans/scan-with-github-actions/#endor-labs-github-action-configuration-parameters) for more information.
* To grant Endor Labs the ability to comment on PRs you must include the permission `pull-requests: write`.

The following example configuration comments on PRs if a policy violation is detected.

```
      - name: Endor Labs Scan PR to Default Branch
        if: github.event_name == 'pull_request'
        uses: endorlabs/github-action@v1 # Replace v1 with the commit SHA of the latest version of the GitHub Action for enhanced security
        with:
          namespace: 'example' # Update with your Endor Labs namespace
          scan_summary_output_type: 'table'
          scan_dependencies: true
          scan_secrets: true
          pr: true
          enable_pr_comments: true
          github_token: ${{ secrets.GITHUB_TOKEN }}
```

#### PR comments example

The [main.yaml](https://github.com/endorlabs/hearts-github/blob/main/.github/workflows/main.yml) file in this [sample repository](https://github.com/endorlabs/hearts-github) contains the following configuration to enable PR comments.

```
name: Build Release
on:
  pull_request:
    branches: [main]
  workflow_dispatch:
  push:
    branches: [main]
  schedule:
    - cron: "23 23 * * 0"
jobs:
  build:
    permissions:
      pull-requests: write
      security-events: write
      contents: read
      id-token: write
      actions: read
    runs-on: ubuntu-latest
    env:
      ENDOR_NAMESPACE: "endorlabs-hearts-github"
    steps:
      - name: Endor Labs Scan PR to Default Branch
        if: github.event_name == 'pull_request'
        uses: endorlabs/github-action@v1 # Replace v1 with the commit SHA of the latest version of the GitHub Action for enhanced security
        with:
          namespace: ${{ env.ENDOR_NAMESPACE }}
          pr: true
          enable_pr_comments: true
          github_token: ${{ secrets.GITHUB_TOKEN }}
```

The [PR #10](https://github.com/endorlabs/hearts-github/pull/10) introduced a reachable vulnerability. Since the workflow has `enable_pr_comments` set as `true`, a comment is added to the PR on the policy violation.

You can expand the comment to view the following details:

* Issue type: Describes the category of the security or policy violation
* Severity: Indicates how critical the issue is.
* Impacted files or dependencies: Specifies the files and packages affected by the issue.
* Remediation steps: Specifies the required fix to resolve the detected issue.

![PR Comment Details](../../../images/pr-comment-details.png)

### Endor Labs CLI

You can generate PR comments using the CLI by including the following flags in the `endorctl scan` command.

```
endorctl scan \
  --pr \
  --enable-pr-comments \
  --github-token <your-token> \
  --scm-pr-id <pull-request-id> \
  --namespace <your-namespace>
```

Ensure that you set the following parameters:

* Set `--enable-pr-comments` to `true` to activate PR comment generation.
* Use `--scm-pr-id` to specify the pull request to comment on.
* Set the `pull-requests` permission to `write` for the `--github-token`.

Note: You can continue to use `--github-pr-id` flag, but it will be deprecated and removed in the future.

## Configure Action policy for PR comments

You must create an Action policy to receive comments on your pull request after enabling PR comments.

1. Create an [Action policy](../../../managing-policies/action-policies/).
2. Set the **Branch Type** to `PR` so the policy applies specifically to pull request scans.
3. Under **Action**, select **Enforce Policy**, then choose:
   * **Warn** to post a comment without breaking the build.
   * **Break the Build** to fail the build and block the pull request.
4. Define the scope of the policy using tags. Only projects that match the specified tags will receive PR comments.

## Customize PR comments templates

Endor Labs provides a default template with standard information that will be included in your pull requests as comments. You can use the default template, or you can choose to edit and customize this template to fit your organization’s specific requirements. You can also create custom templates using [Go Templates](https://pkg.go.dev/text/template).

1. Select **Manage** > **Integrations** from the left sidebar.
2. Click **Edit Template** next to **GitHub PR comments** under **Notifications**.
3. Make the required changes and click **Save Template**.

### PR comments data model

To create custom templates for PR comments, you must understand the data supplied to the template.

See the following protobuf specification for the `GithubCommentData` message that this template uses.

```
syntax = "proto3";

package internal.endor.ai.endor.v1;

import "google/protobuf/wrappers.proto";
import "protoc-gen-openapiv2/options/annotations.proto";
import "spec/internal/endor/v1/common.proto";
import "spec/internal/endor/v1/finding.proto";
import "spec/internal/endor/v1/package_version.proto";
import "spec/internal/endor/v1/security_review_pull_request.proto";

option go_package = "github.com/endorlabs/monorepo/src/golang/spec/internal.endor.ai/endor/v1";
option java_package = "ai.endor.internal.spec";

// The list of finding UUIDs.
message FindingUuids {
  repeated string uuids = 1;
}

// The map of dependency name to findings.
message DependencyToFindings {
  map<string, FindingUuids> dependency_to_findings = 1;
}

// The map of PackageVersion UUID to DependencyToFindings.
message PackageToDependencies {
  map<string, DependencyToFindings> package_to_dependencies = 1;
}

message GithubCommentData {
  // The header of the PR comment. Identifies the PR comment published by Endor Labs.
  // It should always be at top of the template.
  google.protobuf.StringValue comment_header = 1;

  // The footer of the PR comment.
  google.protobuf.StringValue comment_footer = 2;

  // The map of finding UUID to finding object.
  map<string, internal.endor.ai.endor.v1.Finding> findings_map = 3;

  // The map of policy UUID to policy name.
  // This will contain only the policies that are triggered or violated.
  map<string, string> policies_map = 4;

  // The map of policy UUID to the list of finding UUIDs.
  map<string, FindingUuids> policy_findings_map = 5;

  // The map of PackageVersion UUID to PackageVersion object.
  map<string, internal.endor.ai.endor.v1.PackageVersion> package_versions_map = 6;

  // The data needs to be grouped as follows:
  //
  // - Policy 1
  // 		- Package 1
  //			- Dependency Package 1
  //				- Finding 1
  //				- Finding 2
  //			- Dependency Package 2
  //				- Finding 3
  //				- Finding 4
  // 		- Package 2
  //			- Dependency Package 1
  //				- Finding 1
  //				- Finding 5
  // - Policy 2
  //		....
  //
  //		Map 0[PolicyUUID]/Map 1[PkgVerUUID]/Map 2 [Dep Names]/Finding UUID
  map<string, PackageToDependencies> data_map = 7;

  google.protobuf.StringValue api_endpoint = 8;
}

// Data structure for security review comments on pull requests.
message SecurityReviewCommentData {
  option (internal.endor.ai.endor.v1.parent_kinds) = {};
  option (grpc.gateway.protoc_gen_openapiv2.options.openapiv2_schema) = {
    json_schema: {
      extensions: {
        key: "x-internal";
        value {bool_value: true}
      }
    }
  };

  // Represents a specific security risk identified in the code review.
  message SecurityRisk {
    // Icon representing the severity level of the risk.
    google.protobuf.StringValue severity_icon = 1;

    // The category or type of the security risk.
    google.protobuf.StringValue category = 2;

    // The title or name of the security risk.
    google.protobuf.StringValue title = 3;

    // Link to the specific code location where the risk was identified.
    google.protobuf.StringValue code_link = 4;

    // Detailed description of the security risk and potential impact.
    google.protobuf.StringValue description = 5;

    // The level of the security risk.
    google.protobuf.StringValue level = 6;

    // The type of impact (improvement or regression).
    google.protobuf.StringValue impact_type = 7;
  }

  // Represents an issue that occurred during the security analysis.
  message AnalysisIssue {
    // The type of the issue.
    SecurityReviewPullRequest.Spec.IssueType type = 1;

    // A descriptive message about the issue.
    google.protobuf.StringValue message = 2;

    // List of error messages encountered during analysis.
    repeated string errors = 3;

    // List of files that were skipped during analysis.
    repeated string skipped_files = 4;

    // List of files that were summarized instead of fully analyzed.
    repeated string summarized_files = 5;
  }

  // The header of the security review comment.
  // It should always be at the top of the template.
  google.protobuf.StringValue comment_header = 1;

  // The footer of the security review comment.
  google.protobuf.StringValue comment_footer = 2;

  // A description of the changes made in the pull request.
  google.protobuf.StringValue changes_description = 3;

  // A general security assessment description.
  google.protobuf.StringValue security_description = 4;

  // The list of identified security risks in the pull request.
  repeated SecurityRisk security_risks = 5;

  // The list of issues encountered during analysis.
  repeated AnalysisIssue analysis_issues = 6;
}
```

See the following sections to understand the Finding and PackageVersion definitions that are used in this protobuf specification:

* [Finding resource kind](../../../rest-api/using-the-rest-api/data-model/resource-kinds/#finding)
* [PackageVersion resource kind](../../../rest-api/using-the-rest-api/data-model/resource-kinds/#packageversion)

See the following specification to understand the additional functions that are also available. You can access these functions by using their corresponding keys.

```
// FuncMap contains the additional functions that are available to GithubCommentTemplate.
var FuncMap = template.FuncMap{
	"now": toTime, // 'now' gives the current time

	// 'enumToString' coverts the enums for finding level, finding category and finding tags to string
	"enumToString": enumToString,

	// 'getPackageVersionURL' returns the URL for a given PackageVersion
	"getPackageVersionURL": func(apiURL string, packageVersion *endorpb.PackageVersion) string {
		result, err := common.GetPackageVersionURL(apiURL, packageVersion)
		if err != nil {
			return ""
		}
		return result
	},

	// 'getFindingURL' returns the URL for a given Finding
	"getFindingURL": func(apiURL string, finding *endorpb.Finding) string {
		result, err := common.GetFindingURL(apiURL, finding)
		if err != nil {
			return ""
		}
		return result
	},

	// 'add' returns the sum of two integers
	"add": func(n int, incr int) int {
		return n + incr
	},

	// 'getOtherFindingsPackageMarker' returns the key for _findingsWithNoPackages for lookup in DataMap
	// Not all findings are associated with a PackageVersion, such findings are grouped under this key
	// in the DataMap
	"getOtherFindingsPackageMarker": func() string { return _findingsWithNoPackages },

	// 'getOtherFindingsDependencyMarker' returns the key for _findingsWithNoDeps for lookup in DataMap
	// Not all findings are associated with a dependency, such findings are grouped under this key
	// in the DataMap
	"getOtherFindingsDependencyMarker": func() string { return _findingsWithNoDeps },

	// 'getFindingsCountString' returns a string with number of findings, example - "5 findings"
	"getFindingsCountString": func(dataMap *endorpb.PackageToDependencies) string {
		count := 0

		for _, depMap := range dataMap.PackageToDependencies {
			for _, findingMap := range depMap.DependencyToFindings {
				count += len(findingMap.Uuids)
			}
		}

		findingsStr := "findings"
		if count == 1 {
			findingsStr = "finding"
		}

		return fmt.Sprintf("%d %s", count, findingsStr)
	},

	// 'hasFindingCategory' checks if a finding has a specific category
	"hasFindingCategory": func(finding *endorpb.Finding, targetCategory string) bool {
		for _, category := range finding.GetSpec().GetFindingCategories() {
			if enumToString(category) == targetCategory {
				return true
			}
		}
		return false
	},

	// 'isNotEmptyString' checks if a string is not empty
	"isNotEmptyString": func(value string) bool {
		return value != ""
	},

	// 'getCustomLocation' extracts the location from Custom field
	"getCustomLocation": func(finding *endorpb.Finding) string {
		return getCustomFieldValue(finding, "location")
	},

	// 'getCustomCodeSnippet' extracts the code snippet from Custom field
	"getCustomCodeSnippet": func(finding *endorpb.Finding) string {
		return getCustomFieldValue(finding, "code_snippet")
	},

	"fixBackticks": fixUnclosedBackticks,

	// 'getFirstPartyReachableFunctions' extracts first-party functions from reachable paths
	"getFirstPartyReachableFunctions": getFirstPartyReachableFunctions,
}
```

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
