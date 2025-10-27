---
url: https://docs.endorlabs.com/releasenotes/previous-releases/release-1-6-372/
title: July 2024 | Endor Labs Docs
downloaded: 2025-10-27 13:00:42
---

July 2024 | Endor Labs Docs



* Type to search...
* ---

[Print entire section](/releasenotes/previous-releases/release-1-6-372/_print.html)



# July 2024

We are excited to introduce you to the latest version of Endor Labs and endorctl - v1.6.372. This release includes new features and enhancements.

### Scan containers (Beta) New

Endor Labs introduces comprehensive container image scanning to help you identify and prioritize risks while ensuring compliance.

**Key Features**:

* **Operating system packages**: Detects packages installed via the container’s base OS package manager.
* **Programming language packages**: Identifies packages installed through language-specific package managers.
* **Libraries and dependencies**: Scans for static and dynamic libraries, and runtime dependencies required by the application.

In addition, Endor Labs generates an SBOM (Software Bill of Materials) that details all components, their versions, and associated metadata, providing a complete inventory of the container’s contents.

![Container scan](../../../images/container-overview.png)

### Customize notification templates Enhancement

Endor Labs provides out-of-the-box notification templates with standard information for policy violation messages in GitHub PR comments, webhooks, email, and Slack notifications. You can use the default template or customize it to fit your organization’s specific requirements. Additionally, you can create your custom templates using [Go Templates](https://pkg.go.dev/text/template).

For more details, see

* [Customize GitHub PR comments notification templates](../../../deployment/ci-scans/scan-with-github-actions/#customize-github-pr-comments-notification-templates).
* [Customize email notification templates](../../../integrations/email/#customize-email-notification-templates).
* [Customize webhook notification templates](../../../integrations/webhooks/#customize-webhook-notification-templates).
* [Customize Slack notification templates](../../../integrations/slack-integration/#customize-slack-notification-templates).

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
