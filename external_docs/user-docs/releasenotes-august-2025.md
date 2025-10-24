---
url: https://docs.endorlabs.com/releasenotes/august-2025/
title: August 2025 | Endor Labs Docs
downloaded: 2025-10-23 23:26:02
---

August 2025 | Endor Labs Docs



* Type to search...
* ---

[Print entire section](/releasenotes/august-2025/_print.html)



# August 2025

We are excited to introduce the latest features and enhancements in Endor Labs.

### Discontinuation of CI/CD tool scanning Breaking change

CI/CD tool scanning functionality is being deprecated and will be discontinued by September 15, 2025. This change does not affect the scanning of GitHub Action dependencies.

### AI security review New

AI security review provides automated code review capabilities using artificial intelligence to identify potential security issues in your code base. You can set up AI security review to review pull requests and raise findings for security issues.

For more information, see [AI security review](../../ai/ai-security-review/).

### First-party code dashboard New

The first-party code dashboard provides a comprehensive view of the vulnerabilities in your codebase from a SAST and secrets perspective.

For more information, see [First-party code dashboard](../../dashboards/first-party-code/).

### Container end of life dependency finding policy New

You can now enable the **End of Life Container Dependencies** finding policy to raise findings for OS-level packages and components in container images that have reached end of life.

For more information, see [Container finding policies](../../managing-policies/finding-policies/container-policies/).

### Malware policies New

Endor Labs now offers improved malware detection with detailed malware reasoning, broader coverage, and timely warnings before malicious packages disappear from registries. You can use the following new malware focused policies:

* **Malware finding policy**: Enable OSS finding policy to identify known malicious code or suspicious patterns in dependencies and raise findings for them.
* **Malware action policy**: Create an action policy from the malware template to define how to handle malware findings.
* **Malware exception policy**: Create an exception policy to apply exceptions to malware findings under defined conditions and exclude them from action policies.

For more information, see [OSS finding policy](../../managing-policies/finding-policies/oss-policies/), [Malware action policy](../../managing-policies/action-policies/templates/#malware), and [Malware exception policy](../../managing-policies/exception-policies/templates/#malware).

### Export SBOM in SPDX format New

You can now export Software Bill of Materials in the industry standard SPDX format, with support for both `json` and `tag-value` output formats, making it easier to integrate SBOMs into existing compliance, auditing, and security workflows.

For more information see [Export SBOM in Endor Labs](../../managing-sboms/exporting-sboms/#export-an-sbom-as-spdx).

### Support for pull request scans in GHAS SARIF exporter Enhancement

The GHAS SARIF exporter now supports pull request scans for GitHub App (Pro). If you have enabled pull request scans in your GitHub App, the GHAS SARIF exporter exports the findings for each pull request. You can view the findings for the pull request in GitHub Advanced Security.

For more information, see [Export findings to GitHub Advanced Security](../../deployment/monitoring-scans/github-app/github-app-pro/export-findings-to-ghas/).

### Azure OpenAI model detection Enhancement

Endor Labs extends AI model detection to include Azure OpenAI, surfacing detected models as dependencies during scans. Azure OpenAI models are detected but not scored, as provider metadata is limited.

For more information, see [AI model detection](../../ai/ai-llm/#ai-model-detection).

### Scan container image tarball Enhancement

You can now scan container images saved as tarball files using `endorctl`. This helps you analyze dependencies, generate SBOM details, and review security findings for container images that are not directly accessible from a registry.

For more information, see [Scan container image tarball](../../scan-with-endorlabs/scan-containers/#scan-container-image-tarball).

### Search for malware in Vulnerability Database Enhancement

You can now use the MAL identifier to search for known malware in the Endor Labs vulnerability database and quickly identify malicious packages alongside existing vulnerabilities.

For more information, see [Endor Labs vulnerability database](../../discover/vulnerability-db/).

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
