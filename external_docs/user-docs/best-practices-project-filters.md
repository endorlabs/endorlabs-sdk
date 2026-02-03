---
url: https://docs.endorlabs.com/best-practices/project-filters/
title: Best practices: Working with project filters | Endor Labs Docs
downloaded: 2026-02-03 00:50:13
---

Best practices: Working with project filters | Endor Labs Docs



* Type to search...

[Print entire section](/best-practices/project-filters/_print.html)



# Best practices: Working with project filters

Learn how to implement and use project filters to search, prioritize, and manage projects across your organization.

Filters enable targeted queries based on attributes such as severity, package ecosystems, dependency resolution, and platform source.

This guide explains how filters work, how to apply and combine them effectively, and provides practical examples to support triage, audit, and reporting workflows across large codebases.

## Access project filters

Perform the following steps to apply filters to the project list.

1. Select **Projects** from the left sidebar.
2. Click **Add Filter**.
3. Select from the list of available filters.
4. Enter appropriate values and click **Add Filter**.

You can combine multiple filters to create more specific searches and narrow down the project list based on multiple criteria.

## How filters work

Each filter consists of three parts.

* **Field**: The attribute to be filtered (for example, Package Count, Platform Source).
* **Operator**: The comparison logic (for example, equals, greater than, in).
* **Value**: The target value to evaluate (for example, `ECOSYSTEM_NPM`, `100`).

Project filters use standard comparison operators to evaluate criteria. See [Filter operators](../../rest-api/using-the-rest-api/filters/#operators) for detailed information about available operators and their usage.

When you apply multiple filters, the system combines them using logical AND operations across filters for different fields and logical OR operations across filters for the same field.

For example:

* **Filter 1**: `Package Count greater than 1`
* **Filter 2**: `Dependency Resolution Status greater than or equal to 0.5`
* **Filter 3**: `Package Ecosystems equals ECOSYSTEM_NPM`
* **Filter 4**: `Package Ecosystems equals ECOSYSTEM_GO`
* **Filter 5**: `Platform Source in PLATFORM_SOURCE_GITHUB`

![Multiple filters](../../images/multiple-filters.png)

This combination returns only projects that have more than one package, have a dependency resolution status of at least 50%, use npm or Go packages, and that are from GitHub.

## Filter implementation techniques

The following examples demonstrate how to apply filters effectively for common project scenarios.

### Filter projects by custom tags

Use custom tags to filter projects based on environment or predefined labels assigned during project initialization or scan configuration.

For example, to view only projects related to Hugging Face models, use the `Custom Tags matches huggingface` filter.

![filter by custom tags](../../images/filter-custom-tags.png)

### Filter projects by findings severity

Prioritize remediation efforts by filtering projects based on the number and severity of security findings. You can filter by Critical Priority Findings Count, High Priority Findings Count, Medium Priority Findings Count, Low Priority Findings Count, or Total Findings Count to target different priority levels.

For example, to identify critical priority projects requiring immediate attention, use the `Critical Findings Count greater than or equal to 100` filter.

![filter by severity](../../images/filter-finding-severity.png)

### Filter projects by package ecosystem

Use package ecosystem filters to segment projects by programming language or package management system for targeted security policies such as stricter vulnerability thresholds for JavaScript projects or specific license compliance checks for Java applications.

For example, to focus on PHP projects for a security assessment, use the `Package Ecosystems equals ECOSYSTEM_PACKAGIST` filter.

![filter by package ecosystem](../../images/filter-package-ecosystem.png)

### Filter projects by source platform

Use platform source filters to segment projects by their source platform and correlate findings with platform-native security tools like GitHub’s Dependabot alerts or GitLab’s vulnerability scanning.

For example, to identify projects analyzed from binary artifacts like container images or compiled binaries, use the `Platform Source equals PLATFORM_SOURCE_BINARY` filter.

![filter by source platform](../../images/filter-source-platform.png)

### Filter projects by dependency resolution quality

Use dependency resolution status to identify projects with resolution issues that impact security analysis accuracy.

For example, to find projects with poor dependency resolution that need investigation, use the `Dependency Resolution Status equals 0.5` filter.

**Note**

Only float values are supported for dependency resolution status filters such as 0.5 for 50%, 0.75 for 75%, or 1.0 for 100%.

![filter by resolution](../../images/filter-dependency-resolution-status.png)

### Filter projects by scan timestamp

Use last scanned filters to identify projects with stale security data that require fresh scans for current security posture.

For example, to identify projects scanned within the last 24 hours, use the `Last Scanned greater than now (-24h)` filter.

![filter by last scanned](../../images/filter-last-scanned.png)

### Filter projects by complexity

Identify projects based on their size and complexity, which may require different levels of security attention and resources.

For example, to focus on large projects with extensive dependency trees, use the `Package Count greater than or equal to 10` filter.

![filter by complexity](../../images/filter-complexity.png)

### Filter projects by reachability analysis status

Use reachability analysis status to identify projects based on the success rate of call graph generation and reachability analysis.

For example, to find projects with successful reachability analysis, use the `Reachability Analysis Status greater than or equal to 0.7` filter.

**Note**

Only float values are supported for reachability analysis status filters such as 0.5 for 50%, 0.75 for 75%, or 1.0 for 100%.

![filter by reachability status](../../images/filter-reachability-analysis-status.png)

### Filter projects by triage status

Review projects based on how findings have been handled by security teams to ensure proper triage and exception handling.

For example, to review projects with dismissed findings, use the `Dismissed Findings Count equals 1` filter.

![filter by triage status](../../images/filter-dismissed-findings.png)

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
