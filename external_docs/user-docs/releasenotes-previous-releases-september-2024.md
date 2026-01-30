---
url: https://docs.endorlabs.com/releasenotes/previous-releases/september-2024/
title: September 2024 | Endor Labs Docs
downloaded: 2026-01-26 10:09:35
---

September 2024 | Endor Labs Docs



* Type to search...

[Print entire section](/releasenotes/previous-releases/september-2024/_print.html)



# September 2024

We are excited to introduce the latest features and enhancements in Endor Labs.

### Enhanced user interface for Global Findings New

Endor Labs has a new user interface for viewing all findings.

* **Findings list**: The new findings come in a tabular format with columns that include location, EPSS, tags, and more
* **Preset filters**: These preset filters help you to look for the category of findings you care about the most.
  For example, **Prioritized Findings** gives you a List of critical vulnerability findings in the last 30 days that have either a reachable function or a reachable dependency, are not test dependencies, and have an available fix.
* **Detailed drawers**: This side panel drawer provides detailed metadata inside the drawer that includes risk details, fix info, and call graphs when available.

The new updates are designed to enhance your experience by providing:

* **Modern look and feel**: A refreshed, modern design that’s cleaner and more intuitive.
* **Enhanced navigation bar**: Streamlined menus to help you find what you need faster.
* **Improved performance**: Faster load times and smoother transitions for a more efficient workflow with default filters pre-loaded.

![Findings IA](../../../images/findings-ia.png).

### Scan Scala projects with Bazel Enhancement

Users can now scan Scala projects with Bazel using `endorctl scan --use-bazel`. By leveraging this command as a Bazel rule, you can analyze dependencies while using Bazel commands.

* **Bazel Integration**: Scan Scala projects by calling the endorctl scan command as a Bazel rule, ensuring smooth integration with Bazel workflows.
* **Targeted Scanning**: Choose between scanning the entire repository or specific Scala targets using Bazel rules. You can also use a Bazel query to scan targets based on specific criteria.
* **Incremental Scans**: Execute scans by focusing only on recently updated targets, optimizing the scanning process for enhanced efficiency.

For more information, see [Scan with Bazel](../../../scan-with-endorlabs/language-scanning/bazel/#select-and-build-your-bazel-targets).

### Discover container base images Enhancement

Endor Labs container scan automatically identifies the base image used in your container, along with its dependencies, such as software packages and libraries. This enables you to perform a comprehensive security assessment by detecting any vulnerabilities in the base image, ensuring your containers are secure.

You can view and filter dependencies based on the container images.
For more details, see [Discover container images](../../../scan-with-endorlabs/scan-containers/#discover-base-images-of-containers)

![Filter container findings](../../../images/filter_base-images.png).

### Integrate Endor Labs with Google Cloud Build Enhancement

Integrate security scans into your Google Cloud Build pipelines to automatically detect vulnerabilities and issues during the development process. By performing scans within Google Cloud Build, you ensure that code changes are analyzed before deployment, strengthening the security and reliability of your cloud-native applications.

For more details, see [Scan with Google Cloud Build](../../../deployment/ci-scans/scan-with-google-cloud-build/).

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
