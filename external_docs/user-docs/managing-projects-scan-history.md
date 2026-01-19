---
url: https://docs.endorlabs.com/managing-projects/scan-history/
title: Scan history | Endor Labs Docs
downloaded: 2026-01-16 09:49:57
---

Scan history | Endor Labs Docs



* Type to search...

[Print entire section](/managing-projects/scan-history/_print.html)



# Scan history

View the history of scans performed on a project.

Scan history provides a detailed overview of past security scans performed on a project. It helps you understand your project’s security posture over time. With full context and details about individual scans in their repositories, you can assess scan fidelity and troubleshoot issues.

1. Select **Projects** from the left sidebar.
2. Search for and select a project to review.
3. Select **SCAN HISTORY** to review the past scans.

   * **List of Scans**: View all past scans, including details such as the scan time, duration, scan type, and tags.
   * **Findings Summary**: Review the number of security findings, categorized by severity: Critical, High, Medium, or Low.
   * **Commit Details**: Each scan is linked to a specific commit SHA, allowing users to track security issues to specific code changes.
   * **Scanned By**: Identifies the user or system that initiated the scan.
   * **Filtering & Search**: You can filter scans by status, scan type, and time range. You can search by tags, commit SHA, or specific include or exclude file paths.

     For example, you can select **Container** as a scan type from the dropdown list.

     ![scan type dropdown](../../images/scantypes-dropdown.png)

**Note**

The **analytics** scan is a periodic, automated scan triggered by the system that refreshes findings without any user action. The scan is triggered only when the **analytics-check** scan detects changes or new vulnerabilities.

The **analytics-check** scan is an automated, recurring process that checks for changes or newly introduced vulnerabilities and skips the **analytics** scan if no changes are detected.

4. Select a record to view general information about the scan or its logs.
   * **View details**: View scan details for in-depth information about a specific scan, including the scan status, result UUID, detected programming languages, system details, and the versions of key development tools used in the environment.
   * **Overview**: General information about the scans.
   * **Logs**: Monitor scan logs, even while scans are running, and filter by severity level, with selectable log severity from Emergency, Alert, Critical, Error, Warning, Notice, Info, or Debug for in-depth debugging and policy evaluations.

     You can access scan logs and toolchain details for projects onboarded through Endor Labs cloud using the GitHub, GitLab, or Azure DevOps Apps. The log levels in the selected scan result determine the available log severities.

     ![scan history logs](../../images/scan-history-logs.png)
   * **Issues**: View additional errors and warnings from the scan.
     ![scan history issues](../../images/scan-history-issues.png)

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
