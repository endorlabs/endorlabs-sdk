---
url: https://docs.endorlabs.com/releasenotes/
title: Release notes | Endor Labs Docs
downloaded: 2025-10-23 23:28:39
---

Release notes | Endor Labs Docs



* Type to search...
* ---

# Release notes

Endor Labs helps you select, secure, and maintain dependencies, so development moves fast and supply chain risk remains low. The following release notes highlight the most recent major capabilities and any major bug fixes published by Endor Labs.

[October 2025](/releasenotes/october-2025/)

We are excited to introduce the latest features and enhancements in Endor Labs.

### Discontinuation of CI/CD tool scan Breaking Change

CI/CD tool scanning has been discontinued and is no longer available. This change does not affect the scanning of GitHub Action dependencies.

### Endor AI chat New

Endor Labs now includes **Endor AI Chat**, an AI-powered assistant designed to help you understand vulnerabilities and take quicker, more informed action. You can ask natural language questions about security findings, scan results, package versions, and vulnerabilities. See [Endor AI chat](../../ai/ai-chat/).

### Pre-computed reachability analysis New

Endor Labs now supports pre-computed reachability analysis to determine vulnerability exposure in dependencies without requiring code compilation or full call graph generation. You can enable it using the pre-computed flag for quick scans and full scans.

For more information, see [Pre-computed reachability analysis](../../introduction/reachability-analysis/pre-computed-reachability/).

### Search for authorization policies Enhancement

You can now search for authorization policies using rule criteria, creator email addresses, and namespace assignments.

For more information, see [Search authorization policies](../../administration/access-endorlabs/authorization-policies/#search-authorization-policies).

### Filter notifications using project name Enhancement

You can now filter notifications by project name to focus on notifications from specific projects and reduce noise from others.

For more information, see [Notifications](../../getting-started/endor-labs-ui/#notifications).

[September 2025](/releasenotes/september-2025/)

We are excited to introduce the latest features and enhancements in Endor Labs.

### Discontinuation of CI/CD tool scanning Breaking change

CI/CD tool scanning functionality is being deprecated and will be discontinued by the end of September 2025. This change does not affect the scanning of GitHub Action dependencies.

### Dedicated commands for container scans New

You can now use the dedicated command `endorctl container scan` for container scanning. This replaces the older `endorctl scan --container` command. Migrate to `endorctl container scan` to ensure continued compatibility. For more information, see [Use new container scan commands](../../scan-with-endorlabs/scan-containers/container-migration/).

#### Deprecation notice

The old `endorctl scan --container` commands and their corresponding flags (`--container`, `--container-tar`, and `--container-as-ref`) will be removed after a three-month deprecation period.

### Opengrep support for SAST and AI model detection New

Endor Labs now uses [Opengrep](https://www.opengrep.dev/) to scan your code for SAST and AI model findings instead of Semgrep. Opengrep is an open-source, static analysis tool that finds bugs and vulnerabilities in the source code using pattern matching. Endor Labs automatically downloads Opengrep for you when you run a scan that needs it.

You can continue using Semgrep with Endor Labs if you prefer. See [Use Semgrep with Endor Labs](../../administration/use-semgrep-with-endorlabs/) for more information.

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

For more information, see [Export findings to GitHub Advanced Security](../../deployment/monitoring-scans/github-app/github-app-pro/export-findings-to-ghas/#filter-findings-exported-to-github).

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

[August 2025](/releasenotes/august-2025/)

We are excited to introduce the latest features and enhancements in Endor Labs.

### Discontinuation of CI/CD tool scanning Breaking change

CI/CD tool scanning functionality is being deprecated and will be discontinued by September 15, 2025. This change does not affect the scanning of GitHub Action dependencies.

### AI security review New

AI security review provides automated code review capabilities using artificial intelligence to identify potential security issues in your code base. You can set up AI security review to review pull requests and raise findings for security issues.

For more information, see [AI security review](../../ai/ai-security-review/).

### First-party code dashboard New

The first-party code dashboard provides a comprehensive view of the vulnerabilities in your codebase from a SAST and secrets perspective.

For more information, see [First-party code dashboard](../../dashboards/first-party-code/).

### Container end of life dependency finding policy New

You can now enable the **End of Life Container Dependencies** finding policy to raise findings for OS-level packages and components in container images that have reached end of life.

For more information, see [Container finding policies](../../managing-policies/finding-policies/container-policies/).

### Malware policies New

Endor Labs now offers improved malware detection with detailed malware reasoning, broader coverage, and timely warnings before malicious packages disappear from registries. You can use the following new malware focused policies:

* **Malware finding policy**: Enable OSS finding policy to identify known malicious code or suspicious patterns in dependencies and raise findings for them.
* **Malware action policy**: Create an action policy from the malware template to define how to handle malware findings.
* **Malware exception policy**: Create an exception policy to apply exceptions to malware findings under defined conditions and exclude them from action policies.

For more information, see [OSS finding policy](../../managing-policies/finding-policies/oss-policies/), [Malware action policy](../../managing-policies/action-policies/templates/#malware), and [Malware exception policy](../../managing-policies/exception-policies/templates/#malware).

### Export SBOM in SPDX format New

You can now export Software Bill of Materials in the industry standard SPDX format, with support for both `json` and `tag-value` output formats, making it easier to integrate SBOMs into existing compliance, auditing, and security workflows.

For more information see [Export SBOM in Endor Labs](../../managing-sboms/exporting-sboms/#export-an-sbom-as-spdx).

### Support for pull request scans in GHAS SARIF exporter Enhancement

The GHAS SARIF exporter now supports pull request scans for GitHub App (Pro). If you have enabled pull request scans in your GitHub App, the GHAS SARIF exporter exports the findings for each pull request. You can view the findings for the pull request in GitHub Advanced Security.

For more information, see [Export findings to GitHub Advanced Security](../../deployment/monitoring-scans/github-app/github-app-pro/export-findings-to-ghas/).

### Azure OpenAI model detection Enhancement

Endor Labs extends AI model detection to include Azure OpenAI, surfacing detected models as dependencies during scans. Azure OpenAI models are detected but not scored, as provider metadata is limited.

For more information, see [AI model detection](../../ai/ai-llm/#ai-model-detection).

### Scan container image tarball Enhancement

You can now scan container images saved as tarball files using `endorctl`. This helps you analyze dependencies, generate SBOM details, and review security findings for container images that are not directly accessible from a registry.

For more information, see [Scan container image tarball](../../scan-with-endorlabs/scan-containers/#scan-container-image-tarball).

### Search for malware in Vulnerability Database Enhancement

You can now use the MAL identifier to search for known malware in the Endor Labs vulnerability database and quickly identify malicious packages alongside existing vulnerabilities.

For more information, see [Endor Labs vulnerability database](../../discover/vulnerability-db/).

[July 2025](/releasenotes/july-2025/)

We are excited to introduce the latest features and enhancements in Endor Labs.

### Support for CVSS v4.0 scores New

Endor Labs now supports CVSS v4.0, as an enhanced standard for vulnerability severity assessment.

CVSS v4.x scores, including full vector strings and metadata are available in Endor Lab’s reporting and data exports. Note that Vanta exports continue to support only CVSS v3.x.

By default, Endor Labs uses **CVSS v3.x**. You must explicitly configure the system to use **CVSS v4.x.**

For more information, see [Configure CVSS score version](../../administration/configure-system-settings/)

### Endor Labs Vulnerability Database New

Endor Labs now includes a comprehensive vulnerability database to search and analyze known issues across software dependencies using CVE, GHSA, and PySEC identifiers. It maps vulnerable package versions to impacted projects and findings to support easier remediation.

For more information, see [Endor Labs vulnerability database](../../discover/vulnerability-db/).

### SARIF export to GitHub Advanced Security New

Endor Labs now supports exporting findings to GitHub Advanced Security as SARIF files. You can use GitHub Advanced Security to analyze and triage findings from Endor Labs.

For more information, see [Export findings to GitHub Advanced Security](../../deployment/monitoring-scans/github-app/github-app-pro/export-findings-to-ghas/).

### Discover AI models Enhancement

Endor Labs extends AI model detection to include external providers, listing detected models as dependencies. Hugging Face models are scored, as they are open source and provide extensive public metadata. Models from other providers are detected but not scored due to limited data.

For more information, see [AI model detection](../../ai/ai-llm/#ai-model-detection).

### C/C++ scan improvements Enhancement

**Effective Monday, July 21, 2025**, Endor Labs is releasing new updates to the code segment analyzer and the underlying database of hashes and embeddings used in C/C++ Software Composition Analysis. If you use continuous integration workflows or perform local scans, you must update to the latest version of `endorctl` and re-run your scan with:

```
endorctl scan --languages=c
```

The first scan may take longer than usual, as it rebuilds the cache of code segments. You may also see differences in the results compared to previous scans. These changes improve the accuracy of dependency detection and matching.

[June 2025](/releasenotes/june-2025/)

We are excited to introduce the latest features and enhancements in Endor Labs.

### Endor Labs MCP server for IDE Alpha New

Endor Labs MCP server is now available in alpha for Cursor and Visual Studio Code.

The Endor Labs MCP server integrates directly into your IDE to scan code in real-time, and catch security issues before they reach production. This workflow secures both human and AI-generated code from the moment it’s written. For more information, see [Endor Labs MCP Server](../../deployment/ide/mcp/).

### Grant support access to your tenant New

You can now grant the Endor Labs support team read-only access to your tenant for a limited time. This feature enables our support team to assist you more efficiently while ensuring your data remains secure and private.

For more information, see [Grant support access](../../administration/access-endorlabs/authorization-policies/#grant-support-access).

### Finding policies for AI models Enhancement

You can now configure two new finding policies and manage the use of AI models more effectively in your organization.

* **Restricted AI models**: Raise a finding when a repository uses an AI model that your organization has marked as restricted or allowed only in specific contexts.
* **Restricted AI model providers**: Raise a finding when a repository uses an AI model from a provider that is restricted based on your organization’s policy.

For more information, see [Detect AI models](../../ai/ai-llm/#detect-ai-models).

### Manually upgrade finding policies Enhancement

You can now upgrade a finding policy when a new version is available. Policy upgrades may include changes such as updated Rego code, new fields, parameters, or tags. After upgrading, you cannot revert the policy to its previous version.

For more information, see [Upgrade a finding policy](../../managing-policies/#upgrade-a-finding-policy).

### Resolving package names from prop files Enhancement

endorctl now evaluates MSBuild properties from files like `Directory.Build.props`, enabling resolution of package names and versions defined using variables.

For more information, see [Resolving package names from props files](../../scan-with-endorlabs/language-scanning/dotnet/#resolving-package-names-from-props-files).

### Group findings by dependency Enhancement

Findings in the **SCA**, **Vulnerability**, and **Container** categories are now grouped by **Dependency** by default, making it easier to review your scans.

For more information, see [View findings](../../managing-projects/view-findings/).

### AI model discovery in Endor Labs monitoring scans Enhancement

Endor Labs now automatically detects AI models during SCA scans when using the GitHub App, Bitbucket App, Azure DevOps App, and GitLab App. You can view AI models from the **AI Inventory**.

For more information, see [View AI model findings using Endor Labs GitHub App](../../ai/ai-llm/#view-AI-model-findings-through-monitoring-scans).

### Components field support for Jira tickets Enhancement

You can now configure the Jira integration in Endor Labs to automatically populate the **Components** field in Jira tickets for both company-managed and team-managed Jira projects.

For more information, see [Integrate Jira with Endor Labs](../../integrations/jira-integration/#configure-jira-integration-on-endor-labs).

### Exclude all child namespaces Enhancement

By default, the Endor Labs dashboard includes data from all child namespaces. Use the **All child namespaces excluded** toggle to exclude child namespaces and view data and metrics for only the selected namespace.

For more information, see [Namespaces in Endor Labs](../../administration/namespaces/#namespaces-in-an-organization).

[May 2025](/releasenotes/may-2025/)

We are excited to introduce the latest features and enhancements in Endor Labs.

### Outpost: On-premise scheduler for monitoring scans Beta New

Outpost is a new on-premise scheduler for monitoring scans that you can run in your own Kubernetes cluster. When you install and configure Outpost, monitoring scans on your source code repositories are scheduled and run on your own Kubernetes cluster inside your firewall. For more information, see [Outpost](../../deployment/monitoring-scans/outpost/).

### Authenticate Jira Data Center with Endor Labs Enhancement

You can now use **Personal Access Token (PAT)** to authenticate your Jira Data Center to Endor Labs.

For more information, see [Configure Jira integration.](../../integrations/jira-integration/#configure-jira-integration-on-endor-labs)

### Pipenv support for Python projects Enhancement

Endor Labs now offers support for scanning Python projects that use Pipenv as their package manager by resolving dependencies from `Pipfile` and `Pipfile.lock`. For more information, see [Scan Python projects](../../scan-with-endorlabs/language-scanning/python/).

### View AI usage in the application Enhancement

You can now view which features in the Endor Labs application use AI services. To modify AI access settings, go to **Settings** > **AI Access** and contact support to customize access based on your organization’s needs. For more information, see [AI access](../../ai/ai-access/).

### Projects page user interface improvements Enhancement

The **Projects** page now includes enhancements that make it easier to explore, sort, and filter package data.

* The following new columns help you assess the overall health of your project.
  + **Dependency Resolution Status** - Shows the percentage of packages for which dependency resolution was successful.
  + **Reachability Analysis Status** - Shows the percentage of packages for which reachability analysis was successful.
* Click any column header to sort projects in ascending or descending order. For more information, see [Manage projects](../../managing-projects/).
* From **Inventory** > **Packages**, you can now filter packages by Dependency Resolution or Reachability Analysis statuses to focus on relevant results.
* Sort packages by **Package** name, **Created** date, and **Last Scanned** date to quickly locate changes or specific dependencies. For more information, see [Packages](../../managing-projects/packages/#filter-package-dependencies).

### Discontinue reachability analysis for Rust Breaking change

Reachability analysis is no longer supported for Rust projects. However, you can continue to scan Rust projects for software composition analysis and vulnerability detection.

### View findings location in Jira tickets Enhancement

You can now view the location of the findings identified by Endor Labs in your Jira tickets. For more information, see [Findings in Jira.](../../best-practices/jira-with-endor-labs/#track-findings-in-jira)

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
