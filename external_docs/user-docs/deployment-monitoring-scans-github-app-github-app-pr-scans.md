---
url: https://docs.endorlabs.com/deployment/monitoring-scans/github-app/github-app-pr-scans/
title: Scan PRs using the Endor Labs GitHub app | Endor Labs Docs
downloaded: 2026-01-29 22:23:06
---

Scan PRs using the Endor Labs GitHub app | Endor Labs Docs



* Type to search...

[Print entire section](/deployment/monitoring-scans/github-app/github-app-pr-scans/_print.html)



# Scan PRs using the Endor Labs GitHub app

Learn how to scan PRs using the Endor Labs GitHub app.

To automatically scan the PRs when they are raised, set the pull request preferences during the [installation of the GitHub App](../../github-app/#install-the-github-app) or [GitHub App (Pro)](../../github-app/github-app-pro/#install-the-github-app). You can also edit the [integration preferences](../../github-app/#manage-github-apps-on-endor-labs) afterward to enable PR scanning.

The Endor Labs GitHub App provides a scan report with details about scan failures. The report includes warning and error logs, recommended actions when available, and a link to the full [scan history](../../../../managing-projects/scan-history/) for additional context.

To view the scan report:

1. Open the pull request where the scan failed.
2. Click on the three vertical dots and select **View Details** from the **Endor Labs Automated Scan** to view the scan report.

## View PR scan findings

To view the PR scan findings:

1. Sign in to Endor Labs.
2. Select **Projects** from the left sidebar.
3. Search for and select the project.
4. Select **PR runs** to view the PR scan findings.

**PR Runs** captures the commit ID, **Commit SHA**, the referenced branch, its findings, and the tags added to the scan as configured in the policies. Select the specific PR scan to view its findings in detail.

![PR scan results in PR Runs](../../../../images/pr-scan-findings.png)

## GitHub PR comments

You can enable GitHub PR comments during the initial setup of the [GitHub App](../../github-app/) or [GitHub App (Pro)](../../github-app/github-app-pro/), or by editing an existing integration. Once enabled, Endor Labs automatically adds comments to pull requests when policy violations are detected in the PR scans. See [Pull Request comments](../../../../scan-with-endorlabs/pr-scans/pr-comments/) for more information.

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
