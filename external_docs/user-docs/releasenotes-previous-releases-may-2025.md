---
url: https://docs.endorlabs.com/releasenotes/previous-releases/may-2025/
title: May 2025 | Endor Labs Docs
downloaded: 2026-01-16 09:50:30
---

May 2025 | Endor Labs Docs



* Type to search...

[Print entire section](/releasenotes/previous-releases/may-2025/_print.html)



# May 2025

We are excited to introduce the latest features and enhancements in Endor Labs.

### Outpost: On-premise scheduler for monitoring scans Beta New

Outpost is a new on-premise scheduler for monitoring scans that you can run in your own Kubernetes cluster. When you install and configure Outpost, monitoring scans on your source code repositories are scheduled and run on your own Kubernetes cluster inside your firewall. For more information, see [Outpost](../../../deployment/monitoring-scans/outpost/).

### Authenticate Jira Data Center with Endor Labs Enhancement

You can now use **Personal Access Token (PAT)** to authenticate your Jira Data Center to Endor Labs.

For more information, see [Configure Jira integration.](../../../integrations/jira-integration/#configure-jira-integration-on-endor-labs)

### Pipenv support for Python projects Enhancement

Endor Labs now offers support for scanning Python projects that use Pipenv as their package manager by resolving dependencies from `Pipfile` and `Pipfile.lock`. For more information, see [Scan Python projects](../../../scan-with-endorlabs/language-scanning/python/).

### View AI usage in the application Enhancement

You can now view which features in the Endor Labs application use AI services. To modify AI access settings, go to **Settings** > **AI Access** and contact support to customize access based on your organization’s needs. For more information, see [AI access](../../../ai/ai-access/).

### Projects page user interface improvements Enhancement

The **Projects** page now includes enhancements that make it easier to explore, sort, and filter package data.

* The following new columns help you assess the overall health of your project.
  + **Dependency Resolution Status** - Shows the percentage of packages for which dependency resolution was successful.
  + **Reachability Analysis Status** - Shows the percentage of packages for which reachability analysis was successful.
* Click any column header to sort projects in ascending or descending order. For more information, see [Manage projects](../../../managing-projects/).
* From **Inventory** > **Packages**, you can now filter packages by Dependency Resolution or Reachability Analysis statuses to focus on relevant results.
* Sort packages by **Package** name, **Created** date, and **Last Scanned** date to quickly locate changes or specific dependencies. For more information, see [Packages](../../../managing-projects/packages/#filter-package-dependencies).

### Discontinue reachability analysis for Rust Breaking change

Reachability analysis is no longer supported for Rust projects. However, you can continue to scan Rust projects for software composition analysis and vulnerability detection.

### View findings location in Jira tickets Enhancement

You can now view the location of the findings identified by Endor Labs in your Jira tickets. For more information, see [Findings in Jira.](../../../best-practices/jira-with-endor-labs/#track-findings-in-jira)

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
