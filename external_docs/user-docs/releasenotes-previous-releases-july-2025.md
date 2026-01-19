---
url: https://docs.endorlabs.com/releasenotes/previous-releases/july-2025/
title: July 2025 | Endor Labs Docs
downloaded: 2026-01-16 09:50:28
---

July 2025 | Endor Labs Docs



* Type to search...

[Print entire section](/releasenotes/previous-releases/july-2025/_print.html)



# July 2025

We are excited to introduce the latest features and enhancements in Endor Labs.

### Support for CVSS v4.0 scores New

Endor Labs now supports CVSS v4.0, as an enhanced standard for vulnerability severity assessment.

CVSS v4.x scores, including full vector strings and metadata are available in Endor Lab’s reporting and data exports. Note that Vanta exports continue to support only CVSS v3.x.

By default, Endor Labs uses **CVSS v3.x**. You must explicitly configure the system to use **CVSS v4.x.**

For more information, see [Configure CVSS score version](../../../administration/configure-system-settings/)

### Endor Labs Vulnerability Database New

Endor Labs now includes a comprehensive vulnerability database to search and analyze known issues across software dependencies using CVE, GHSA, and PySEC identifiers. It maps vulnerable package versions to impacted projects and findings to support easier remediation.

For more information, see [Endor Labs vulnerability database](../../../discover/vulnerability-db/).

### SARIF export to GitHub Advanced Security New

Endor Labs now supports exporting findings to GitHub Advanced Security as SARIF files. You can use GitHub Advanced Security to analyze and triage findings from Endor Labs.

For more information, see [Export findings to GitHub Advanced Security](../../../deployment/monitoring-scans/github-app/github-app-pro/export-findings-to-ghas/).

### Discover AI models Enhancement

Endor Labs extends AI model detection to include external providers, listing detected models as dependencies. Hugging Face models are scored, as they are open source and provide extensive public metadata. Models from other providers are detected but not scored due to limited data.

For more information, see [AI model detection](../../../ai/ai-llm/#ai-model-detection).

### C/C++ scan improvements Enhancement

**Effective Monday, July 21, 2025**, Endor Labs is releasing new updates to the code segment analyzer and the underlying database of hashes and embeddings used in C/C++ Software Composition Analysis. If you use continuous integration workflows or perform local scans, you must update to the latest version of `endorctl` and re-run your scan with:

```
endorctl scan --languages=c
```

The first scan may take longer than usual, as it rebuilds the cache of code segments. You may also see differences in the results compared to previous scans. These changes improve the accuracy of dependency detection and matching.

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
