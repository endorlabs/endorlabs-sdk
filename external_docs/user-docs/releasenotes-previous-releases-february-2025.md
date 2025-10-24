---
url: https://docs.endorlabs.com/releasenotes/previous-releases/february-2025/
title: February 2025 | Endor Labs Docs
downloaded: 2025-10-23 23:28:22
---

February 2025 | Endor Labs Docs



* Type to search...
* ---

[Print entire section](/releasenotes/previous-releases/february-2025/_print.html)



# February 2025

We are excited to introduce the latest features and enhancements in Endor Labs.

### Endor patch dashboard New

The Endor Patch dashboard demonstrates the impact of Endor patches and request patches directly within the product.

It provides:

* A list of the most impactful dependencies affecting applications, with patches available for evaluation.
* Existing patches that can be used immediately upon purchase, along with their organization-wide impact.
* A visualization of how multiple patches would affect an application portfolio.
* Filters for reachability and severity to refine results easily.
* The dashboard makes it easier to assess, justify, and act on patching needs efficiently.

For more information, see [Endor patch dashboard](../../../dashboards/endor-patches/).

### View scan history New

Scan History gives you a detailed view of past security scans, helping you track your project’s security posture over time. With full context on individual scans, you can assess fidelity and troubleshoot issues more effectively.

For more information, see [Review past scan details](../../../managing-projects/#review-past-scan-details).

### endorctl scan CLI options New

Use the following new endorctl CLI options for tagging findings and projects:

* **Associate custom tags with findings**: Using the newly introduced `endorctl scan` CLI flag `--finding-tags <tags>` you can associate a list of custom tags with findings generated for objects in your scan. You can also use these tags to search and filter findings in the Endor Labs user interface.
* **Associate custom tags to your projects**: Using the newly introduced `endorctl scan` CLI flag ``project-tags ` you can associate a list of custom tags to your projects.

For more information, see [endorctl scan commands](../../../endorctl/commands/scan/).

### Endor Labs Azure Pipelines extension New

The Endor Labs Azure Pipelines extension is now available in the [Visual Studio Marketplace](https://marketplace.visualstudio.com/items?itemName=EndorLabs.endorlabs-security-scan-task).

You can use the extension to seamlessly integrate Endor Labs scanning into Azure Pipeline. For more information, see [Use Endor Labs extension with Azure pipelines](../../../deployment/ci-scans/scan-with-azuredevops/#configure-azure-pipeline-to-use-endor-labs).

### Add Azure organizations to Endor Labs Enhancement

You can now add Azure organizations to Endor Labs instead of individual projects. All projects under the organization are added automatically. Azure organizations and projects are mapped as managed namespaces in Endor Labs.

For more information, see [Managed namespaces for Azure DevOps](../../../deployment/monitoring-scans/azure-app/#managed-namespaces-for-azure-devops).

### Handle multiple requirement files with custom names in pip Enhancement

Endor Labs now supports custom and multiple requirement file names while performing dependency analysis using the pip package manager.
For more information, see [Handling custom and multiple requirement files in pip](../../../scan-with-endorlabs/language-scanning/python/#handling-custom-and-multiple-requirement-files-in-pip).

### Support for py\_images with Bazel Enhancement

Endor Labs now supports scanning [py\_image](https://github.com/bazelbuild/rules_docker/blob/master/README.md#py3_image) with Bazel. For more information, see [Select and build your Bazel targets](../../../scan-with-endorlabs/language-scanning/bazel/#select-and-build-your-bazel-targets).

### Labels in Jira ticket Enhancement

Jira tickets created by Endor Labs now include the labels `endorlabs-scan` and `endor-severity`, making it easy to identify these tickets and the severity of the findings associated with them. For more information, see [View ticket details in Jira](../../../integrations/jira-integration/#view-ticket-details-in-jira).

### Enhanced findings user interface Enhancement

Endor Labs has improved the user interface for findings:

* Removed the **Overview tab** to simplify the findings workflow.
* Moved the **Dependencies** and **Packages** tabs under **Inventory** for better organization and accessibility.

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
