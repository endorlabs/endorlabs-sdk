---
url: https://docs.endorlabs.com/releasenotes/previous-releases/release-1-6-330/
title: June 2024 | Endor Labs Docs
downloaded: 2025-12-11 11:35:39
---

June 2024 | Endor Labs Docs



* Type to search...
* ---

[Print entire section](/releasenotes/previous-releases/release-1-6-330/_print.html)



# June 2024

We are excited to introduce you to the latest version of Endor Labs and endorctl - v1.6.330. This release includes new features and enhancements.

## New Features

### Endor Labs offerings

Endor Labs application now comes packaged in the following new license bundles, designed to offer flexible and comprehensive solutions to meet your organization’s unique needs.

* **Endor Labs Supply Chain** - Endor Labs Supply Chain is a single platform for open-source dependency management, CI/CD security, and compliance, providing comprehensive tools to ensure your software supply chain’s integrity and security.
* **Endor Labs Open Source Core** - Endor Labs Open Source Core includes basic SCA and SBOM capabilities, offering essential tools for open-source software management and security assessment.
* **Endor Labs Open Source Pro** - Endor Labs Open Source Pro includes all components of Endor Labs Open Source Core with additional features, providing an advanced suite for open-source software management.
* **Endor Labs CI/CD** - Endor Labs CI/CD includes components to strengthen the security posture of source code repositories and verify the integrity of your builds, ensuring secure and reliable CI/CD pipelines.
* **Endor Labs SBOM Hub** - Endor Labs SBOM Hub includes components to help manage your third-party SBOMs and generate findings, providing a centralized solution for software bill of materials management.
* **Endor Labs Secrets** - Endor Labs Secrets includes components to help you detect and prevent secret leaks.

For more details on Endor Labs’ offerings and the features they include, see [pricing and packaging](https://www.endorlabs.com/pricing).

### Exception policies

Exception policies define the conditions for applying an exception to a finding. When an exception is applied to a finding, it is tracked as an exception and action policies do not apply to it. Findings with exceptions are filtered out from Endor Labs reports by default.

For example, exception policies can be used to:

* Exclude a specific finding for a specific package from build breaking policies.
* Exclude specific vulnerabilities that are accepted across your organization.
* Mark an identified issue as a false positive.

The application also comes with templates that you can use to quickly create exception policies. Each exception policy template provides parameters to help you customize the conditions under which an exception is applied. See [exception policies](../../../managing-policies/exception-policies/)

## Enhancements

### GitHub Action policies

To address security and safety risks in GitHub Actions, Endor Labs has introduced the following new out-of-the-box finding policies for GitHub Actions.

**Policies for evaluating configuration settings in workflow files**

* Default workflow token permission should be read only
* Workflows should not be allowed to create and approve pull requests
* Restrict the use of runner groups for public repositories
* Restrict runner groups to specific repositories
* Restrict GitHub Actions to selected repositories

**Policies for assessing configuration settings in workflow files**

* Script injection detected in GitHub workflow file
* Non OIDC cloud authentication detected in GitHub workflow file
* Secrets object detected in GitHub workflow file
* Untrusted code checkout detected in workflow file

See [GitHub Action policies](../../../managing-policies/finding-policies/github-action-policies/).

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
