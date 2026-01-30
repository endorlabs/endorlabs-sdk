---
url: https://docs.endorlabs.com/releasenotes/previous-releases/release-1-6-448/
title: August 2024 | Endor Labs Docs
downloaded: 2026-01-26 10:09:36
---

August 2024 | Endor Labs Docs



* Type to search...

[Print entire section](/releasenotes/previous-releases/release-1-6-448/_print.html)



# August 2024

We are excited to introduce you to the latest version of Endor Labs and endorctl - v1.6.448. This release includes new features and enhancements.

### Upgrades and recommendations (Beta) New

Endor Labs upgrade and remediation workflows provide an end-to-end solution to help you discover, prioritize, manage, and resolve risks in your software development environment.

* **Upgrade Impact Analysis**: Endor Labs identifies and recommends upgrades for your dependencies. By pinpointing the distinct actions that can resolve your vulnerabilities and mitigate the risks associated with updates, your security program can make more informed risk management decisions and triage issues more effectively.
* **Endor Patches**: Endor Labs backports security fixes to your packages, allowing you to minimize the impact of software updates. By using an Endor patch, you can update the libraries with a minimal viable security patch that reduces your risk of breaking changes, bugs, or performance issues associated with an upgrade.

For more information, see [Upgrades and remediation](../../../upgrades-and-remediation/).

### Manage build tools (Beta) New

Endor Labs provides you with the following options to define tools necessary for building your software while performing endorctl scans:

* Specify toolchain configuration through endorctl API.
* Specify toolchain configuration through profile.yaml file.
* Falls back to the system default values for your toolchain specifications.

Endor Labs will automatically install build tools in a sandbox to ensure you can run highly accurate scans. Build tools are not installed on your host. For more information, see [Manage build tools](../../../scan-with-endorlabs/manage-scan-profiles/build-tools/).

### Support for Azure pipelines and Azure Advanced Security New

You can integrate endorctl inside an Azure pipeline and view the scan results in Azure Advanced Security.

When you integrate endorctl in the Azure pipeline, endorctl scan runs and generates SARIF files during the pipeline run. The SARIF file is consumed by Advanced Security in your Azure repository. By configuring this integration, you can use Endor Labs seamlessly within the Azure ecosystem to enhance security and streamline workflows. For more information, see [Scan with Azure Pipelines](../../../deployment/ci-scans/scan-with-azuredevops/).

### Changes to endorctl CLI options Enhancement

Endor Labs is introducing two new endorctl CLI options `--include-path` and `--exclude-path` to replace the existing `include` and `exclude` options.

* Using these new options, you can specify the file paths or patterns to exclude or include from the endorctl scan using Glob style expressions which are easier to use.
* You can easily scope your scans by defining inclusion or exclusion patterns. See [scoping scans](../../../best-practices/scoping-scans/) for more details.

The existing `--include` and `--exclude` options are deprecated. However, if these options are already in use, such as in a script, the updates remain backwards compatible, ensuring continued functionality.

### Changes to the default view on the Findings page Enhancement

By default, Endor Labs now displays findings that meet the following criteria in the Findings page:

* Critical severity vulnerabilities
* Reachable vulnerabilities
* Vulnerabilities with EPSS probability above 1%
* Security vulnerabilities
* Vulnerabilities created in the last week

Previously, the Findings page displayed all findings when you opened the Findings page.

You can use the basic or advanced filters to view additional findings. For more information, see [View Findings](../../../managing-projects/view-findings/).

### Container action policy templates Enhancement

Endor Labs now provides action policy templates that you can use to quickly create action policies specific to container scanning. For more information, see [Action policy templates](../../../managing-policies/action-policies/templates/).

### PDM package manager support for Python projects Enhancement

Endor Labs now offers support for scanning Python projects that use PDM as their package manager. For more information, see [Scan Python projects](../../../scan-with-endorlabs/language-scanning/python/).

### New fields to filter project dependencies Enhancement

You can filter project dependencies and export additional fields for project dependencies with the following new fields:

* License File
* License Matched Text
* License Name
* License Type
* License URL

### Sign up with GitHub Enhancement

You can now sign up to Endor Labs with your GitHub account.

### Quickstart with Endor Labs GitHub App Enhancement

Endor Labs GitHub App is now available as an option in quick start. The Endor Labs GitHub App allows you to quickly set up your GitHub repositories in Endor Labs and initiate scans. For more information, see [Quick start with GitHub App](../../../getting-started/quickstart/quickstart-github-app/).

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
