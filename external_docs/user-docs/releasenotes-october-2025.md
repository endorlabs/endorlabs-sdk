---
url: https://docs.endorlabs.com/releasenotes/october-2025/
title: October 2025 | Endor Labs Docs
downloaded: 2026-01-29 22:22:22
---

October 2025 | Endor Labs Docs



* Type to search...

[Print entire section](/releasenotes/october-2025/_print.html)



# October 2025

We are excited to introduce the latest features and enhancements in Endor Labs.

### Discontinuation of CI/CD tool scan Breaking Change

CI/CD tool scanning has been discontinued and is no longer available. This change does not affect the scanning of GitHub Action dependencies.

### Endor AI chat New

Endor Labs now includes **Endor AI Chat**, an AI-powered assistant designed to help you understand vulnerabilities and take quicker, more informed action. You can ask natural language questions about security findings, scan results, package versions, and vulnerabilities. See [Endor AI chat](../../ai/ai-chat/).

### Pre-computed reachability analysis New

Endor Labs now supports pre-computed reachability analysis to determine vulnerability exposure in dependencies without requiring code compilation or full call graph generation. You can enable it using the pre-computed flag for quick scans and full scans.

For more information, see [Pre-computed reachability analysis](../../introduction/reachability-analysis/pre-computed-reachability/).

### Search for authorization policies Enhancement

You can now search for authorization policies using rule criteria, creator email addresses, and namespace assignments.

For more information, see [Search authorization policies](../../administration/access-endorlabs/authorization-policies/#search-authorization-policies).

### Filter notifications using project name Enhancement

You can now filter notifications by project name to focus on notifications from specific projects and reduce noise from others.

For more information, see [Notifications](../../getting-started/endor-labs-ui/#notifications).

### Gradle support for Scala projects Enhancement

Endor Labs now supports scanning Scala projects built with Gradle by resolving dependencies from `build.gradle` or `build.gradle.kts` files.

For more information, see [Scan Scala projects](../../scan-with-endorlabs/language-scanning/scala/).

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
