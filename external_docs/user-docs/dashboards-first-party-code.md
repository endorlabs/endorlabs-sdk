---
url: https://docs.endorlabs.com/dashboards/first-party-code/
title: First-party code | Endor Labs Docs
downloaded: 2026-01-29 22:22:05
---

First-party code | Endor Labs Docs



* Type to search...

[Print entire section](/dashboards/first-party-code/_print.html)



# First-party code

Visualize the first-party code vulnerabilities in your organization.

Use the widgets in the first-party code dashboard to understand the vulnerabilities in your codebase from a SAST and secrets perspective. Dashboard represents the vulnerabilities across all the projects in the given namespace.

![First-party code dashboard](../../images/first-party-code.png)

The following sections describe the widgets in the first-party code dashboard and how to use them.

* [Set the filters for the dashboard](#set-the-filters-for-the-dashboard)
* [SAST findings](#sast-findings)
* [Secrets findings](#secrets-findings)
* [OWASP Top 10 by severity](#owasp-top-10-by-severity)
* [Top 10 secret rules by severity](#top-10-secret-rules-by-severity)
* [Top Projects by SAST findings](#top-projects-by-sast-findings)
* [Top Projects by secrets findings](#top-projects-by-secrets-findings)

### Set the filters for the dashboard

You can filter the data displayed on the dashboard by applying filters based on the severity of the findings. You can choose the combination of critical, high, medium, and low severity findings.

### SAST findings

Displays the number of open SAST findings categorized by severity and languages. Click on the severity or language to view the list of specific findings.

### Secrets findings

Displays the number of open secrets findings. Valid secrets are critical in nature while invalid secrets are informational in nature with a low severity. The findings are based on the secrets finding policy configured for the projects. Click on the type of secret to view the list of specific findings.

### OWASP Top 10 by severity

Displays the number of OWASP Top 10 findings across your projects in a stacked bar chart. Each bar chart represents the OWASP security risk categorized by severity. Click on the bar to view the list of the SAST findings for that risk.

### Top 10 secret rules by severity

Displays the number of top 10 secret detection rule findings across your projects in a stacked bar chart. Each bar represents a secret rule categorized by severity. Click on a bar to view the list of findings identified by that secret rule.

### Top Projects by SAST findings

Lists the top five projects with the highest number of SAST findings. Click on the project to view the list of SAST findings associated with the project.

### Top Projects by secrets findings

Lists the top five projects with the highest number of secrets findings. Click on the project to view the list of findings associated with the project.

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
