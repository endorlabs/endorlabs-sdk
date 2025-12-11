---
url: https://docs.endorlabs.com/deployment/monitoring-scans/gitlab-app/manage-gitlab-app/
title: Manage GitLab App on Endor Labs | Endor Labs Docs
downloaded: 2025-12-11 11:32:19
---

Manage GitLab App on Endor Labs | Endor Labs Docs



* Type to search...
* ---

[Print entire section](/deployment/monitoring-scans/gitlab-app/manage-gitlab-app/_print.html)



# Manage GitLab App on Endor Labs

Learn how to manage your GitLab App integration in Endor Labs.

You can make changes to the GitLab App integrations or delete them. You can view the activity logs for the GitLab App and rescan your GitLab projects on demand.

1. Sign in to Endor Labs and select **Manage** > **Integrations** from the left sidebar.
2. Click **Manage** next to **GitLab** under **Source Control Managers**.

   ![Manage GitLab App](../../../../images/gitlab-app-manage.png)
3. Click the three vertical dots next to the integration.

   You can choose from the following options:

   * [**Edit Integration**](#edit-gitlab-app-integration)
   * [**Delete Integration**](#delete-endor-labs-gitlab-app)
   * [**View Sync Log**](#view-sync-logs)

### Edit GitLab App integration

To edit the GitLab App integration:

1. Click the three vertical dots next to the integration, and select **Edit Integration**.
2. You can update your personal access token and choose the scanners.
   ![Edit GitLab App](../../../../images/GitLabAppManageEdit.png)\
3. Select **Merge Request Settings** to edit the MR scans configuration.

   See [GitLab App MR scans](../gitlab-mr-scan/) for more information.

**Scope of the Personal Access Token**

Replace the personal access token with the personal access token of a project developer (minimum) role with the `api` scope for MR scans.

4. Click **Save**.

   The changes are applicable from the next scanning cycle.

### Delete Endor Labs GitLab App

To delete a GitLab App integration, click the three vertical dots next to the integration, and select **Delete Integration**.

![Manage GitLab App](../../../../images/gitlab-app-manage.png)

When you delete the integration, it will also delete all child namespaces, projects and references associated with the auto-generated root group namespace. It also deletes any manually created namespaces and projects under auto-generated namespace.

### View sync logs

Endor Labs detects and reports installation and synchronization errors during organization sync. These include expired tokens, insufficient permissions, invalid host configurations, and certificate issues. Sync logs report those errors that you can resolve.

![Sync logs showing error](/images/scm-installation-error.png)

To view sync logs, click the three vertical dots next to the integration, and select **View Sync Logs**.

The sync logs display details of synchronization attempts, including timestamps, error types, and diagnostic messages. These logs help identify issues such as authentication failures or configuration problems.

#### Types of errors

The sync logs detect and display the following categories of sync failures:

* **Expired or invalid Personal Access Tokens (PATs)**: The PAT used for authentication has expired or is no longer valid. Edit the integration and provide a valid token.
* **Insufficient PAT permissions**: The PAT does not have the required scopes, such as repository read access. You must generate and provide a PAT with the correct access.
* **Certificate related access issues**: The certificates required to connect to the SCM are invalid, outdated, or untrusted. This error occurs in self-hosted GitLab instances that use custom SSL certificates. Update the certificate configuration or ensure the certificate chain is properly trusted to resolve the issue.
* **Incorrect or invalid host URLs**: The configured URL is incorrect or unreachable. Since you cannot edit the host URL, you need to delete and reinstall the integration using the correct URL.

After you resolve the issue, the error is automatically cleared during the next successful scan. You can manually re-trigger the scan using **Rescan Org** to verify the resolution immediately.

![sync logs](../../../../images/sync-logs-gitlab.png)

### Manually rescan GitLab projects

The GitLab App scans your repositories every 24 hours. Click **Rescan Org** to manually trigger a scan outside the 24-hour period.

### Add more GitLab projects to scan

Click **Scan More Repositories** to go to **Projects**, where you can add more projects to scan through the GitLab App.

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
