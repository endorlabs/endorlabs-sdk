---
url: https://docs.endorlabs.com/releasenotes/previous-releases/march-2025/
title: March 2025 | Endor Labs Docs
downloaded: 2026-02-03 00:50:14
---

March 2025 | Endor Labs Docs



* Type to search...

[Print entire section](/releasenotes/previous-releases/march-2025/_print.html)



# March 2025

We are excited to introduce the latest features and enhancements in Endor Labs.

### Software Composition Analysis (SCA) for C and C++ projects Beta New

You can now perform Software Composition Analysis (SCA) for C and C++ projects using Endor Labs to identify vulnerabilities, track dependencies, and ensure compliance with open-source security best practices. This helps you manage risk effectively and maintain a secure codebase.

You can now include C and C++ in your [scan profile](../../../scan-with-endorlabs/manage-scan-profiles/configure-scanprofile-ui/) to enable scanning for C and C++ projects.

For more information, see [Scan C/C++ projects](../../../scan-with-endorlabs/language-scanning/c/).

### Perform keyless authentication with Azure New

Endor Labs now supports keyless authentication for Azure, enabling seamless and secure access without the need to store or manage keys. By configuring your Azure virtual machine with a managed identity and creating an authorization policy in Endor Labs, you can integrate with Azure services while ensuring credential security.

For more information, see [Keyless authentication for Azure](../../../deployment/ci-scans/keyless-authentication/azure-keyless-auth/).

### Scan profiles Enhancement

The following enhancements are available for [scan profiles](../../../scan-with-endorlabs/manage-scan-profiles/build-tools/).

* You can configure the latest .NET SDK 9.0 toolchain in your scan profiles. This update is available for Linux and Darwin (macOS)’s arm64 and amd64 architectures, ensuring seamless integration across platforms. For more information, see [Toolchain reference](../../../scan-with-endorlabs/manage-scan-profiles/build-tools/).
* You can set a default scan profile for a namespace. For more information, see [Set a default scan profile](../../../scan-with-endorlabs/manage-scan-profiles/configure-scanprofile-ui/#set-a-default-scan-profile).
* You can create a standard version of a build tool and use it across all scan profiles. For more information, see [Configure build tools](../../../scan-with-endorlabs/manage-scan-profiles/configure-scanprofile-ui/#configure-build-tools).

### Filter findings with action policy violations Enhancement

You can now filter findings that violate action policy with the action policy enforcement attribute.

For more information, see [Search for findings with basic filters](../../../managing-projects/view-findings/#search-for-findings-using-basic-filters).

### Comments in Jira tickets Enhancement

With Jira integration, scan findings are now automatically updated in your Jira ticket comments. If new issues are detected or existing findings are resolved, a comment is generated with details.

For more information, see [Comments in Jira tickets.](../../../integrations/jira-integration/#view-ticket-details-in-jira)

### NTLM proxy support Enhancement

You can now configure NTLM proxy settings on machines that need to connect to Endor Labs when Internet access requires NTLM-authenticated proxy servers.

For more information, see [Configure proxy servers](../../../administration/proxy-server-configuration/#configure-proxy-for-ntlm-authentication).

### PR remediation support for Python Enhancement

Endor Labs GitHub App (Pro) now supports PR remediation for Python, alongside Java, JavaScript, and Go. Automated remediation is available for dependencies managed through `pyproject.toml` and `requirements.txt`.

For more information, see [Pull requests remediation in GitHub](../../../upgrades-and-remediation/pr-remediation/)

### Include or exclude archived repositories Enhancement

You can now include or exclude archived repositories when configuring scans using Azure DevOps and GitLab Apps. By default, archived repositories are excluded to conserve resources.

For more information, see [Deploy Azure DevOps App](../../../deployment/monitoring-scans/azure-app/) and [Deploy GitLab App](../../../deployment/monitoring-scans/gitlab-app/).

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
