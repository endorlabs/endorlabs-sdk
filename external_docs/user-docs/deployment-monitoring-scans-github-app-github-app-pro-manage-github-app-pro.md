---
url: https://docs.endorlabs.com/deployment/monitoring-scans/github-app/github-app-pro/manage-github-app-pro/
title: Manage GitHub App (Pro) on Endor Labs | Endor Labs Docs
downloaded: 2026-01-29 22:21:27
---

Manage GitHub App (Pro) on Endor Labs | Endor Labs Docs



* Type to search...

[Print entire section](/deployment/monitoring-scans/github-app/github-app-pro/manage-github-app-pro/_print.html)



# Manage GitHub App (Pro) on Endor Labs

Learn how to manage your GitHub App integration in Endor Labs.

You can make changes to the GitHub App integrations or delete them. You can view the activity logs for the GitHub App and rescan your GitHub repositories on demand.

1. Sign in to Endor Labs and select **Manage** > **Integrations** from the left sidebar.
2. Click **Manage** next to **GitHub** under **Source Control Managers**.

   ![Manage GitHub App](../../../../../images/manage-github-app-pro.png)
3. Click the three vertical dots next to the integration.

   You can choose from the following options:

   * [**Edit Integration**](#edit-github-app-integration)
   * [**Delete Integration**](#delete-endor-labs-github-app)
   * [**View Sync Logs**](#view-sync-logs)
   * [**Migrate to Standard App**](#migrate-to-standard-github-app)

### Edit GitHub App integration

To edit the GitHub App integration:

1. Click the three vertical dots next to the integration, and select **Edit Integration**.
2. Update your personal access token and choose the scanners.
3. Choose **Pull Request Scans** to set preferences for scanning pull requests submitted by users:
   * **Enable Automatic Pull Request Scanning** to automatically scan PRs submitted by users.
   * **Enable Pull Request Comments** to allow GitHub Actions to comment on PRs for policy violations.
   * Set the **Scanning Preferences** to:
     + **Quick Scan** for dependency resolution without reachability analysis. This provides rapid visibility into potential vulnerabilities for faster merges.
     + **Full Scan** for dependency resolution, reachability analysis, and call graph generation for supported languages. This provides full visibility but may take longer to complete.
4. Click **Save**. The changes are applied from the next scanning cycle.

### Delete Endor Labs GitHub App

To delete a GitHub App integration, click the three vertical dots next to the integration, and select **Delete Integration**.

When you delete the integration, it also deletes all child namespaces, projects, and references associated with the auto-generated root group namespace, as well as any manually created namespaces and projects under that namespace.

### View sync logs

To view sync logs, click the three vertical dots next to the integration, and select **View Sync Logs**.

The sync logs display details of synchronization attempts, including timestamps, error types, and diagnostic messages. These logs help identify issues such as authentication failures or configuration problems.

![sync logs](../../../../../images/sync-logs-github.png)

### Migrate to Standard GitHub App

**Warning**

You cannot have both GitHub App and GitHub App (Pro) simultaneously in your environment. When you migrate from one app to the other, select the same set of repositories as before to preserve the currently scanned projects and findings after the migration.

To migrate from GitHub App (Pro) to standard GitHub App:

1. Click the three vertical dots on the right side of the integration that you want to edit, and select **Migrate to Standard App**.
2. Click **Migrate**.

   You will be redirected to GitHub.
3. Click **Configure**.
4. Select a user to authorize the app.
5. Select **Configure** in the organization in which you want to migrate the app.
6. Select whether to install and authorize Endor Labs on all your repositories or select the specific repositories that you wish to scan.
7. Choose the namespace and click **Next**.

**Warning**

You must choose the same namespace as your existing GitHub App installation.

8. Select and enable the scanners you require.
9. Select the preferences for scanning pull requests, if required.
10. Click **Continue**.

**Old installation cleanup**

After migration is successful, delete the old installation from your GitHub organization.

**Branch protection rules**

When you migrate from one app to another, you must manually update your branch protection rules in GitHub. Branch protection rules that reference the old GitHub App (Pro) ID will become inactive and will not function until reconfigured with the new app. Refer to [Branch protection rules](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/managing-a-branch-protection-rule#creating-a-branch-protection-rule) to learn more.

### Manually rescan GitHub repositories

GitHub App scans your repositories every 24 hours. Click **Rescan Org** to manually trigger a scan outside the 24-hour period.

### Add more GitHub repositories to scan

Click **Scan More Repositories** to go to **Projects**, where you can add more repositories to scan through the GitHub App.

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
