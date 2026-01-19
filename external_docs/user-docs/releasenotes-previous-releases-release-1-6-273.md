---
url: https://docs.endorlabs.com/releasenotes/previous-releases/release-1-6-273/
title: May 2024 | Endor Labs Docs
downloaded: 2026-01-16 09:51:27
---

May 2024 | Endor Labs Docs



* Type to search...

[Print entire section](/releasenotes/previous-releases/release-1-6-273/_print.html)



# May 2024

We are excited to introduce you to the latest version of Endor Labs and endorctl - v1.6.273. This release includes new features and enhancements.

## New Features

### Detect GitHub Actions (Beta)

Endor Labs provides comprehensive visibility into GitHub Action workflows used in your code repositories and helps you to:

* Assess the authenticity and reliability of the dependencies in your CI environment. This enables you to determine potential exposure to known or headline incidents.
* Ensures that the code in your CI workflows does not change without your knowledge. This reduces breaking changes and helps you manage your supply chain risks.
* Detect and identify if any vulnerable or malicious software is part of your CI environment.
  For more information, see [View GitHub Action findings](../../../managing-projects/view-findings/).

![View GitHub Action findings](../../../images/githubactions.png)

To detect and view GitHub Action findings, run the endorctl scan with the `--ghactions` flag.
For more information, see [endorctl scan command](../../../endorctl/commands/scan/).

## Enhancements

### Dashboard widgets

Endor Labs introduces new widgets on the Dashboard to help you track the development hours and the cost metrics of your organization.

* The newly introduced **Vulnerability Prioritization Funnel** systematically assesses and categorizes vulnerabilities based on their severity and category. By applying this funnel approach, organizations can prioritize addressing the most critical, exploitable, and actionable vulnerabilities first, maximizing their security efforts.
* Visualize **Dev Hours Saved** and **Cost Saved** metrics on the dashboard to make more informed decisions, optimize resource allocation, and better manage project budgets.

![Dashboard](../../../images/dashboard.png)
For more information, see [View Dashboards](../../../dashboards/oss-overview/).

### Support for .NET Prop files (Beta)

Endor Labs now provides the support to scan the following .NET Prop files.

* Package references in `Directory.Build.props` or `Directory.Packages.props` files.
* Package references in any `*.props` file and the prop file is imported in the `*.csproj` file.
* Package references in `*.Targets` file

For more information, see [Scan .NET projects](../../../scan-with-endorlabs/language-scanning/dotnet/)

### npm for Windows operating systems

You can now use npm to install endorctl on Windows operating systems.

For more information, see [Install endorctl with npm](../../../endorctl/install-and-configure/)

### Finding policies for Repository Security Posture Management

The following new out-of-the-box finding policies are included in the application for repository security posture management (RSPM).

| Policy | Severity |
| --- | --- |
| Restrict the use of runner groups for public repositories | High |
| Restrict runner groups to specific repositories | Medium |
| Restrict the use of runner groups for public repositories | High |
| Script injection detected in GitHub workflow files | High |
| Organization webhooks must be configured with a secret | Medium |
| Repository webhooks must be configured with a secret | Medium |
| Default workflow token permission should be read only | High |
| Restrict general action permissions to organization members | High |
| Default member permissions should be restricted | Medium |

For more information, see [RSPM Policies](../../../managing-policies/finding-policies/managing-scm-configuration/).

### endorctl commands

Note the updates to the following flags used with the endorctl scan.

| Flag | Environment variable | Description | Usage |
| --- | --- | --- | --- |
| `--dependencies` | `ENDOR_SCAN_DEPENDENCIES` | Scan commits and generate findings for all dependencies. | Using this flag will generate findings for dependencies only. Previously it was generating findings for tools and dependencies. To fetch findings for both tools and dependencies, run the endorctl scan with `--tools` and `--dependencies`. |
| `--github` | `ENDOR_SCAN_GITHUB` | Scans GitHub repositories and generates findings for GitHub misconfigurations. | Using this flag will generate findings for misconfigurations only. Previously it was generating findings for misconfigurations, tools, and dependencies. |
| `--tools` | `ENDOR_SCAN_TOOLS` | Scans repositories and generates findings for CI/CD tools used in the source code repository. | Using this flag will generate findings for CI/CD tools only. Use it with `--github` to include GitHub app. It requires a valid GitHub token with `read:org access`. |
| `--pr-incremental` | `ENDOR_SCAN_PR_INCREMENTAL` | Scan packages with dependencies that have changed compared to the baseline scan | Use it with `--pr-baseline` or `--enable-pr-comments` to perform an incremental scan by ignoring any packages that have the same dependencies as the baseline. |

For more information, see [endorctl scan command](../../../endorctl/commands/scan/).

### Dependency reachability

Note the following updates when you perform a deep scan for the following languages:

* Python - The dependencies that are used in source code but not declared in the package’s manifest files are detected by default when you perform a deep scan on Python projects.
* JavaScript/TypeScript - You must include the flag `--call-graph-languages` with value `javascript,typescript` to detect dependencies that are used in the source code but not declared in the JavaScript or TypeScript package’s manifest files.

The flag `--phantom-dependencies` and its corresponding environment variable `ENDOR_SCAN_PHANTOM_DEPS` is deprecated from this release.

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
