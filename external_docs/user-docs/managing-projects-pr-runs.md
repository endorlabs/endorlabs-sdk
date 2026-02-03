---
url: https://docs.endorlabs.com/managing-projects/pr-runs/
title: PR runs | Endor Labs Docs
downloaded: 2026-02-03 00:50:11
---

PR runs | Endor Labs Docs



* Type to search...

[Print entire section](/managing-projects/pr-runs/_print.html)



# PR runs

View the history of PR scans performed on a project.

PR runs provide a detailed view of security scans performed on pull requests before they are merged. They help you assess the security impact of code changes and identify issues early in the development cycle. You can use them to verify merge readiness, ensure compliance, and troubleshoot scan failures with full context on vulnerabilities, policy violations, and dependency issues.

1. Select **Projects** from the left sidebar.
2. Search for and select a project to review.
3. Select **PR RUNS** to review the past scans.

   * **List of Scans**: View all past PR scans, including details such as the scan time, duration, scan type, and tags.
   * **Ref**: The Git reference identifying the scanned commit or branch. For Endor Labs SCM Apps, pre-merge pull request scans use a named ref (for example, `pr/1259`), while merge commit scans use a commit SHA.
   * **Findings Summary**: Review the number of security findings, categorized by severity: Critical, High, Medium, or Low.
   * **Commit Details**: Each scan is linked to a specific commit SHA, allowing users to track security issues to specific code changes.
   * **Scanned By**: Identifies the user or system that initiated the scan.
   * **Filtering & Search**: You can filter scans by status, scan type, and time range. You can search by tags, commit SHA, or specific include or exclude file paths.

     For example, you can select **Container** as a scan type from the dropdown list.

     ![scan type dropdown](../../images/pr-runs-ui.png)
4. Select a record to view general information about the scan or its logs.

   * **View Findings**: Displays security findings associated with the scan.

**Note**

Findings are not recorded in case of scan failures.

```
- **View Scan Result**: Displays scan information, issue logs with error details, and additional scan data.
- **Overview**: Displays general scan information such as the scan status, result UUID, detected programming languages, system details, and versions of key development tools used in the environment.
- **Issues**: Displays additional errors and warnings from the scan.
- **Logs**: Monitor scan logs, even while scans are running, and filter by severity level, with selectable log severity from Emergency, Alert, Critical, Error, Warning, Notice, Info, or Debug for in-depth debugging and policy evaluations.

    You can access scan logs and toolchain details for projects onboarded through Endor Labs cloud using the GitHub, GitLab, or Azure DevOps Apps. The log levels in the selected scan result determine the available log severities.

  ![pull request scans history logs](../../images/pr-scan-logs.png)
```

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
