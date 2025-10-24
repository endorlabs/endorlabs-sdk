---
url: https://docs.endorlabs.com/rest-api/using-the-rest-api/data-model/resource-kinds/
title: Resource kinds | Endor Labs Docs
downloaded: 2025-10-23 23:25:53
---

Resource kinds | Endor Labs Docs



* Type to search...
* ---

[Print entire section](/rest-api/using-the-rest-api/data-model/resource-kinds/_print.html)



# Resource kinds

Learn about the resource kinds in the Endor Labs data model.

Here is an overview diagram of the Endor Labs data model for the most commonly used resource kinds. Lighter shading identifies the objects that are re-computed on every scan.

![data model](../../../../images/data-model.png)

This section describes the most commonly used resource kinds. For a complete list of supported resource kinds, see the [Endor Labs OpenAPI documentation](https://docs.endorlabs.com/api/).

All objects contain a reference to the project UUID, either as the parent object (`meta.parent_uuid`) or a specific field in the object-specific data if the project is not the direct parent (`spec.project_uuid` if not specified otherwise).

Use the following command to get a list of all objects of a given resource kind in your tenant.

Here are a few useful options:

* `--count`
* `--page-size=1`
* `--list-all`
* `--filter="meta.parent_uuid==<uuid>"`
* `--filter="spec.project_uuid==<uuid>"`

```
endorctl api list -r <resource-kind>
```

## Project

* This is the logical root of all the other information for a given project.
* Contains information about the source code location of a project, such as a Git repository, or a package manager package name.
* Does not have a parent and is not associated with a context.
* The object name is the HTTP clone URL, for example: `"https://github.com/definitelytyped/definitelytyped.git"`.

For more information, see the [ProjectService REST API documentation](https://docs.endorlabs.com/api/#tag/ProjectService).

## Repository

* Contains information about the source code for a project.
* Child of a Project and, just like the Project, does not belong to a context.
* There is at most one Repository per Project, but a Project may not have a Repository if there is no source code.
* The object name is the same as the Project.

For more information, see the [RepositoryService REST API documentation](https://docs.endorlabs.com/api/#tag/RepositoryService).

## RepositoryVersion

* Contains information about a specific version of a Repository.
* Has the Project as the parent.
* There are often multiple RepositoryVersions per project.
* Each RepositoryVersion is associated with a [Context](../common-fields/#context).
* The object name is the corresponding branch name, tag, or SHA, for example: `"main"`.

For more information, see the [RepositoryVersionService REST API documentation](https://docs.endorlabs.com/api/#tag/RepositoryVersionService).

## PackageVersion

* Contains information about a specific version of a package and its dependencies.
* Does not have a parent (for historical reasons), but is associated with a [Context](../common-fields/#context) and connected to the Project via `spec.project_uuid`.
* The object name is the corresponding package version name in the format `<ecosystem>://<package-name>@<version>`, for example: `"mvn://org.webjars.npm:types__json-schema@1.2.3"`.

For more information, see the [PackageVersionService REST API documentation](https://docs.endorlabs.com/api/#tag/PackageVersionService).

### Resolution errors

Details about any dependency resolution or call graph generation errors for a package version are stored in `spec.resolution_errors`. There are three categories of resolution errors, each with a separate field that can contain up to one resolution error:

1. **Unresolved** - Details in `spec.resolution_errors.unresolved` if there was an error computing the unresolved dependencies.
2. **Resolved** - Details in `spec.resolution_errors.resolved` if there was an error resolving the dependency versions.
3. **Call graph** - Details in `spec.resolution_errors.call_graph` if there was an error generating the call graph.

Each resolution error has a `status_error` field and may also contain details about the `target`, the `operation` that failed, and a `description` of the error. The following status errors are supported:

| Status Error | Description |
| --- | --- |
| STATUS\_ERROR\_BUILD | Indicates that the plugin failed to build the package version. This status error is only used for unresolved dependencies. |
| STATUS\_ERROR\_CALL\_GRAPH | Indicates that the system failed to create the call graph. This status error is only used for call graph computation. |
| STATUS\_ERROR\_DEPENDENCY | Indicates that the system failed to resolve a dependency. Usually happens when a manifest contains bad associations of dependencies and versions. This status error is only used for resolved dependencies. |
| STATUS\_ERROR\_INTERNAL | Indicates that there was an internal system failure such as a data stream error. |
| STATUS\_ERROR\_MANIFEST\_LOAD | Indicates that the system is unable to find the manifest of the language (pom.xml, packages.json, etc). This status error is only used for unresolved dependencies. |
| STATUS\_ERROR\_MANIFEST\_PARSE | Indicates that the system failed to parse the manifest. This status error is only used for unresolved dependencies. |
| STATUS\_ERROR\_MISSING\_ARTIFACT | Indicates that the system failed to compute the call graph because the package is not built. This status error is only used for call graph computation. |
| STATUS\_ERROR\_NO\_CODE\_ARTIFACT | Indicates that the package version does not have any source code. This status error is only used for call graphs. |
| STATUS\_ERROR\_PACKAGE\_VERSION\_UNAVAILABLE | Indicates that the package version is not available from the package manager. This status error is only used for unresolved dependencies. |
| STATUS\_ERROR\_UNSUPPORTED | Indicates that a package version with an unsupported language was scanned. |
| STATUS\_ERROR\_VENV | Indicates that the system failed to create the virtual environment required to generate the call graph. This status error is only applicable to Python projects. |

Below is an example resolution error in the **Resolved** category:

```
{
  "spec": {
    "resolution_errors": {
      "resolved": {
        "description": "failed to discover dependency: unable to resolve dependencies for 'requirements': unable to get direct dependencies: unable to install modules to extract dependencies: unable to resolve package version: ResolveModuleVersion: error in pypi json api for: torch, exact version: 1.9.0+cpu, err: package not found in the repository: unable to resolve dependency version: unable to discover dependencies, unable to discover dependencies",
        "operation": "python:resolvedDependencies:discover",
        "status_error": "STATUS_ERROR_DEPENDENCY",
        "target": "pypi://requirements@main"
      }
    }
  }
}
```

## DependencyMetadata

* Different from other common resource kinds as it represents the *relationship* between two PackageVersions: The **importer** and the **dependency**.
* There is one DependencyMetadata object for every dependency for every PackageVersion.
* Has the **importer** PackageVersion as the parent and exists in the same [Namespace](../common-fields/#tenantmeta) and [Context](../common-fields/#context) as the parent.
* The object name is the same as the **dependency** PackageVersion.
* Combine the object name (`meta.name`) and the parent UUID (`meta.parent_uuid`) to get a unique key.
* Connected to the Project via `spec.importer_data.project_uuid`.
* Details about the relationship are stored in `spec.dependency_data`.
  For example:

  + `spec.dependency_data.direct`
  + `spec.dependency_data.reachable`
  + `spec.dependency_data.scope`

For more information, see the [DependencyMetadataService REST API documentation](https://docs.endorlabs.com/api/#tag/DependencyMetadataService).

## LinterResult

* Contains the results of scans using third-party programs such as Gitleaks or Semgrep.
* Has a RepositoryVersion or PackageVersion as the parent.
* Belongs to the same [Context](../common-fields/#context) as the parent.
* Connected to the Project through `spec.project_uuid`.
* The object name is the name of the rule that created the result, for example: `"gen-shady-links"`.
* The result origin is stored in `spec.origin`, for example: `"LINTER_RESULT_ORIGIN_SECRETS_SCANNER"`.

For more information, see the [LinterResultService REST API documentation](https://docs.endorlabs.com/api/#tag/LinterResultService).

## Metric

* Contains the output of the analytics processing.
* Has a PackageVersion, RepositoryVersion, or Repository as the parent.
* Belongs to the same [Context](../common-fields/#context) as the parent.
* Connected to the Project via `spec.project_uuid`.
* The object name is the name of the analytic that created the metric, for example: `"package_version_scorecard"`.

For more information, see the [MetricService REST API documentation](https://docs.endorlabs.com/api/#tag/MetricService).

### Metric types

There are many different types of Metrics. The specifics are stored under `spec.metric_values.<key>.<value>`, for example: `spec.metric_values.scorefactor.score_factor_list`. Some Metrics have more than one key-value field under `spec.metric_values`. The following table lists all supported Metric types along with the corresponding paths to the Metric specific data under `spec.metric_values`.

| Metric Name | Metric Values Paths | Description |
| --- | --- | --- |
| `github_workflow_posture` | `GHWorkflowPosture.github_workflows` | Posture management of GitHub Actions workflow yaml files for a repository version. |
| `model_scorecard` | `scorecard.score_card`, `scorefactor.score_factor_list` | Scorecard for a model repository. |
| `package_version_scorecard` | `scorecard.score_card`, `scorefactor.score_factor_list` | Scorecard for a package version. |
| `pkg_version_info_for_license` | `licenseInfoType.license_info` | License information for a package version. |
| `pkg_version_stats_for_dependency` | `dependencyStatsType.dependency_stats` | Dependency related statistics for a package version. |
| `pkg_version_stats_for_linter` | `linterStats.linter_stats` | Linter related statistics for a package version. |
| `pkg_version_stats_for_secret` | `secretStats.secret_stats` | Secret related statistics for a package version. |
| `pkg_version_stats_for_vuln` | `vulnerabilityStatsType.vulnerability_stats`, `publishedVulnerabilitiesStatsType.time_tracker` | Vulnerability related statistics for a package version. |
| `repo_activity_for_commit` | `locationActivityTrackerType.time_tracker`, `locationActivityCountType.tag_counts` | Commit activity for a repository. |
| `repo_activity_for_issue` | `locationActivityTrackerType.time_tracker`, `locationActivityCountType.tag_counts` | Issue activity for a repository. |
| `repo_activity_for_pr` | `allActivityTrackerType.time_tracker`, `accountActivityTrackerType.time_tracker`, `locationActivityTrackerType.time_tracker`, `locationActivityCountType.tag_counts` | PR activity for a repository. |
| `repo_scorecard` | `scorecard.score_card`, `scorefactor.score_factor_list` | Scorecard for a repository. |
| `repo_scpm_data` | `ScpmDataType.scpm_data` | RSPM data for a repository. |
| `repo_stats_for_dependency` | `dependencyStatsType.dependency_stats` | Dependency related statistics for a repository version. |
| `repo_stats_for_file` | `fileStats.file_stats` | File related statistics for a repository version. |
| `version_activity_for_commit` | `locationActivityTrackerType.time_tracker`, `locationActivityCountType.tag_counts` | Commit activity of a repository version. |
| `version_activity_for_issue` | `locationActivityTrackerType.time_tracker`, `locationActivityCountType.tag_counts` | Issue activity of a repository version. |
| `version_activity_for_pr` | `allActivityTrackerType.time_tracker`, `accountActivityTrackerType.time_tracker`, `locationActivityTrackerType.time_tracker`, `locationActivityCountType.tag_counts` | PR activity of a repository version. |
| `version_cicd_tools` | `CiCdTools.ci_cd_tools` | List of CI/CD Tools for a repository version. |
| `version_scorecard` | `scorecard.score_card`, `scorefactor.score_factor_list` | Scorecard for a repository version. |
| `version_stats_for_dependency` | `dependencyStatsType.dependency_stats` | Dependency related statistics for a repository version. |
| `version_stats_for_file` | `fileStats.file_stats` | File related statistics for a repository version. |
| `version_stats_for_vuln` | `vulnerabilityStatsType.vulnerability_stats`, `publishedVulnerabilitiesStatsType.time_tracker` | Vulnerability related statistics for a package version. |

## Finding

* Contains details of a problem that needs to be fixed.
* Has a PackageVersion, RepositoryVersion, or Repository as the parent.
* Belongs to the same [Context](../common-fields/#context) as the parent.
* Connected to the Project via `spec.project_uuid`.
* There are many different types of Findings and new types can be created by custom [Finding Policies](../../../../managing-policies/finding-policies/).
* The object name is the Finding type, for example: `"outdated_release"`. For more information, see [Finding names and metadata](#finding-names-and-metadata) below.
* The object description contains a more specific description of the Finding, for example: `"Outdated Dependency @babel/plugin-syntax-async-generators@7.8.4"`.
* Additional finding type specific data is stored in `spec.finding_metadata`, for example: `spec.finding_metadata.vulnerability`.
* PackageVersion Findings often involve both the root PackageVersion and a dependency PackageVersion. The following details about the dependency PackageVersion are available directly in the Finding object:
  + `spec.target_dependency_name`, for example: `"@babel/plugin-syntax-async-generators"`
  + `spec.target_dependency_package_name`, for example: `"npm://@babel/plugin-syntax-async-generators@7.8.4"`
  + `spec.target_dependency_version`, for example: `"7.8.4"`
  + `spec.finding_metadata.dependency_package_version_metadata`
* The UUID of the DependencyMetadata for the dependency is stored in `spec.target_uuid`.
* There is one Finding object for every PackageVersion that includes a dependency with a given problem. If 10 PackageVersions include a dependency with a vulnerability then there will be 10 findings for the vulnerability.

For more information, see the [FindingService REST API documentation](https://docs.endorlabs.com/api/#tag/FindingService).

### Finding names and metadata

The following table lists all supported values for the Finding `meta.name` field along with an example value for the corresponding `meta.description` and an explanation.

| Finding Name | Example Description | Explanation |
| --- | --- | --- |
| `archived_source_code_repo` | `Unmaintained Dependency derive-error-chain@0.10.1` | The source code repository for this package is archived. There is no additional metadata for this finding type. |
| `bad_license` | `License Risk in Dependency org.codehaus.plexus:plexus-io@2.0.3` | The repository for this package is either missing a license or the license found is problematic. There is no additional metadata for this finding type. |
| `dependency_with_critical_vulnerabilities` | `GHSA-65fg-84f6-3jq3: SQL Injection in Log4j 1.2.x` | A critical severity known vulnerability has been assessed against this version of the software package according to the information in `OSV.dev`. Additional information about the vulnerability is stored in `spec.finding_metadata.vulnerability`. |
| `dependency_with_high_severity_vulnerabilities` | `GHSA-w9p3-5cr8-m3jj: Deserialization of Untrusted Data in Log4j 1.x` | This package version contains a vulnerability that has been marked as high severity according to the information in `OSV.dev`. Additional information about the vulnerability is stored in `spec.finding_metadata.vulnerability`. |
| `dependency_with_low_activity_score` | `Dependency tempdir@0.3.7 With Low Activity Score` | This package may be unmaintained, as determined by several factors contributing to a low activity score. Reliance on packages that are no longer maintained can make it costly or unreasonable to fix significant security risks, or quality issues. This may render the package obsolete over time. By relying on an unmaintained software package, organizations may assume the cost of maintenance and have a longer lead time for fixes on any security issues, if they are fixed at all. Additional information about the score is stored in `spec.finding_metadata.dependency_score_card` and `spec.finding_metadata.dependency_score_factor_list`. |
| `dependency_with_low_popularity_score` | `Dependency unicode-canonical-property-names-ecmascript@2.0.0 With Low Popularity Score` | Popularity is a social proxy for quality. Popular packages are more likely to remain maintained and thoroughly tested. Relying on lesser known packages for critical functions may increase operational risk. Additional information about the score is stored in `spec.finding_metadata.dependency_score_card` and `spec.finding_metadata.dependency_score_factor_list`. |
| `dependency_with_low_quality_score` | `Dependency org.slf4j:slf4j-api@1.7.6 With Low Quality Score` | This package may have an increased risk of bugs and quality issues as determined by several factors contributing to a low-quality score. A low quality score indicates a project may have an immature software development practice. Relying on packages that do not follow code development best practices can result in an increased risk of security and operational problems. Additional information about the score is stored in `spec.finding_metadata.dependency_score_card` and `spec.finding_metadata.dependency_score_factor_list`. |
| `dependency_with_low_severity_vulnerabilities` | `GHSA-5mg8-w23w-74h3: Information Disclosure in Guava` | This package version contains a vulnerability that has been marked as low severity according to the information in `OSV.dev`. Additional information about the vulnerability is stored in `spec.finding_metadata.vulnerability`. |
| `dependency_with_malicious_package` | `MAL-2023-462: Malicious code in fsevents (npm)` | This version of the software package is considered malware according to `OSV.dev`. Additional information about the malware advisory is stored in `spec.finding_metadata.vulnerability`. |
| `dependency_with_medium_severity_vulnerabilities` | `GHSA-269g-pwp5-87pp: TemporaryFolder on unix-like systems does not limit access to created files` | This package version contains a vulnerability that has been marked as medium severity according to the information in `OSV.dev`. Additional information about the vulnerability is stored in `spec.finding_metadata.vulnerability`. |
| `dependency_with_multiple_low_scores` | `Dependency esformatter-remove-trailing-commas@1.0.1 With Multiple Low Scores` | This package version has received low scores across more than one categories. This is stronger indication that the package may be problematic and presents an increased risk for security and operational problems. Additional information about the scores is stored in `spec.finding_metadata.dependency_score_card` and `spec.finding_metadata.dependency_score_factor_list`. |
| `dependency_with_very_low_activity_score` | `Dependency is-finite@1.1.0 With Very Low Activity Score` | This package is very likely to be unmaintained, as determined by several factors contributing to a very low activity score. Reliance on packages that are no longer maintained can make it costly or unreasonable to fix significant security risks, or quality issues. This may render the dependency obsolete over time. By relying on an unmaintained software package, organizations may assume the cost of maintenance and have a longer lead time for fixes on any security issues, if they are fixed at all. Additional information about the score is stored in `spec.finding_metadata.dependency_score_card` and `spec.finding_metadata.dependency_score_factor_list`. |
| `dependency_with_very_low_popularity_score` | `Dependency http-range-header@0.3.0 With Very Low Popularity Score` | Popularity is a social proxy for quality. Popular packages are more likely to remain maintained and thoroughly tested. Relying on lesser known packages for critical functions may increase operational risk. Additional information about the score is stored in `spec.finding_metadata.dependency_score_card` and `spec.finding_metadata.dependency_score_factor_list`. |
| `dependency_with_very_low_quality_score` | `Dependency org.apache.sis.core:sis-utility@1.1 With Very Low Quality Score` | This package is likely to have an increased risk of bugs and quality issues as determined by several factors contributing to a very low-quality score. A low quality score indicates a project may have an immature software development practice. Relying on packages that do not follow code development best practices can result in an increased risk of security and operational problems. Additional information about the score is stored in `spec.finding_metadata.dependency_score_card` and `spec.finding_metadata.dependency_score_factor_list`. |
| `missing_source_code` | `Missing Source Code Repository for Dependency commons-dbcp:commons-dbcp@1.4` | The package versions source code reference is not currently available. As a result, automated analysis of the package’s activity, popularity, code quality and security have not been performed. Manual assessment is required to assess the operational and security risk of this package. There is no additional metadata for this finding type. |
| `outdated_release` | `Outdated Dependency @babel/plugin-syntax-async-generators@7.8.4` | This package has had multiple later releases or a significant period of time has passed since the release of the version currently in use. Relying on outdated dependencies can result in missing important bug fixes or security patches and make upgrades more difficult. There is no additional metadata for this finding type. |
| `policy_finding` | `Code owner approval is not required` | The finding was created by a [Rego policy](../../../../managing-policies/finding-policies/). The policy UUID is stored in `spec.finding_metadata.source_policy_info.uuid`. |
| `recently_released_dependency` | `Recently Released Dependency chalk@5.6.1`. | This package version is using a recent release of a dependency. Recently released versions of dependencies are more likely to introduce supply chain risk and breaking changes. |
| `typosquatted_dependency` | `Dependency serverles@3.27.1 is a Potential Typosquat` | The name of the dependency is very similar to another package which is more popular and widely used. It is possible that this is a malicious package in the package manager with malware inserted. Additional information about the typosquatted dependency is stored in `spec.finding_metadata.typosquatted_dependency_version_metadata`. |
| `unpinned_direct_dependency` | `Unpinned Direct Dependency num-integer@0.1.45` | This package version has not pinned one of its direct dependencies. Dependencies that are not pinned to a specified version decrease the likelihood of build reproducibility and can be unexpectedly updated, which may introduce operational or security issues into your application. Unpinned dependencies expose organizations to the risk of software supply chain attacks where attackers compromise the upstream software dependency and publish a malicious version of the code. There is no additional metadata for this finding type. |
| `unreachable_direct_dependency` | `Unused Direct Dependency org.typelevel:macro-compat_2.11@1.1.1` | Static analysis of this software package indicates that this direct dependency is unused. Unused direct dependencies unnecessarily increase the size of executables, application resource utilization and, increase build time and as a result may decrease developer productivity and application performance. There is no additional metadata for this finding type. |

### Finding categories

The following finding categories are supported as possible values in the `spec.finding_categories` list. All findings must have at least one category.

| Finding Category | UI Category | Description |
| --- | --- | --- |
| `FINDING_CATEGORY_AI_MODELS` | AI Models | AI model findings |
| `FINDING_CATEGORY_CICD` | CI/CD | CI/CD pipeline findings |
| `FINDING_CATEGORY_CONTAINER` | Container | Container findings |
| `FINDING_CATEGORY_GHACTIONS` | GitHub Actions | GitHub action findings |
| `FINDING_CATEGORY_LICENSE_RISK` | License Risk | License issues |
| `FINDING_CATEGORY_MALWARE` | Malware | Malware findings |
| `FINDING_CATEGORY_OPERATIONAL` | Operational | Operational issues |
| `FINDING_CATEGORY_SAST` | SAST | SAST findings |
| `FINDING_CATEGORY_SCA` | SCA | Software Composition Analysis issues |
| `FINDING_CATEGORY_SCPM` | RSPM | Repository security posture management issues |
| `FINDING_CATEGORY_SECRETS` | Secrets | Exposed secrets |
| `FINDING_CATEGORY_SECURITY` | Security | Security issues |
| `FINDING_CATEGORY_SUPPLY_CHAIN` | Supply Chain | Supply chain specific problems (malicious packages, typosquats) |
| `FINDING_CATEGORY_TOOLS` | Tools | Tool-related findings |
| `FINDING_CATEGORY_VULNERABILITY` | Vulnerability | Vulnerability findings |

### Finding tags

The following system defined finding tags are supported as possible values in the `spec.finding_tags` list and referred to as “attributes” in the UI. Note that these are different from the free-form custom tags that are stored in the [Meta](../common-fields/#meta) field.

| Finding Tag | UI Attribute | Description |
| --- | --- | --- |
| `FINDING_TAGS_CI_BLOCKER` | Blocker | Finding was marked as blocking by one or more action policies. The policy UUIDs are stored in `spec.actions.policy_uuids`. |
| `FINDING_TAGS_CI_WARNING` | Warning | Finding triggered a warning based on one or more action policies. The policy UUIDs are stored in `spec.actions.policy_uuids`. |
| `FINDING_TAGS_DIRECT` | Direct | Finding applies to a direct dependency. |
| `FINDING_TAGS_DISPUTED` | Disputed | The CVE reported in this finding has been marked as ‘disputed’. |
| `FINDING_TAGS_EXCEPTION` | Exception | Finding was marked as exempt from action policies by one or more exception policies. The policy UUIDs are stored in `spec.exceptions.policy_uuids`. |
| `FINDING_TAGS_EXPLOITED` | Exploited | The CVE reported in this finding is actively exploited and is listed in the Known Exploited Vulnerabilities (KEV) database. |
| `FINDING_TAGS_FIX_AVAILABLE` | Fix Available | There is a fix available for the CVE reported in this finding. |
| `FINDING_TAGS_INVALID_SECRET` | Invalid Secret | Finding applies to an invalid secret. |
| `FINDING_TAGS_MALWARE` | Malware | Finding applies to a malicious package. |
| `FINDING_TAGS_NAMESPACE_INTERNAL` | First Party | Finding applies to a dependency that belongs to the same namespace. |
| `FINDING_TAGS_NORMAL` | Normal | Finding applies to a normal, non-test, dependency. |
| `FINDING_TAGS_NOTIFICATION` | Notification | Finding triggered a notification based on one or more action policies. The policy UUIDs are stored in `spec.actions.policy_uuids`. |
| `FINDING_TAGS_PATH_EXTERNAL` | External Path Only | Finding applies to a transitive dependency that can only be reached through external, non-OSS, project paths. |
| `FINDING_TAGS_PHANTOM` | Phantom | Finding applies to a phantom dependency. |
| `FINDING_TAGS_POLICY` | Policy Based | Finding was generated by a Rego based finding policy. The policy UUID is stored in `spec.finding_metadata.source_policy_info.uuid`. |
| `FINDING_TAGS_POTENTIALLY_REACHABLE_DEPENDENCY` | Potentially Reachable Dependency | Finding applies to a potentially reachable dependency. |
| `FINDING_TAGS_POTENTIALLY_REACHABLE_FUNCTION` | Potentially Reachable Function | Finding applies to a potentially reachable function. |
| `FINDING_TAGS_PROJECT_INTERNAL` | Same Repository | Finding applies to a dependency that belongs to the same project. |
| `FINDING_TAGS_REACHABLE_DEPENDENCY` | Reachable Dependency | Finding applies to a reachable dependency. |
| `FINDING_TAGS_REACHABLE_FUNCTION` | Reachable Function | Finding applies to a reachable function. |
| `FINDING_TAGS_SELF` | Self | Finding applies only to the analyzed package version, there is no dependency involved. |
| `FINDING_TAGS_TEST` | Test | Finding applies to a dependency that is not in production code. |
| `FINDING_TAGS_TRANSITIVE` | Transitive | Finding applies to a transitive (indirect) dependency. |
| `FINDING_TAGS_UNDER_REVIEW` | Under Review | Finding applies to suspicious package under review. |
| `FINDING_TAGS_UNFIXABLE` | Unfixable | There is no fix available for the CVE reported in this finding. |
| `FINDING_TAGS_UNREACHABLE_DEPENDENCY` | Unreachable Dependency | Finding applies to an unreachable dependency. |
| `FINDING_TAGS_UNREACHABLE_FUNCTION` | Unreachable Function | Finding applies to an unreachable function. |
| `FINDING_TAGS_VALID_SECRET` | Valid Secret | Finding applies to a valid secret. |
| `FINDING_TAGS_WITHDRAWN` | Withdrawn | The CVE reported in this finding has been marked as ‘withdrawn’. |

### Exceptions

A finding can be exempt from triggering action policies (such as admission and notification policies)
if it is matched and marked as dismissed by an exception policy.

[Exception policies](../../../../managing-policies/exception-policies/) allow you to set any criteria
you want to mark findings as dismissed. You can apply an exception policy across all projects, a sub-set of projects,
or a specific project, within a tenant.
Based on the criteria you set, the exception can persist across multiple package versions.

Findings dismissed by one or more exception policies have the `spec.dismissed` field set to `true` and
the corresponding policy object UUIDs are listed under the `spec.exceptions.policy_uuids` field.
They also carry the `FINDING_TAGS_EXCEPTION` tag.

### Action policies

Findings matched by one or more action policies (a.k.a. admission and notification policies)
contain the corresponding policy object UUIDs in `spec.actions.policy_uuids`.
They also carry a tag corresponding to the specific action, for example, `FINDING_TAGS_CI_WARNING`,
`FINDING_TAGS_CI_BLOCKER`, or `FINDING_TAGS_NOTIFICATION`.

## ScanResult

* Contains details of a scan such as:
  + Configuration
  + Host environment details
  + Runtime statistics
  + Findings
  + Policies triggered
  + Error logs
  + [Exit code](../../../../troubleshooting/endorctl-exitcodes/)
  + [Scan status](#scan-status)
* Has the Project as the parent.
* Belongs to the same [Context](../common-fields/#context) as the scan.

For more information, see the [ScanResultService REST API documentation](https://docs.endorlabs.com/api/#tag/ScanResultService).

### Scan status

The following scan statuses are supported:

| Status | Description |
| --- | --- |
| `STATUS_SUCCESS` | Scan completed successfully. |
| `STATUS_PARTIAL_SUCCESS` | Scan completed, but with critical warnings or errors. See `spec.logs` for more information. |
| `STATUS_FAILURE` | Scan failed. See `spec.exit_code` and the [exit code documentation](../../../../troubleshooting/endorctl-exitcodes/) for more information. |
| `STATUS_RUNNING` | Scan is running. |

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
