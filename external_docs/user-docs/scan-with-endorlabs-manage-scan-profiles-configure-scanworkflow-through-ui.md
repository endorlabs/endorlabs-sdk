---
url: https://docs.endorlabs.com/scan-with-endorlabs/manage-scan-profiles/configure-scanworkflow-through-ui/
title: Configure scan workflow through Endor Labs user interface | Endor Labs Docs
downloaded: 2025-10-27 13:00:04
---

Configure scan workflow through Endor Labs user interface | Endor Labs Docs



* Type to search...
* ---

[Print entire section](/scan-with-endorlabs/manage-scan-profiles/configure-scanworkflow-through-ui/_print.html)



# Configure scan workflow through Endor Labs user interface

Learn how to configure scan workflow through the Endor Labs user interface.

Configure scan workflows to define how your projects are scanned. You can assign [scan profiles](../../manage-scan-profiles/) to scanning steps and control their order of execution, and manage these settings in the Endor Labs user interface.

## Set up a scan workflow

Set up a scan workflow to define scanning steps, assign profiles, and manage how your projects are scanned.

1. Sign in to Endor Labs and select **Projects** in the left sidebar.
2. Select the project for which you want to configure a scan workflow.
3. Navigate to **Settings** and select **Scan Workflow**.
4. Click **Add Step** to add an existing scan profile.
5. Enter a descriptive name in **Step title** to describe the workflow step.
6. Select a scan profile from your namespace for this step.
7. Click **Save** to add this step, and repeat to add as many steps as you need.
8. Toggle **Enabled** for each step to choose which steps to include in the workflow during the scan.
9. Configure additional options in GitHub App features. See [GitHub App features](#set-up-github-app-features) for more information.
10. Click **Save**.

### Set up GitHub App features

Configure GitHub App features in scan workflows to enable pull request scanning, AI security reviews, and custom scan settings for your projects.

1. Select the pull request flags you want to enable for the scan workflow.

   * **Pull request scans**: Automatically scan changes in the pull request.
   * **Pull request comments**: Add scan results as comments in the pull request.
2. Select the AI Security Review settings that you want to enable for the scan workflow.

   * **AI Security Review Scans**: Automatically analyze code repositories with AI, detect vulnerabilities and misconfigurations, and generate detailed security reports.
   * **Disable Code Summary**: Exclude the code summary from the AI Security Review scan report.
   * Enter a **Custom Prompt** to modify how AI Code Security Review detects and categorizes security related changes. You can use this only when **AI Security Review Scans** is enabled.
3. Select **Disable code snippet storage for SAST** to exclude code summary from the AI Security Review scan report. See [automated scan parameters](../build-tools/#configure-automated-scan-parameters) to learn more.
4. Enter any additional environment variables, if required. Only the environment variables starting with `ENDOR_` are passed to the scan, all others are ignored.
5. Click **Save**.

#### Note

GitHub App feature settings defined in the scan workflow take precedence over those specified in the individual scan profiles.

## Customize scan workflow

Customize the scan workflow to control which profiles, checks, and features are applied to your project.

### Edit scan workflow

To edit the steps in your scan workflow:

1. Select the project for which you want to configure a scan workflow.
2. Navigate to **Settings** and select **Scan Workflow**.
3. Click **Edit Step** and update the step title.
4. Select a different scan profile to replace the one associated with the step.
5. Click **Save**.

### Remove a step from scan workflow

To remove a step from the scan workflow:

1. Select the project for which you want to configure a scan workflow.
2. Navigate to **Settings** and select **Scan Workflow**.
3. Click **Remove**.

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
