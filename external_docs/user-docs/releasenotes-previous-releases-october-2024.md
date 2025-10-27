---
url: https://docs.endorlabs.com/releasenotes/previous-releases/october-2024/
title: October 2024 | Endor Labs Docs
downloaded: 2025-10-27 13:00:39
---

October 2024 | Endor Labs Docs



* Type to search...
* ---

[Print entire section](/releasenotes/previous-releases/october-2024/_print.html)



# October 2024

We are excited to introduce the latest features and enhancements in Endor Labs.

### Find and evaluate AI models New

You can now view AI models from Hugging Face on the Endor Labs platform. Search for AI models and review their Endor scores, including security, activity, popularity, and quality. These scores help you make informed decisions before integrating models into your organization. See [Discover AI models](../../../ai/ai-model/) for more information.

![AI model list](../../../images/llm-detail.png)

### Scan Java projects without pom.xml New

You can now scan Java projects that do not have a `pom.xml` file. This feature enables Endor Labs to scan a non-Maven and non-Gradle Java artifact, and provide the list of unresolved dependencies, resolved dependencies, and dependency tree. You can set the environment variables `ENDOR_JVM_USE_ARTIFACT_SCAN`,`ENDOR_JVM_USE_ARTIFACT_SCAN_CLASSPATH`, and `ENDOR_JVM_FIRST_PARTY_PACKAGE` to facilitate the scan of projects that contain such artifacts. See [Scan projects without pom.xml](../../../scan-with-endorlabs/language-scanning/java/#scan-projects-without-pomxml-beta) for more information.

### Export multiple package versions in SBOM New

You can now export multiple package versions in an SBOM through endorctl with the new command options `--package-version-uuids`, `--project-uuid`, and `--project-name`. This feature allows aggregating multiple package versions across one or many projects in a single SBOM file. See [Export multiple package versions in SBOM](../../../managing-sboms/exporting-sboms/#Export-SBOM-through-endorctl) for more information.

### Enhanced user interface to view findings of a project Enhancement

Endor Labs has a new user interface to view findings of a project.

* **Findings list**: The new findings come in a tabular format with columns that include location, EPSS, tags, and more.
* **Preset filters**: Preset filters help you to look for the category of findings you care about the most. For example, Prioritized Findings gives the list of critical vulnerability findings in the last 30 days that have either a reachable function or a reachable dependency, are not test dependencies, and have an available fix.
* **Detailed drawers**: This side panel drawer provides detailed metadata inside the drawer that includes risk details, fix info, and call graphs when available.

The new updates are designed to enhance your experience by providing:

* **Modern look and feel**: A refreshed, modern design that’s cleaner and more intuitive.
* **Enhanced navigation bar**: Streamlined menus to help you find what you need faster.
* **Improved performance**: Faster load times and smoother transitions for a more efficient workflow with default filters pre-loaded.

See [View findings associated with a project](../../../managing-projects/view-findings/) for more information.

![Project Findings](../../../images/ProjectFindings.png)

### Manage build tools Enhancement

The following enhancements are now available for specifying project build toolchains:

* **Auto detection of build tools** - You can enable auto detection of build tools for their projects based on the manifest files present in the repository. Auto detection is supported for Long Term Support (LTS) versions of Java, Python, Go, and .NET (C#) projects. See [Enable auto detection](../../../scan-with-endorlabs/manage-scan-profiles/auto-detect-toolchains/) for more information.
* **Specify toolchains with scanprofile.yaml** - You must now specify build toolchains in the `scanprofile.yaml` file, a multi-document yaml file with a structure similar to Kubernetes configuration files. Previously, build toolchains were defined in the `profile.yaml` file. See [Build tools](../../../scan-with-endorlabs/manage-scan-profiles/build-tools/) for more information.

### Jira integration Enhancement

When integrating Jira with Endor Labs, you can:

* Specify an issue type from the custom Jira project such as Bug, Task, Epic, Story, or any other value when raising a Jira ticket. This enables efficient categorization and tracking of issues within the project.
* Configure the integration to define custom fields with appropriate values, that align with your organization’s workflows. For instance, you can create key-value pairs like `Source = Endor Labs` to associate specific information with each Jira ticket raised from Endor Labs.

#### Note

Make sure the endorctl version is v1.6.547 to use **ISSUE TYPE** and v1.6.567 or higher to use **Custom Fields**.

See [Set up Jira integration with Endor Labs](../../../integrations/jira-integration/) for more information.

### Support for Bazel with Gazelle in vendored mode in Go projects Enhancement

Endor Labs now supports scanning Go projects that use Bazel with Gazelle in vendored mode. See [Scan Go projects using Bazel with Gazelle in vendored mode](../../../scan-with-endorlabs/language-scanning/golang/#run-a-scan)

### Kotlin 2.0 Support Enhancement

Endor Labs has extended Kotlin support to include version 2.0. With this enhancement, Endor Labs supports Kotlin projects from version 1.4 to 2.0.

### Other enhancements Enhancement

* **Archived repositories** - The Endor Labs GitHub App no longer scans archived repositories by default. To include archived repositories in the scan, you can adjust the preferences during the GitHub App installation or by editing the integration settings afterward.
* **Name change from SCPM to RSPM** - Endor Labs now uses RSPM (Repository Security Posture Management) as the standard terminology for all SCPM (Source Code Posture Management) policies and findings across the user interface and documentation. Previously, both RSPM and SCPM were used interchangeably.
* **Removal of Dismiss Findings** - You can no longer dismiss a finding from the Findings page on the Endor Labs user interface. Instead, you can apply an exception policy if you want the finding to not trigger any action policy. See [Apply exception to findings](../../../managing-projects/view-findings/#apply-exception-to-findings).

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
