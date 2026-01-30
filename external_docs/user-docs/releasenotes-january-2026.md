---
url: https://docs.endorlabs.com/releasenotes/january-2026/
title: January 2026 | Endor Labs Docs
downloaded: 2026-01-26 10:05:18
---

January 2026 | Endor Labs Docs



* Type to search...

[Print entire section](/releasenotes/january-2026/_print.html)



# January 2026

We are excited to introduce the latest features and enhancements in Endor Labs.

### Export scan data to Amazon S3 New

Endor Labs now supports exporting scan data to an Amazon S3 storage bucket for archival, compliance, or integration with other tools. The S3 exporter supports exporting findings in JSON or SARIF format.

For more information, see [Export findings to S3](../../scan-with-endorlabs/data-exporters/export-to-s3/).

### Send separate notifications for each finding Enhancement

You can now use the **None (Notify for each Finding)** aggregation type to send separate notifications for every finding generated from the configured action policy, making it easier to track and assign individual security issues. This aggregation type is supported only for SAST and Secrets action policies.

For more information, see [Aggregation types for notifications](../../managing-policies/action-policies/#aggregation-types-for-notifications).

### Filter findings by tags in GitHub Advanced Security Enhancement

Endor Labs now includes finding tags and categories in the SARIF output when exporting findings to GitHub Advanced Security (GHAS). You can use these tags to filter and identify specific types of findings in GitHub code scanning, such as reachable vulnerabilities, findings with available fixes, or findings by category, like SCA, SAST, and Secrets.

For more information, see [Filter findings by tags in GitHub](../../scan-with-endorlabs/data-exporters/export-to-ghas/#filter-findings-by-tags-in-github).

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
