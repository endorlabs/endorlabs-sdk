---
url: https://docs.endorlabs.com/releasenotes/previous-releases/archive/
title: Archive releases | Endor Labs Docs
downloaded: 2026-01-26 10:09:49
---

Archive releases | Endor Labs Docs



* Type to search...

[Print entire section](/releasenotes/previous-releases/archive/_print.html)



# Archive releases

## Release 1.5.251

## New Features

### Prioritize vulnerabilities with C# call graphs

Users can now use call graphs in the Endor Labs application to analyze the dependencies and relationships among various functions in .NET **C#** projects.

* Endor Labs generates the call graphs for your **C#** projects and identifies functions or methods with known vulnerabilities or potential security issues.
* Users can examine the call graph to identify the functions that directly or indirectly call the vulnerable functions by tracing the paths of execution.
* Users can prioritize the vulnerabilities based on their severity, threat levels, and application importance.

Call graphs assist users in comprehending the potential consequences and enable them to prioritize the resolution of vulnerabilities that are more likely to result in additional exploitation.

### View policy violations in PR comments

Users can view policy violations in their source code before committing the code to the repository during the automated pre-commit checks. The information is included as comments on the respective pull requests. Users can easily identify and take remedial measures early in the development life cycle.

Based on the actions configured in your action policy, the workflow is designed to either warn you or fail the build based on the severity of these policy violations.

### Configure webhooks

Integrate Endor Labs with webhooks to send Endor Labs notifications to webhooks and pass information to any third-party applications such as Slack, Microsoft Teams, and many more. Users can monitor the webhook channels to investigate and take remedial measures.
With a webhook integration, you can configure Endor Labs to send information to the webhook as an HTTP POST request as soon as a notification is generated. You can also modify the key format and value associated with the notification in the payload.

### Perform organization-wide supervisory scans

Use the Endor Labs [Jenkins pipeline](https://github.com/endorlabs/jenkins-org-scan) to scan all the repositories in your organization at once and view consolidated findings. This pipeline runs on your organization’s Jenkins infrastructure and enables administrators to run organization-level supervisory scans easily. It is designed to work in GitHub Cloud and GitHub enterprise server environments.

## Enhancements

### Detect malware packages

When software applications depend on malicious packages, the confidentiality, integrity, and availability of systems and data belonging to software development organizations or to application end-users is compromised.

Endor Labs now detects application dependencies that are known to be malicious, as reported by the Open Source Vulnerabilities (OSV). Use the newly introduced **Malware** category on the **Findings** page to filter and view malware findings. Users can prioritize, and take necessary remedial actions such as patching or replacing the affected packages.

### Configure private NuGet repositories

Endor Labs provides the support to integrate with private NuGet package repositories, in addition to scanning public C# projects and repositories. Users can configure this integration from **Manage** > **Integrations** > **NuGet**. Endor Labs will fetch the resources from the authenticated endpoints and perform the scan.

### Secrets enhancements

* **Scan for secrets in pre-commits** - Users can scan for secrets in the code before committing the code to the code repository during the automated pre-commit checks. This helps identify and remove sensitive information from the code files early in the development life cycle.
* **Secrets deduplication** - A single secret may exist at multiple places in your code or repository. Duplicate secrets increase the attack surface and the risk of unauthorized access. Managing duplicate secrets can be complex and error-prone. Endor Labs intelligently categorizes instances of identical secrets found within your application components and repositories and raises a single finding so that you can manage them efficiently.

## Release 1.5.194

## Enhancements

## Support for private Composer package repositories

In addition to scanning public PHP projects and repositories, Endor Labs provides the support to integrate with private Composer package repositories. Users can configure this integration from **Manage** > **Integrations** > **Packagist**. Endor Labs will fetch the resources from the authenticated endpoints and perform the scan.

## Release 1.5.171

We are excited to introduce you to the latest version of Endor Labs and endorctl - v 1.5.171. This release includes new features.

## New Features

## Support for scanning secrets in code

Endor Labs scans your code files and repositories for secrets such as API keys, registration tokens, client secrets, client IDs, access tokens, bearer tokens, refresh tokens, or registration tokens of several popular services such as GitHub, Git Lab, AWS, Dropbox, Adobe, Atlassian, Bitbucket, Coinbase, Databricks, and many more services.

Using [Endor Labs’ secrets scan](../../../secrets-leak-detection/), users can:

* View findings for secrets exposed in the code and take remedial actions based on their severity.
* Detect valid and active secrets in their code repositories and immediately secure them.
* Perform the endorctl scan to audit their codebase regularly for secrets and take necessary mitigation measures.

## Release 1.5.159

We are excited to introduce you to the latest version of Endor Labs and endorctl - v 1.5.159. This release includes new features and enhancements.

## New Features

## Support for PHP project scanning

Endor Labs further extends its language scanning capabilities by incorporating support for [PHP](../../../scan-with-endorlabs/language-scanning/php/). In addition to the current support for Java, JavaScript, Rust, Python, Go, Ruby, .NET C#, and Scala, users can now scan and monitor their PHP projects.

Endor Labs scans PHP projects and resolves dependencies by analyzing both composer.json and composer.lock files. Users can view finding policy violations and dependency graphs.

Using Endor Labs, users can gain significant insights into the structure and relationships of their PHP project’s dependencies, aiding in managing dependencies effectively, identifying potential issues, and ensuring a well-organized and maintainable codebase.

## Enhancements

## Support for Ruby private registry

In addition to scanning public Ruby projects and repositories, Endor Labs provides the support to integrate with private Ruby registries that are not available publicly. Users can configure this integration from **Manage** > **Integrations** > **RubyGems**. Endor Labs will fetch the resources from the authenticated endpoints and perform the scan.

## Release 1.5.131

We are excited to introduce you to the latest version of Endor Labs and endorctl - v 1.5.131. This release includes new features.

## New Features

## Support for Scala language scan

Endor Labs further extends its language scanning capabilities by incorporating support for [Scala](../../../scan-with-endorlabs/language-scanning/scala/) projects. In addition to the current support for Java, JavaScript, Rust, Python, Go, Ruby, and .NET C#, users can now scan and monitor their Scala projects managed by sbt.

Endor Labs scans Scala projects by executing sbt plugins and inspecting the build.sbt file to retrieve information about direct and transitive dependencies.

Using Endor Labs, users can gain significant insights into the structure and relationships of their Scala project’s dependencies, aiding in managing dependencies effectively, identifying potential issues, and ensuring a well-organized and maintainable codebase.

## Release 1.5.117

We are excited to introduce you to the latest version of Endor Labs and endorctl - v 1.5.117. This release includes new features and enhancements.

## New Features

## Support for .NET scan

Endor Labs further extends its language scanning capabilities by incorporating support for the [.NET C# framework](../../../scan-with-endorlabs/language-scanning/dotnet/). In addition to the current support for Java, JavaScript, Rust, Python, Go, and Ruby, users can now scan and monitor their .NET **C#** projects and repositories.

Endor Labs leverages the packages.lock.json file to monitor the packages for dependencies and discovers unresolved, resolved, direct, and transitive dependencies. Users will also be able to view finding policy violations and dependency graphs.

Organizations can maintain secure .NET development and runtime environments while designing, coding, debugging, testing, and deploying complex C# projects and applications.

## Endor Labs extension for Visual Studio Code

Developers can now use Endor Labs directly from their Visual Studio Code’s Integrated Development Environment (IDE). The [Endor Labs extension](../../../deployment/ide/) scans your repositories and highlights issues that may exist in the open-source dependencies.

The extension helps developers fix code at its origin phase and during the early stages of development. They can successfully perform early security reviews and mitigate the need for expensive fixes during later stages.

## Enhancements

## Use Python call graphs for vulnerability prioritization

Users can now use call graphs in Endor Labs application to analyze the dependencies and relationships among various functions in Python projects.

* Endor Labs generates the call graphs for your Python projects and identifies functions or methods with known vulnerabilities or potential security issues.
* Users can examine the call graph to identify the functions that directly or indirectly call the vulnerable functions by tracing the paths of execution.
* Users can prioritize the vulnerabilities based on their severity, threat levels, and application importance.

Call graphs assist users in comprehending the potential consequences and enable them to prioritize the resolution of vulnerabilities that are more likely to result in additional exploitation.

## EPSS probability filter for findings

Users can now use the new Exploit Prediction Scoring System **EPSS probability** filter on the **Findings** page to refine their findings search results by the [EPSS](https://www.first.org/epss/) score range.

## View Notifications

Users can now view the Jira tickets created for action policies in **Manage** > **Notifications** on the sidebar. Users have the ability to observe specific information such as the status of tickets (whether they are open or closed), the associated action policy, and other important details. This aids in seamless troubleshooting and identification of both unresolved and resolved issues.

## Release 1.5.104

We are excited to introduce you to the latest version of Endor Labs and endorctl - v 1.5.104. This release comes with the following new features.

## New Features

## Integrate Endor Labs with Jira

[Integrate Endor Labs with Jira](../../../integrations/jira-integration/) and receive alert notifications for your action policies in your Jira accounts. With this integration, administrators can automate the process of generating Jira tickets within their organization’s existing security workflows.

Administrators can choose to raise bugs or create tasks in Jira and notify required people about any failures.

## Set up SAML integration for Endor Labs

Set up SAML integration on Endor Labs, using an Identity Provider (IdP) that supports Security Assertion Markup Language (SAML), such as Okta, Microsoft Active Directory Federation Services (AD FS), Azure Active Directory (AD), Google, or OneLogin.

Administrators can use their existing Single Sign On (SSO) process in their organization and allow their users to seamlessly sign in to Endor Labs without providing credentials.

## Support for Ruby language scan

Endor Labs broadens its language scanning capabilities by incorporating support for the [Ruby programming language](../../../scan-with-endorlabs/language-scanning/ruby/). In addition to the current support for Java, JavaScript, Rust, Python, and Go, users can now scan and monitor their Ruby projects and repositories.

Endor Labs monitors the packages for dependencies and discovers unresolved, resolved, direct, and transitive dependencies. Users will also be able to view finding policy violations and dependency graphs.

## Release 1.5.43

Endor Labs and endorctl version 1.5.43 includes:

* A portfolio level view of all findings across your repositories
* SARIF output format support for GitHub Integrations
* Custom identity provider claim requests to allow for custom attribute based access controls
* Support for Gradle version 8
* The ability to ask natural language questions of open source software via DriodGPT
* The ability to configure, enable and disable your organizations desired findings

## New Capabilities

### A portfolio level view of all findings across your repositories

Organizations are now able to review all findings across their entire portfolio. Each project monitored by Endor Labs is aggregated into a global view of findings so that organizations can easily search for updates.

### SARIF output format support for GitHub integrations

In CI pipelines developers can now upload their findings to GitHub via a SARIF output of their findings. This enables developers to not have to leave GitHub to review detailed results.

### DroidGPT

Organizations can now ask natural language questions about open source software using DroidGPT. As part of Endor Lab’s open source explorer organizations can now ask questions like “What is the most secure package for json to csv conversion?”

## Release 0.5.126

Endor Labs and endorctl version 0.5.126 includes:

* Support for policy actions in CI pipelines (Beta)
* Environmental configuration checks for scanning
* Significant performance improvements
* Improved sorting and filtering for findings

## New Capabilities

### Support for policy actions in CI pipelines (Beta)

Endor Labs now enables users to configure policy that returns an error in CI pipelines. This can allow users to fail CI checks when a policy is violated to enforce organizational governance policy.

Endor Labs comes with out-of-the-box policy templates to enable teams to configure policy on known vulnerabilities, outdated, unmaintained and unused software dependencies.

### Environmental checks for scanning

Endor Labs now helps ensure that your machine is well setup for scanning by providing inline configuration checks on commands. If your host is not properly configured or does not have the required software to perform a given scan or command, the command line utility, endorctl will inform you.

### Improved sorting and filtering for findings

Findings can now be filtered and displayed based on categories to help users better report on what they care about and focus their attention.

Supported categories include:

* Vulnerabilities
* Supply Chain Risk
* License Compliance
* Supply Chain Posture Management Risk
* General Security Risks
* General Operational Risks

## Release 0.5.100

Endor Labs and endorctl version 0.5.100 includes:

* Scanning for JavaScript and Python is generally available.

## New Capabilities

### General Availability of Python and JavaScript Support

Endor Labs support for JavaScript and Python Language Scanning is now generally available.

## Release 0.5.80

Endor Labs and endorctl version 0.5.80 includes:

* Support for GitLab and Bitbucket source control repository scanning
* Support for Keyless Authentication in GCP with workload identity

## Major Changes

* Previously, Endor Labs supported remote cloning of GitHub based repositories. This option has been removed. Only locally cloned repositories are supported.

## New Capabilities

### Support for GitLab and Bitbucket based

Endor Labs now supports the ability to scan source control repositories hosted in GitLab and Bitbucket.

### Keyless Authentication for GCP

Endor Labs now supports the ability to leverage keyless authentication for workload identity federation in Google Cloud.

## Release 0.5.50

Endor Labs and endorctl version 0.5.50 includes:

* Support for parallel language scanning
* Identification of potential typos in dependencies
* Support to export Vulnerability Exploitability eXchange (VEX) data for packages
* Dependency License Identification
* Support for user authorization roles

## New Capabilities

### Parallel Language Scanning Support

Endor Labs now supports the ability to scan different languages in parallel to accelerate scan speed and performance.

### Identification of potential typos in dependencies

Endor Labs now supports the ability to monitor and alert on dependencies imported as typos of much more widely used dependencies in your environment.

### Export Vulnerability Exploitability eXchange (VEX) for packages

Endor Labs now enables software producers to export VEX documents with automated triage of unreachable vulnerable functions to support software consumer vulnerability triage efforts.

### Dependency license identification support

Endor Labs now identifies the license associated with an associated software dependency for open source license management.

### Authorization Roles

Endor Labs now comes with out-of-the-box authorization roles for platform users. Authorization roles include:

* Policy Editor - The policy editor role allows users to edit policy.
* Code Scanner - The code scanner role allows users with this permission to scan code. This is the minimum role for a CI/CD based service account.
* Read-only - The read only permission gives users full read only access to Endor Labs.
* Admin - The Admin permission gives users full read and write access to Endor Labs.

## Major Bug Fixes Resolved in version 0.5.50

* Previously, Endor Labs failed to scan a repository and identify packages within a repository if the repository was cloned with a shallow Git clone. This has been addressed in 0.5.50.

## Release 0.5.40

Endor Labs and endorctl version 0.5.40 includes:

* Support for EAR and WAR File scanning for Maven
* Fat/Uber JAR support for Maven
* Vulnerable function reachability analysis
* Call path visualizations for findings

## New Capabilities

### Enhanced Java Scanning Support

When scanning Java based web applications using EAR, WAR and Uber JAR files, Endor Labs now builds a bill of materials for these packages and is able to successfully perform static analysis for vulnerability prioritization.

### Vulnerable function reachability analysis

Endor Labs now identifies if a vulnerable function associated with a known vulnerability is reachable through static analysis in a provided Java package.

### Call Path Visualizations

Endor Labs will now display reachable function paths to dependencies and functions associated with known vulnerabilities.

## Release 0.5.31

Endor Labs and endorctl version 0.5.31 includes:

* The ability to export a Software Bill of Materials (SBOM) for a specified software package
* Windows support for endorctl
* Beta support for Gradle with Java
* Authorization Policies for enhanced access control with Endor Labs

## New Capabilities

### Support for exporting SBOMs

SBOMs may now be generated for any supported software package that you create in CycloneDX format. Endor Labs supports XML and json formats for CycloneDX and by default exports in CycloneDX 1.4.

### Windows Support for `endorctl`

Endor Labs now supports Windows for the endorctl binary. This allows Windows users who previously were using the Endor Labs Docker image to migrate to a supported binary on their native platform.

### Support for Gradle

Endor Labs now supports Gradle 7 and above as a build tool for Java packages. Java packages using Gradle 7 or above can now successfully have their dependencies resolved and generate call graphs for their packages.

### Authorization Policies

Endor Labs users can now set granular authorization policies for each supported identity provider. Users may now specify a unique user identity such as a GitHub handle or Google Workspace email address to authorize users. Authorization rules may also be timeboxed to ensure that a user only has access to Endor Labs for a predefined time.

Previously, new users could only be authorized by requiring them to be sent an email invitation to the platform.

## Major Bug Fixes Resolved in version 0.5.31

**Release date**: 28 October, 2022

* Previously, some packages failed dependency resolution due to a nil pointer exception. This resolution error has been addressed.
* Previously, when filtering findings based on their attributes filters only respected the current page being searched on. This issue has now been addressed.
* Previously, some findings that had an upstream patch available were displayed as having a fix unavailable. This issue has been addressed.

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
