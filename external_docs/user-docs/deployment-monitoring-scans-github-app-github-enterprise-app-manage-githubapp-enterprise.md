---
url: https://docs.endorlabs.com/deployment/monitoring-scans/github-app/github-enterprise-app/manage-githubapp-enterprise/
title: Manage GitHub Enterprise Server App on Endor Labs | Endor Labs Docs
downloaded: 2026-02-03 00:50:03
---

Manage GitHub Enterprise Server App on Endor Labs | Endor Labs Docs



* Type to search...

[Print entire section](/deployment/monitoring-scans/github-app/github-enterprise-app/manage-githubapp-enterprise/_print.html)



# Manage GitHub Enterprise Server App on Endor Labs

Learn how to manage your GitHub App Enterprise integration in Endor Labs.

Beta

You can make changes to the GitHub Enterprise Server App integrations or delete them. You can view the activity logs for the GitHub Enterprise Server App and rescan your GitHub Enterprise repositories on demand.

1. Sign in to Endor Labs and select **Manage** > **Integrations** from the left sidebar.
2. Click **Manage** next to **GitHub Enterprise Server** under **Source Control Managers**.

   ![Manage GitHub Enterprise Server App](../../../../../images/manage-github-enterprise.png)
3. Click the three vertical dots next to the integration.

   You can choose from the following options:

   * [**Edit Integration**](#edit-github-enterprise-server-app-integration)
   * [**View Sync Logs**](#view-sync-logs)
   * [**Delete Integration**](#delete-github-enterprise-server-app-integration)

### Edit GitHub Enterprise Server App integration

To edit the GitHub Enterprise Server App integration:

1. Click the three vertical dots next to the integration, and select **Edit Integration**.
2. Update your personal access token and choose the scanners.
3. Choose **Pull Request Scans** to set preferences for scanning pull requests submitted by users:
   * **Enable Automatic Pull Request Scanning** to automatically scan PRs submitted by users.
   * **Enable Pull Request Comments** to allow GitHub Actions to comment on PRs for policy violations.
   * Set the **Scanning Preferences** to:
     + **Quick Scan** for dependency resolution without reachability analysis. This provides rapid visibility into potential vulnerabilities for faster merges.
     + **Full Scan** for dependency resolution, reachability analysis, and call graph generation for supported languages. This provides full visibility but may take longer to complete.
4. Click **Save**. The changes are applied from the next scanning cycle.

### Delete GitHub Enterprise Server App integration

To delete a GitHub Enterprise Server App integration, click the three vertical dots next to the integration, and select **Delete Integration**.

Deleting the integration also deletes all child namespaces, projects, and references associated with the auto-generated root group namespace, as well as any manually created namespaces and projects under that namespace.

### Manage the Endor Labs GitHub Enterprise Server App

You can modify the app configuration or remove the app from your GitHub Enterprise Server instance.

1. Sign in to Endor Labs and select **Manage** > **Integrations** from the left sidebar.
2. Click **Manage** next to **GitHub Enterprise Server** under **Source Control Managers**.
3. Click **View Created Apps**.
4. Click the three vertical dots next to the app and select **Edit** to edit the app details or **Delete** to delete the app.

   ![Manage GitHub Enterprise Server App](../../../../../images/manage-github-enterprise-app.png)

**Note**

You cannot delete the app unless you uninstall it from all organizations where it is installed.

### View sync logs

To view sync logs, click the three vertical dots next to the integration, and select **View Sync Logs**.

The sync logs display details of synchronization attempts, including timestamps, error types, and diagnostic messages. These logs help identify issues such as authentication failures or configuration problems.

### Manually rescan GitHub Enterprise repositories

GitHub Enterprise Server App scans your repositories every 24 hours. Click **Rescan Org** to manually trigger a scan outside the 24-hour period.

### Add more GitHub Enterprise repositories to scan

Click **Scan More Repositories** to go to **Projects**, where you can add more repositories to scan through the GitHub Enterprise Server App. See [scan repositories](../#scan-more-repositories) to learn more.

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
