---
url: https://docs.endorlabs.com/scan-with-endorlabs/data-exporters/
title: Data exporters | Endor Labs Docs
downloaded: 2026-01-26 10:07:22
---

Data exporters | Endor Labs Docs



* Type to search...

[Print entire section](/scan-with-endorlabs/data-exporters/_print.html)



# Data exporters

Learn how to export findings and scan data from Endor Labs to external storage and security platforms using the export framework.

Endor Labs provides an export framework that enables you to export scan data to external platforms for archival, compliance, or integration with other security tools. You can configure exporters to automatically send data to supported destinations after each scan.

## Supported export destinations

The export framework supports the following destinations.

| Destination | Description |
| --- | --- |
| [AWS S3](./export-to-s3/) | Export data to an Amazon S3 storage bucket for archival or integration with data analytics tools. |
| [GitHub Advanced Security](./export-to-ghas/) | Export findings in SARIF format to GitHub Advanced Security for viewing in the GitHub security dashboard. |

## Supported data types

You can configure exporters to export different types of data:

| Data Type | Description | Message Type | Exporters |
| --- | --- | --- | --- |
| Findings | Security findings from scans including vulnerabilities, secrets, and SAST issues | `MESSAGE_TYPE_FINDING` | S3, GHAS |
| Action policy findings | Findings that match your configured action policies (blocked or warning) | `MESSAGE_TYPE_ADMISSION_POLICY_FINDING` | GHAS |

## Supported export formats

| Format | Description | Format Type | Exporters |
| --- | --- | --- | --- |
| JSON | Export data in JSON format for flexibility and compatibility with various tools | `MESSAGE_EXPORT_FORMAT_JSON` | S3 |
| SARIF | Export findings in Static Analysis Results Interchange Format for security tools integration | `MESSAGE_EXPORT_FORMAT_SARIF` | S3, GHAS |

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
