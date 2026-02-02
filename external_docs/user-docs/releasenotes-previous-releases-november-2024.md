---
url: https://docs.endorlabs.com/releasenotes/previous-releases/november-2024/
title: November 2024 | Endor Labs Docs
downloaded: 2026-01-29 22:24:05
---

November 2024 | Endor Labs Docs



* Type to search...

[Print entire section](/releasenotes/previous-releases/november-2024/_print.html)



# November 2024

We are excited to introduce the latest features and enhancements in Endor Labs.

### Endor Labs Integration with Microsoft Defender for Cloud New

You can now set up an integration between Endor Labs and Microsoft Defender for Cloud.

This integration allows you to access reachability analysis directly within the Microsoft Defender for Cloud console, enabling you to prioritize fixes based on exploitability without switching between tools. Additionally, you can view detailed attack paths that reveal where vulnerable code is running throughout the SDLC and in the cloud, providing a new way to prioritize which vulnerabilities to remediate first.

For more information, see [Set up Microsoft Defender for Cloud integration with Endor Labs](../../../integrations/microsoft-defender-for-cloud/).

### Azure DevOps App New

Endor Labs now provides an Azure DevOps app that you can use to onboard your Azure Repos and continuously monitor in Endor Labs. You can seamlessly integrate your Azure project to an Endor Labs namespace. The Azure repos in the project are scanned every 24-hours, and you can initiate a rescan according to your convenience.

For more information, see [Azure DevOps App](../../../deployment/monitoring-scans/azure-app/).

### Analytics dashboard New

Endor Labs’ new **Analytics dashboard** provides a comprehensive overview of your security metrics, tracking vulnerability trends, and resolution times across projects. You can use it to quickly assess risk levels, monitor progress, and identify areas for improving your security posture. For more information, see [Analytics dashboard](../../../dashboards/analytics/)

### Function level reachability for JavaScript projects (Beta) New

Endor Labs is excited to announce the function level reachability analysis for JavaScript/TypeScript projects.

You can now track the exact portion of the code in a dependency that is being reused by a program. Endor Labs generates call graphs for JavaScript/TypeScript projects to help you:

* Analyze the dependencies and relationships among various functions in JavaScript projects. They help identify functions or methods with known vulnerabilities or potential security issues.
* Examine the call graph to identify the functions that directly or indirectly call the vulnerable functions by tracing the paths of execution.
* Prioritize the vulnerabilities based on their severity, threat levels, and application importance.

Call graphs assist users in comprehending the potential consequences and enable them to prioritize the resolution of vulnerabilities that are more likely to result in additional exploitation.

For more information, see [Scan JavaScript/TypeScript projects](../../../scan-with-endorlabs/language-scanning/javascript/#enable-call-graphs-beta).

### Configure package manager integrations with AWS CodeArtifact New

Configure Endor Labs to integrate with AWS CodeArtifact to use private libraries to build and scan your software.

You can set up an OpenID Connect provider in AWS and create roles with trust policies to allow Endor Labs access to your CodeArtifact repositories. For more information, see [Configure package manager integrations with AWS CodeArtifact](../../../integrations/package-manager/aws-codeartifact/).

### Configure Scan profile through Endor Labs user interface Enhancement

While scanning projects using the GitHub App, you can configure a scan profile and assign it to your projects directly from the Endor Labs user interface.
For more information, see [Configure Scan profile](../../../scan-with-endorlabs/manage-scan-profiles/configure-scanprofile-ui/).

### Differentiate base image and application layer vulnerabilities Enhancement

While scanning containers, you can now distinguish the base image related vulnerabilities from those in the application layer by first scanning the base image, followed by scanning any images built on top of it.
For more information, see [Discover base images](../../../scan-with-endorlabs/scan-containers/#discover-base-images-of-containers).

### Support for Go image with Bazel Enhancement

Endor Labs now supports scanning [Go image](https://github.com/bazelbuild/rules_docker/blob/master/README.md#go_image) with Bazel. For more information, see [Select and build your Bazel targets](../../../scan-with-endorlabs/language-scanning/bazel/#select-and-build-your-bazel-targets).

### Include resolved status for Jira integration Enhancement

Enhanced the **RESOLVED STATUS** configuration for Jira integrations. You can now specify a custom resolved status such as **Completed** for updating Jira tickets after findings are resolved. If no status is provided, Endor Labs will default to `Done`, `Resolved`, `Closed`, or `Fixed` based on the project settings. For more information, see [Configure Jira integration](../../../integrations/jira-integration/#configure-jira-integration-on-endor-labs).

### Dependency detection for GitHub Action packages Enhancement

Endor Labs no longer detects test dependencies in GitHub Action packages. This update reduces the number of transitive dependencies detected for GitHub Action packages, thereby streamlining dependency analysis and improving overall clarity.

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
