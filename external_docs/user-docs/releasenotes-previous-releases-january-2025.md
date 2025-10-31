---
url: https://docs.endorlabs.com/releasenotes/previous-releases/january-2025/
title: January 2025 | Endor Labs Docs
downloaded: 2025-10-27 13:00:36
---

January 2025 | Endor Labs Docs



* Type to search...
* ---

[Print entire section](/releasenotes/previous-releases/january-2025/_print.html)



# January 2025

#### Version upgrade notice

Effective 21st January 2025, Endor Labs and endorctl are upgraded to version 1.7 from the previous 1.6.x series. This version upgrade reflects continuous improvements to our GitHub App and introduces a new suite of capabilities to help teams accelerate their security maturity.

Policy updates and the activation of new policies are disabled by default. To allow automatic updates and enable new policies by default, see [Configure policy settings](../../../administration/configure-system-settings/#configure-policy-settings).

This update does not introduce any breaking changes and requires no action on your part. You can continue using the product without any impact on compatibility or performance.

We are excited to introduce the latest features and enhancements in Endor Labs.

### SAST scan with Endor Labs Beta New

You can now use the Endor Labs SAST scan to examine your source code and identify potential security vulnerabilities without program execution. For more information, see [SAST scan with Endor Labs](../../../sast-scans-with-endorlabs/).

### Detect AI models Beta New

Endor Labs’ scan can now detect AI models from HuggingFace used in Python projects and list them as dependencies. These models are flagged and displayed in the scan results. You can define custom policies to detect and flag models with low-quality scores, ensuring the use of secure and reliable AI models in your projects. For more information, see [Detect AI Models](../../../ai/ai-llm/).

### Monitor your projects using Endor Labs GitLab App Beta New

You can now use the Endor Labs GitLab App to continuously monitors your projects for security and operational risk. You can use the GitLab App to selectively scan your repositories for SCA, secrets, SAST, and CI/CD tools. For more information, see [Deploy Endor Labs GitLab App](../../../deployment/monitoring-scans/gitlab-app/).

### PR remediation with Endor Labs GitHub App Pro Beta New

You can use the Endor Labs GitHub App (Pro) to create automated pull requests to remediate findings in your GitHub environment. When PR remediation is set up, Endor Labs creates a PR to update the manifest files with dependency version upgrades, based on a remediation policy, to address vulnerability findings. For more information, see [Pull requests remediation in GitHub](../../../upgrades-and-remediation/pr-remediation/).

### Scan PRs with the Endor Labs GitHub App Beta New

In addition to automatically scanning your repositories every 24 hour, Endor Labs GitHub App can now perform fully automated scanning process for all pull requests and merges initiated into the main branch.

Whenever a PR is created against a repository, you can use the Endor Labs GitHub App to perform incremental scans to detect any changes in resolved dependencies that may introduce new vulnerabilities. These incremental scans are CI runs and are not monitored. You can see the results of the scan on GitHub.

Based on your preferences, you can perform a quick scan or a full scan before merging the PRs into the main branch.

* **Quick Scan** performs dependency resolution but does not conduct reachability analysis to prioritize vulnerabilities. The quick scan enables users to swiftly identify potential vulnerabilities in dependencies, ensuring a smoother and more secure merge into the main branch.
* **Full Scan** performs dependency resolution, reachability analysis, and generate call graphs for supported languages and ecosystems. This scan enables users to get complete visibility and identifies all issues related to dependencies and call graph generation, before merging into the main branch. Full scans may take longer to complete, potentially delaying PR merges.

### arm64 Linux binaries of endorctl New

endorctl is now available as arm64 binaries for Linux in addition to the existing AMD64 binaries. You can now use endorctl with arm64 flavors of Linux. For more information, see [Install endorctl on Linux](../../../getting-started/quickstart/quickstart-local-system/).

### Function level reachability for JavaScript/TypeScript projects Enhancement

Function level reachability analysis for JavaScript/TypeScript projects is now enabled by default. This means you no longer need to manually enable it using the `ENDOR_JS_ENABLE_TSSERVER` environment variable or the `--call-graph-languages` flag.

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
