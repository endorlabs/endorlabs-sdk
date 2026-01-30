---
url: https://docs.endorlabs.com/releasenotes/september-2025/
title: September 2025 | Endor Labs Docs
downloaded: 2026-01-29 22:22:48
---

September 2025 | Endor Labs Docs



* Type to search...

[Print entire section](/releasenotes/september-2025/_print.html)



# September 2025

We are excited to introduce the latest features and enhancements in Endor Labs.

### Discontinuation of CI/CD tool scanning Breaking change

CI/CD tool scanning functionality is being deprecated and will be discontinued by the end of September 2025. This change does not affect the scanning of GitHub Action dependencies.

### Dedicated commands for container scans New

You can now use the dedicated command `endorctl container scan` for container scanning. This replaces the older `endorctl scan --container` command. Migrate to `endorctl container scan` to ensure continued compatibility. For more information, see [Use new container scan commands](../../scan-with-endorlabs/scan-containers/container-migration/).

**Deprecation notice**

The old `endorctl scan --container` commands and their corresponding flags (`--container`, `--container-tar`, and `--container-as-ref`) will be removed after a three-month deprecation period.

### Opengrep support for SAST and AI model detection New

Endor Labs now uses [Opengrep](https://www.opengrep.dev/) to scan your code for SAST and AI model findings instead of Semgrep. Opengrep is an open-source, static analysis tool that finds bugs and vulnerabilities in the source code using pattern matching. Endor Labs automatically downloads Opengrep for you when you run a scan that needs it.

### Customize project scans using scan workflow New

Endor Labs now supports Scan Workflow, which lets you define scan profiles as sequential steps within a single project scan. This gives you fine grained control over how scans run, allowing you to target different parts of your codebase more precisely.

You can configure a scan workflow and assign it to your project either using the [Endor Labs API](../../scan-with-endorlabs/manage-scan-profiles/configure-scan-workflow-through-api/) or through the [Endor Labs user interface](../../scan-with-endorlabs/manage-scan-profiles/configure-scanworkflow-through-ui/).

For more information see [Configure Scan Workflow in Endor Labs](../../scan-with-endorlabs/manage-scan-profiles/#scan-workflow).

### Upgrade Impact Analysis for JavaScript/TypeScript New

Endor Labs now supports Upgrade Impact Analysis (UIA) for JavaScript and TypeScript projects. UIA helps you understand the potential impact of upgrading dependencies by identifying breaking changes and dependency conflicts that may occur during upgrades.

For more information, see [Upgrade impact analysis](../../upgrades-and-remediation/upgrade-impact-analysis/) and [JavaScript/TypeScript scanning](../../scan-with-endorlabs/language-scanning/javascript/).

### Recently released dependencies (cooldown) New

Endor Labs now offers policies that reduce supply chain risks by detecting newly released open source dependencies within a configurable cooldown period and optionally blocking their adoption to prevent issues from unverified packages and malware.

* **Recently Released Dependencies finding policy**: Enable this finding policy to identify and raises findings for dependency versions that have been published within the defined cooldown period. Default cooldown period is 48 hours.
* **Recently Released Dependencies (Cooldown) action policy**: Create an action policy from the template to define how to handle these findings.

For more information, see [OSS finding policy](../../managing-policies/finding-policies/oss-policies/), and [Recently released dependencies action policy](../../managing-policies/action-policies/templates/#recently-released-dependencies-cooldown).

### Support for SAST scan on Windows Enhancement

With the use of Opengrep instead of Semgrep for SAST scan, you can now run SAST scans on Windows. For more information, see [SAST scan with Endor Labs](../../sast-scans-with-endorlabs/).

### SwiftPM support for Swift/Objective-C projects Enhancement

Endor Labs now supports scanning Swift projects that use the Swift Package Manager (SwiftPM) by resolving dependencies from the `Package.swift` file.

For more information, see [Scan Swift projects](../../scan-with-endorlabs/language-scanning/swift-objective-c/).

### Filter findings exported to GitHub Advanced Security Enhancement

Endor Labs now supports filtering findings exported to GitHub Advanced Security through action policies. Findings are exported only from projects covered by configured action policies.

For more information, see [Export findings to GitHub Advanced Security](../../scan-with-endorlabs/data-exporters/export-to-ghas/#filter-findings-exported-to-github).

### Top 10 secret rules by severity Enhancement

The First Party Code dashboard now features a stacked bar chart that displays the top 10 secret rules along with their corresponding findings. This enables you to identify high impact rules and prioritize remediation by severity.

For more information, see [First-party code](../../dashboards/first-party-code/).

### Enhanced SARIF output with vulnerability identifiers Enhancement

Endor Labs now includes vulnerability aliases in SARIF output for SCA findings. Aliases such as CVE IDs, GHSA IDs, and other OSV identifiers help you track multiple identifiers for the same vulnerability and improve integration with security tools and workflows.

### Filter projects to view OSS overview Enhancement

You can now use the search bar to filter projects by name to focus the OSS overview on specific projects. This helps organizations prioritize the most critical and exploitable vulnerabilities, enabling more targeted security efforts.

For more information, see [First-party code](../../dashboards/first-party-code/).

### Gradle package manager support Enhancement

Endor Labs now supports Gradle package manager integration. You can configure private package manager repositories for Gradle through the user interface to scan dependencies from custom repositories and enhance dependency resolution.

For more information, see [Gradle private package manager](../../integrations/package-manager/gradle-private-package-manager/).

### Filter findings using project name Enhancement

You can now filter findings by project name, allowing you to target the findings of a specific project, focus on them, and eliminate noise from other projects.

For more information, see [Search for findings using basic filters](../../managing-projects/view-findings/#search-for-findings-using-basic-filters).

### Clone scan profiles Enhancement

You can now clone scan profiles in your namespace. The cloned profile retains all parameters and custom settings, helping you set up new profiles faster and maintain consistent configurations across scans.

For more information, see [Clone scan profile](../../scan-with-endorlabs/manage-scan-profiles/configure-scanprofile-ui/#clone-scan-profile).

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
