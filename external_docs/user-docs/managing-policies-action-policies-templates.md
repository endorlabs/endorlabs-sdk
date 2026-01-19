---
url: https://docs.endorlabs.com/managing-policies/action-policies/templates/
title: Action policy templates | Endor Labs Docs
downloaded: 2026-01-16 09:47:09
---

Action policy templates | Endor Labs Docs



* Type to search...

[Print entire section](/managing-policies/action-policies/templates/_print.html)



# Action policy templates

Learn about the predefined action policy templates and how to customize them.

Endor Labs provides the following action policy templates that you can use to quickly create action policies.
Each policy template provides parameters to help you customize the conditions under which a policy action takes place.

**Note**

All action policy templates automatically only match new findings for PR scans, assuming that there is a baseline that the scan results can be compared to. If the finding already exists in the baseline, then it is not considered to be a match. See [PR baseline](../../../endorctl/commands/scan/#pull-request-ci-flags) and [PR comments](../../../scan-with-endorlabs/pr-scans/pr-comments/#enable-pr-comments) to learn more.

The following template categories are available:

* [Container](#container)
* [Malware](#malware)
* [SAST](#sast)
* [SCA](#sca)
* [Secrets](#secrets)
* [Security Review](#security-review)
* [Vulnerabilities](#vulnerabilities)

## Container

Use these templates to define actions for findings related to container images, including vulnerabilities in base images, installed packages, and container configurations.

### Containers

Matches container findings for vulnerabilities that meet specific parameters.

The following table describes the parameters.

| Parameter | Description |
| --- | --- |
| Vulnerability ID | Full vulnerability identifier. For example, CVE-2024-3727 or GHSA-qh2h-chj9-jffq (case insensitive). |
| Severity | Only match findings with this severity. |
| Fix Availability | Select **Fix Available** to only match findings if a patch is available to fix the issue in the dependency. |
| Relationship | Select **Direct Dependency** to only match findings for direct dependencies, or **Transitive Dependency** to only match findings for transitive dependencies. |
| EPSS Percentile Threshold | Only match findings with an EPSS percentile threshold equal to or higher than this threshold (0.00-100.00). The EPSS percentile threshold represents the percentile ranking among all vulnerabilities that a vulnerability will be exploited. |
| EPSS Probability Threshold | Only match findings with an EPSS probability score equal to or higher than this threshold (0.00-1.00). The EPSS probability score represents the probability [0-1] of exploitation in the wild in the next 30 days following score publication. |
| Exploited | Only match findings for CVEs that are listed in the Known Exploited Vulnerabilities (KEV) database. |
| Ecosystem | Match finding ecosystem. |
| Exclude if Dependency Name Contains | Allows you to define full or partial dependency names for which an action policy should exclude. For example, you want to exclude a specific dependency from this policy. |
| Exclude if Package Name Contains | Allows you to define full or partial package names for which an action policy should exclude. This is the resource that the finding is raised against. For example, the package indirectly or directly includes an unmaintained dependency. |
| Exclude findings for transitive dependencies via other projects | Exclude findings for transitive dependencies that can only be reached through other projects. This helps your team to not act when they do not have control of findings introduced by libraries your team developed. |
| Branch Type | Only match findings for this branch type. Set to **Default** to match findings for the default branch. Set to **Ref** to match findings for reference (non-default) branches. Set to **Pull Request** to match findings for pull requests. Note that the **Send Notification** action does not apply to pull requests, as notifications are only processed for monitored branches. |

### Custom (Advanced)

Allows you to define a custom action policy based on the attributes of the finding.

The following table describes the parameters.

| Parameter | Description |
| --- | --- |
| Finding Name | Match full or partial finding name. |
| Category | Match finding category. |
| Type | Match finding type. |
| Severity | Match finding severity. |
| Fix Availability | Select **Fix Available** to only match findings if a patch is available to fix the issue in the dependency. |
| Relationship | Select **Direct Dependency** to only match findings for direct dependencies, or **Transitive Dependency** to only match findings for transitive dependencies. |
| Dependency Reachability | Select **Reachable Dependency** and **Potentially Reachable Dependency** to only match findings where the vulnerable dependency is reachable. |
| Function Reachability | Select **Reachable Function** and **Potentially Reachable Function** to only match findings where the vulnerable function is reachable. |
| Exclude Test | Select **Yes** to exclude test dependencies. |
| Ecosystem | Match finding ecosystem. |
| Custom Tag | Only match findings that have this custom tag (set by the policy that created the finding or using the `--finding-tags` CLI option). Note that these are different and separate from the system-defined finding tags. |
| Include Path | Only match findings for dependencies or files that match this glob style file pattern. For example, `src/golang/**`. |
| Exclude Path | Do not match findings for dependencies or files that match this glob style file pattern. For example, `src/golang/**`. |
| Exclude if Dependency Name Contains | Allows you to define full or partial dependency names for which an action policy should exclude. For example, you want to exclude a specific dependency from this policy. |
| Exclude if Package Name Contains | Allows you to define full or partial package names for which an action policy should exclude. This is the resource that the finding is raised against. For example, the package indirectly or directly includes an unmaintained dependency. |
| Exclude findings for transitive dependencies via other projects | Exclude findings for transitive dependencies that can only be reached through other projects. This helps your team to not act when they do not have control of findings introduced by libraries your team developed. |
| Include GitHub Action findings | Select **Yes** to include findings for GitHub action dependencies. |
| Include Container findings | Select **Yes** to include findings for container dependencies. |
| Branch Type | Only match findings for this branch type. Set to **Default** to match findings for the default branch. Set to **Ref** to match findings for reference (non-default) branches. Set to **Pull Request** to match findings for pull requests. Note that the **Send Notification** action does not apply to pull requests, as notifications are only processed for monitored branches. |
| Code Owner | Only match findings with this code owner. For example, `@octocat` or `@octocat-team`. Case-insensitive exact matches only, no partial or approximate (fuzzy) matches. If a finding does not have a code owner, it is not matched by the policy. Code owners are automatically assigned to findings based on the `CodeOwners` object for the project, which is generated from the CODEOWNERS file in the default branch of the repository. For projects without a CODEOWNERS file, the `CodeOwners` object can be managed through the API. |

#### Finding categories

Findings are classified into one or more of the following categories:

| Category | Description |
| --- | --- |
| AI Models | AI model related findings. See [AI model policies](../../../ai/ai-model-policies/) for details. |
| CI/CD | Umbrella category for CI/CD pipeline findings including GitHub action and CI/CD tool findings. |
| Container | Container related findings. See [Container policies](../../finding-policies/container-policies) for details. |
| GitHub Actions | GitHub Action dependency findings. See [GitHub Action policies](../../finding-policies/github-action-policies) for details. |
| License Risk | License related findings. See [License policies](../../finding-policies/license-policies) and [Open-source policies](../../finding-policies/oss-policies) for details. |
| Malware | Malware findings. |
| Operational | Umbrella category for operational issues including license risks, low dependency scores, outdated dependencies, recently released dependencies, unpinned dependencies, unreachable dependencies, unmaintained dependencies, and CI/CD findings. |
| RSPM | Repository security posture management (RSPM) related findings. See [RSPM policies](../../finding-policies/managing-scm-configuration) for details. |
| SAST | Static Application Security Testing (SAST) related findings. |
| SCA | Umbrella category for Software Composition Analysis (SCA) related findings for software packages and their dependencies. Does not include AI model, Container, or CI/CD findings. |
| Secrets | Findings for exposed secrets such as passwords or access tokens. See [Secret policies](../../finding-policies/secret-policies) for details. |
| Security | Umbrella category for security issues including vulnerabilities, malware, phantom dependency, missing source code, SAST, secrets, and typosquatting findings. |
| Supply Chain | Umbrella category for supply chain issues including malware, typosquatting, license risk, and AI model findings. |
| Vulnerability | Vulnerability findings. |

#### Finding types

Findings are classified into the following types when the packages scanned include:

| Type | Description |
| --- | --- |
| Custom | Custom findings defined in custom policies. |
| Dependency With Low Activity Score | Low Endor activity score. |
| Dependency With Low Popularity Score | Low Endor popularity score. |
| Dependency With Low Quality Score | Low Endor quality score. |
| Dependency With Multiple Low Scores | More than one Low Endor Score. |
| Dependency With Very Low Activity Scores | Very low Endor activity score. |
| Dependency With Very Low Popularity Score | Very low Endor popularity score. |
| Dependency With Very Low Quality Score | Very low Endor quality score. |
| License Risk | Missing, unknown, restricted, or problematic licenses. |
| Malware Dependency | Known malicious dependencies reported by Open Source Vulnerabilities (OSV). |
| Malware OSS Review | Potentially suspicious code that needs review. |
| Missing Source Code | Associated source code is not auditable. |
| Outdated Dependency | Outdated code with older versions of the released dependencies. |
| Recently Released Dependency | Dependencies with newer versions than the configured cooldown period. |
| Typosquatted Dependency | Dependencies with intentionally similar names to popular packages. |
| Unmaintained Dependency | Unmaintained dependencies introducing vulnerabilities. |
| Unpinned Dependency | Variable version specifications of dependencies. |
| Unused Dependency | Unused dependencies in the code. |

## Malware

Allows you to define the action policy to apply when a malware finding is detected, depending on its status, relationship to root packages, and ecosystem.

Allows you to define the action policy to apply when a malware finding is detected, depending on its status, relationship to root packages, and ecosystem.

The following table describes the parameters.

| Parameter | Description |
| --- | --- |
| Status | Select the status of malware finding such as **Malware** for confirmed malware, **Telemetry** if the package is not always malicious but may expose environment details, or **Unhealthy** if the package appears broken or non-functional. |
| Relationship | Select **Direct Dependency** to only match findings for direct dependencies, or **Transitive Dependency** to only match findings for transitive dependencies. |
| Ecosystem | Match finding ecosystem. |
| Exclude Test | Select **Yes** to exclude test dependencies from this policy. |
| Exclude Approximate | Select **Yes** to exclude approximate dependencies from this policy. |

## SAST

Allows you to define the action taken when a SAST finding is raised.

| Parameter | Description |
| --- | --- |
| Severity | Only match findings that have this severity level. |
| Confidence | Only match findings for SAST rules with this confidence level. |
| Language | Only match findings for this SAST result language. |
| SAST Tag | Only match findings that have this SAST tag. For example, `A01:2021` or `Cryptographic-Failures`. |
| Custom Tag | Only match findings that have this custom tag (set by the policy that created the finding or using the `--finding-tags` CLI option). Note that these are different and separate from the system-defined finding tags. |
| CWE | Only match findings with this CWE. For example, `CWE-123` or `CWE-456` (case insensitive). |
| File Scope | Only match findings with this file scope. For example, `Normal` or `Test`. |
| Include Path | Only match findings for files that match this glob style file pattern. For example, `src/golang/**`. |
| Exclude Path | Do not match findings for files that match this glob style file pattern. For example, `src/golang/**`. |
| Branch Type | Only match findings for this branch type. Set to **Default** to match findings for the default branch. Set to **Ref** to match findings for reference (non-default) branches. Set to **Pull Request** to match findings for pull requests. Note that the **Send Notification** action does not apply to pull requests, as notifications are only processed for monitored branches. |
| Code Owner | Only match findings with this code owner. For example, `@octocat` or `@octocat-team`. Case-insensitive exact matches only, no partial or approximate (fuzzy) matches. If a finding does not have a code owner, it is not matched by the policy. Code owners are automatically assigned to findings based on the `CodeOwners` object for the project, which is generated from the CODEOWNERS file in the default branch of the repository. For projects without a CODEOWNERS file, the `CodeOwners` object can be managed through the API. |

## SCA

Use these templates to define actions for Software Composition Analysis (SCA) findings, including vulnerabilities, outdated dependencies, unmaintained packages, license risks, and other issues in your open-source dependencies.

### Containers

Matches container findings for vulnerabilities that meet specific parameters.

The following table describes the parameters.

| Parameter | Description |
| --- | --- |
| Vulnerability ID | Full vulnerability identifier. For example, CVE-2024-3727 or GHSA-qh2h-chj9-jffq (case insensitive). |
| Severity | Only match findings with this severity. |
| Fix Availability | Select **Fix Available** to only match findings if a patch is available to fix the issue in the dependency. |
| Relationship | Select **Direct Dependency** to only match findings for direct dependencies, or **Transitive Dependency** to only match findings for transitive dependencies. |
| EPSS Percentile Threshold | Only match findings with an EPSS percentile threshold equal to or higher than this threshold (0.00-100.00). The EPSS percentile threshold represents the percentile ranking among all vulnerabilities that a vulnerability will be exploited. |
| EPSS Probability Threshold | Only match findings with an EPSS probability score equal to or higher than this threshold (0.00-1.00). The EPSS probability score represents the probability [0-1] of exploitation in the wild in the next 30 days following score publication. |
| Exploited | Only match findings for CVEs that are listed in the Known Exploited Vulnerabilities (KEV) database. |
| Ecosystem | Match finding ecosystem. |
| Exclude if Dependency Name Contains | Allows you to define full or partial dependency names for which an action policy should exclude. For example, you want to exclude a specific dependency from this policy. |
| Exclude if Package Name Contains | Allows you to define full or partial package names for which an action policy should exclude. This is the resource that the finding is raised against. For example, the package indirectly or directly includes an unmaintained dependency. |
| Exclude findings for transitive dependencies via other projects | Exclude findings for transitive dependencies that can only be reached through other projects. This helps your team to not act when they do not have control of findings introduced by libraries your team developed. |
| Branch Type | Only match findings for this branch type. Set to **Default** to match findings for the default branch. Set to **Ref** to match findings for reference (non-default) branches. Set to **Pull Request** to match findings for pull requests. Note that the **Send Notification** action does not apply to pull requests, as notifications are only processed for monitored branches. |

### Custom (Advanced)

Allows you to define a custom action policy based on the attributes of the finding.

The following table describes the parameters.

| Parameter | Description |
| --- | --- |
| Finding Name | Match full or partial finding name. |
| Category | Match finding category. |
| Type | Match finding type. |
| Severity | Match finding severity. |
| Fix Availability | Select **Fix Available** to only match findings if a patch is available to fix the issue in the dependency. |
| Relationship | Select **Direct Dependency** to only match findings for direct dependencies, or **Transitive Dependency** to only match findings for transitive dependencies. |
| Dependency Reachability | Select **Reachable Dependency** and **Potentially Reachable Dependency** to only match findings where the vulnerable dependency is reachable. |
| Function Reachability | Select **Reachable Function** and **Potentially Reachable Function** to only match findings where the vulnerable function is reachable. |
| Exclude Test | Select **Yes** to exclude test dependencies. |
| Ecosystem | Match finding ecosystem. |
| Custom Tag | Only match findings that have this custom tag (set by the policy that created the finding or using the `--finding-tags` CLI option). Note that these are different and separate from the system-defined finding tags. |
| Include Path | Only match findings for dependencies or files that match this glob style file pattern. For example, `src/golang/**`. |
| Exclude Path | Do not match findings for dependencies or files that match this glob style file pattern. For example, `src/golang/**`. |
| Exclude if Dependency Name Contains | Allows you to define full or partial dependency names for which an action policy should exclude. For example, you want to exclude a specific dependency from this policy. |
| Exclude if Package Name Contains | Allows you to define full or partial package names for which an action policy should exclude. This is the resource that the finding is raised against. For example, the package indirectly or directly includes an unmaintained dependency. |
| Exclude findings for transitive dependencies via other projects | Exclude findings for transitive dependencies that can only be reached through other projects. This helps your team to not act when they do not have control of findings introduced by libraries your team developed. |
| Include GitHub Action findings | Select **Yes** to include findings for GitHub action dependencies. |
| Include Container findings | Select **Yes** to include findings for container dependencies. |
| Branch Type | Only match findings for this branch type. Set to **Default** to match findings for the default branch. Set to **Ref** to match findings for reference (non-default) branches. Set to **Pull Request** to match findings for pull requests. Note that the **Send Notification** action does not apply to pull requests, as notifications are only processed for monitored branches. |
| Code Owner | Only match findings with this code owner. For example, `@octocat` or `@octocat-team`. Case-insensitive exact matches only, no partial or approximate (fuzzy) matches. If a finding does not have a code owner, it is not matched by the policy. Code owners are automatically assigned to findings based on the `CodeOwners` object for the project, which is generated from the CODEOWNERS file in the default branch of the repository. For projects without a CODEOWNERS file, the `CodeOwners` object can be managed through the API. |

### Malware

Allows you to define the action policy to apply when a malware finding is detected, depending on its status, relationship to root packages, and ecosystem.

The following table describes the parameters.

| Parameter | Description |
| --- | --- |
| Status | Select the status of malware finding such as **Malware** for confirmed malware, **Telemetry** if the package is not always malicious but may expose environment details, or **Unhealthy** if the package appears broken or non-functional. |
| Relationship | Select **Direct Dependency** to only match findings for direct dependencies, or **Transitive Dependency** to only match findings for transitive dependencies. |
| Ecosystem | Match finding ecosystem. |
| Exclude Test | Select **Yes** to exclude test dependencies from this policy. |
| Exclude Approximate | Select **Yes** to exclude approximate dependencies from this policy. |

### Outdated Releases

Matches findings based on older versions of software or dependencies and are not actively updated. The following parameters are supported:

| Parameter | Description |
| --- | --- |
| Relationship | Select **Direct Dependency** to only match findings for direct dependencies, or **Transitive Dependency** to only match findings for transitive dependencies. |
| Dependency Reachability | Select **Reachable Dependency** and **Potentially Reachable Dependency** to only match findings where the vulnerable dependency is reachable. |
| Exclude Test | Exclude test dependencies from this policy. |
| Ecosystem | Match finding ecosystem. |
| Exclude if Dependency Name Contains | Allows you to define full or partial dependency names for which an action policy should exclude. For example, you want to exclude a specific dependency from this policy. |
| Exclude if Package Name Contains | Allows you to define full or partial package names for which an action policy should exclude. This is the resource that the finding is raised against. For example, the package indirectly or directly includes an unmaintained dependency. |
| Exclude findings for transitive dependencies via other projects | Exclude findings for transitive dependencies that can only be reached through other projects. This helps your team to not act when they do not have control of findings introduced by libraries your team developed. |

### Recently Released Dependencies (cooldown)

Matches findings for recently released dependencies. Supported configuration parameters for this action policy template are:

| Parameter | Description |
| --- | --- |
| Ecosystem | Match finding ecosystem. |
| Exclude Test | Exclude test dependencies from this policy. |
| Exclude if Dependency Name Contains | Allows you to define full or partial dependency names for which an action policy should exclude. For example, you want to exclude a specific dependency from this policy. |
| Exclude if Package Name Contains | Allows you to define full or partial package names for which an action policy should exclude. This is the resource that the finding is raised against. For example, the package indirectly or directly includes an unmaintained dependency. |
| Exclude findings for transitive dependencies via other projects | Exclude findings for transitive dependencies that can only be reached through other projects. This helps your team to not act when they do not have control of findings introduced by libraries your team developed. |
| Branch Type | Only match findings for this branch type. Set to **Default** to match findings for the default branch. Set to **Ref** to match findings for reference (non-default) branches. Set to **Pull Request** to match findings for pull requests. Note that the **Send Notification** action does not apply to pull requests, as notifications are only processed for monitored branches. |

### Unmaintained Dependencies

Matches findings based on dependencies that are no longer maintained or may have reached end-of-life. The following parameters are supported:

| Parameter | Description |
| --- | --- |
| Relationship | Select **Direct Dependency** to only match findings for direct dependencies, or **Transitive Dependency** to only match findings for transitive dependencies. |
| Dependency Reachability | Select **Reachable Dependency** and **Potentially Reachable Dependency** to only match findings where the vulnerable dependency is reachable. |
| Exclude Test | Exclude test dependencies from this policy. |
| Ecosystem | Match finding ecosystem. |
| Exclude if Dependency Name Contains | Allows you to define full or partial dependency names for which an action policy should exclude. For example, you want to exclude a specific dependency from this policy. |
| Exclude if Package Name Contains | Allows you to define full or partial package names for which an action policy should exclude. This is the resource that the finding is raised against. For example, the package indirectly or directly includes an unmaintained dependency. |
| Exclude findings for transitive dependencies via other projects | Exclude findings for transitive dependencies that can only be reached through other projects. This helps your team to not act when they do not have control of findings introduced by libraries your team developed. |

### Unpinned Direct Dependencies

Matches findings based on direct dependencies that do not have a version or a range of versions specified. Supported configuration parameters for this action policy template are:

| Parameter | Description |
| --- | --- |
| Exclude Test | Exclude test dependencies from this policy. |
| Ecosystem | Match finding ecosystem. |
| Exclude if Dependency Name Contains | Allows you to define full or partial dependency names for which an action policy should exclude. For example, you want to exclude a specific dependency from this policy. |
| Exclude if Package Name Contains | Allows you to define full or partial package names for which an action policy should exclude. This is the resource that the finding is raised against. For example, the package indirectly or directly includes an unmaintained dependency. |
| Exclude findings for transitive dependencies via other projects | Exclude findings for transitive dependencies that can only be reached through other projects. This helps your team to not act when they do not have control of findings introduced by libraries your team developed. |

### Unreachable Direct Dependencies

Matches findings based on dependencies that are not directly used or called within a project. Supported configuration parameters for this action policy template are:

| Parameter | Description |
| --- | --- |
| Exclude Test | Exclude test dependencies from this policy. |
| Ecosystem | Match finding ecosystem. |
| Exclude if Dependency Name Contains | Allows you to define full or partial dependency names for which an action policy should exclude. For example, you want to exclude a specific dependency from this policy. |
| Exclude if Package Name Contains | Allows you to define full or partial package names for which an action policy should exclude. This is the resource that the finding is raised against. For example, the package indirectly or directly includes an unmaintained dependency. |
| Exclude findings for transitive dependencies via other projects | Exclude findings for transitive dependencies that can only be reached through other projects. This helps your team to not act when they do not have control of findings introduced by libraries your team developed. |

### Vulnerabilities

Matches findings that are vulnerabilities that meet specific parameters.

The following table describes the parameters.

| Parameter | Description |
| --- | --- |
| Vulnerability ID | Full vulnerability identifier. For example, `CVE-2024-3727` or `GHSA-qh2h-chj9-jffq` (case insensitive). |
| Severity | Only match findings with this severity. |
| Fix Availability | Select **Fix Available** to only match findings if a patch is available to fix the issue in the dependency. |
| Relationship | Select **Direct Dependency** to only match findings for direct dependencies, or **Transitive Dependency** to only match findings for transitive dependencies. |
| Dependency Reachability | Select **Reachable Dependency** and **Potentially Reachable Dependency** to only match findings where the vulnerable dependency is reachable. |
| Function Reachability | Select **Reachable Function** and **Potentially Reachable Function** to only match findings where the vulnerable function is reachable. |
| Exclude Test | Select **Yes** to exclude test dependencies from this policy. |
| EPSS Percentile Threshold | Only match findings with an EPSS percentile threshold equal to or higher than this threshold (0.00–100.00). The EPSS percentile threshold represents the percentile ranking among all vulnerabilities that a vulnerability will be exploited. |
| EPSS Probability Threshold | Only match findings with an EPSS probability score equal to or higher than this threshold (0.00–1.00). The EPSS probability score represents the probability [0–1] of exploitation in the wild in the next 30 days following score publication. |
| Exploited | Only match findings for CVEs that are listed in the Known Exploited Vulnerabilities (KEV) database. |
| Ecosystem | Match finding ecosystem. |
| Exclude if Dependency Name Contains | Allows you to define full or partial dependency names for which an action policy should exclude. For example, you want to exclude a specific dependency from this policy. |
| Exclude if Package Name Contains | Allows you to define full or partial package names for which an action policy should exclude. This is the resource that the finding is raised against. For example, the package indirectly or directly includes an unmaintained dependency. |
| Exclude findings for transitive dependencies via other projects | Exclude findings for transitive dependencies that can only be reached through other projects. This helps your team to not act when they do not have control of findings introduced by libraries your team developed. |
| Include GitHub Action findings | Select **Yes** to include findings for GitHub action dependencies. |
| Include Container findings | Select **Yes** to include findings for container dependencies. |
| Branch Type | Only match findings for this branch type. Set to **Default** to match findings for the default branch. Set to **Ref** to match findings for reference (non-default) branches. Set to **Pull Request** to match findings for pull requests. Note that the **Send Notification** action does not apply to pull requests, as notifications are only processed for monitored branches. |
| Code Owner | Only match findings with this code owner. For example, `@octocat` or `@octocat-team`. Case-insensitive exact matches only, no partial or approximate (fuzzy) matches. If a finding does not have a code owner, it is not matched by the policy. Code owners are automatically assigned to findings based on the `CodeOwners` object for the project, which is generated from the CODEOWNERS file in the default branch of the repository. For projects without a CODEOWNERS file, the `CodeOwners` object can be managed through the API. |

## Secrets

Allows you to define the action taken when a leaked secret is detected based on the validation status of the secret.

| Parameter | Description |
| --- | --- |
| Validation Status | Select secret validation status: **Valid**, **Invalid**, or **Unable to Validate**. |
| Custom Tag | Only match findings that have this custom tag (set by the policy that created the finding or using the `--finding-tags` CLI option). Note that these are different and separate from the system-defined finding tags. |
| Include Path | Only match findings for files that match this glob style file pattern. For example, `src/golang/**`. |
| Exclude Path | Do not match findings for files that match this glob style file pattern. For example, `src/golang/**`. |
| Code Owner | Only match findings with this code owner. For example, `@octocat` or `@octocat-team`. Case-insensitive exact matches only, no partial or approximate (fuzzy) matches. If a finding does not have a code owner, it is not matched by the policy. Code owners are automatically assigned to findings based on the `CodeOwners` object for the project, which is generated from the CODEOWNERS file in the default branch of the repository. For projects without a CODEOWNERS file, the `CodeOwners` object can be managed through the API. |

## Security Review

Use these templates to define actions for security review findings that require manual assessment or additional analysis before taking action.

Match security review findings. The following parameters are supported:

| Parameter | Description |
| --- | --- |
| Severity | Only match findings with this severity. |
| Branch Type | Only match findings for this branch type. Set to **Default** to match findings for the default branch. Set to **Ref** to match findings for reference (non-default) branches. Set to **Pull Request** to match findings for pull requests. Note that the **Send Notification** action does not apply to pull requests, as notifications are only processed for monitored branches. |

## Vulnerabilities

Use these templates to define actions for vulnerability findings, including CVEs, security advisories, and known exploits in your dependencies based on severity, exploitability, and fix availability.

### Containers

Matches container findings for vulnerabilities that meet specific parameters.

The following table describes the parameters.

| Parameter | Description |
| --- | --- |
| Vulnerability ID | Full vulnerability identifier. For example, CVE-2024-3727 or GHSA-qh2h-chj9-jffq (case insensitive). |
| Severity | Only match findings with this severity. |
| Fix Availability | Select **Fix Available** to only match findings if a patch is available to fix the issue in the dependency. |
| Relationship | Select **Direct Dependency** to only match findings for direct dependencies, or **Transitive Dependency** to only match findings for transitive dependencies. |
| EPSS Percentile Threshold | Only match findings with an EPSS percentile threshold equal to or higher than this threshold (0.00-100.00). The EPSS percentile threshold represents the percentile ranking among all vulnerabilities that a vulnerability will be exploited. |
| EPSS Probability Threshold | Only match findings with an EPSS probability score equal to or higher than this threshold (0.00-1.00). The EPSS probability score represents the probability [0-1] of exploitation in the wild in the next 30 days following score publication. |
| Exploited | Only match findings for CVEs that are listed in the Known Exploited Vulnerabilities (KEV) database. |
| Ecosystem | Match finding ecosystem. |
| Exclude if Dependency Name Contains | Allows you to define full or partial dependency names for which an action policy should exclude. For example, you want to exclude a specific dependency from this policy. |
| Exclude if Package Name Contains | Allows you to define full or partial package names for which an action policy should exclude. This is the resource that the finding is raised against. For example, the package indirectly or directly includes an unmaintained dependency. |
| Exclude findings for transitive dependencies via other projects | Exclude findings for transitive dependencies that can only be reached through other projects. This helps your team to not act when they do not have control of findings introduced by libraries your team developed. |
| Branch Type | Only match findings for this branch type. Set to **Default** to match findings for the default branch. Set to **Ref** to match findings for reference (non-default) branches. Set to **Pull Request** to match findings for pull requests. Note that the **Send Notification** action does not apply to pull requests, as notifications are only processed for monitored branches. |

### Custom (Advanced)

Allows you to define a custom action policy based on the attributes of the finding.

The following table describes the parameters.

| Parameter | Description |
| --- | --- |
| Finding Name | Match full or partial finding name. |
| Category | Match finding category. |
| Type | Match finding type. |
| Severity | Match finding severity. |
| Fix Availability | Select **Fix Available** to only match findings if a patch is available to fix the issue in the dependency. |
| Relationship | Select **Direct Dependency** to only match findings for direct dependencies, or **Transitive Dependency** to only match findings for transitive dependencies. |
| Dependency Reachability | Select **Reachable Dependency** and **Potentially Reachable Dependency** to only match findings where the vulnerable dependency is reachable. |
| Function Reachability | Select **Reachable Function** and **Potentially Reachable Function** to only match findings where the vulnerable function is reachable. |
| Exclude Test | Select **Yes** to exclude test dependencies. |
| Ecosystem | Match finding ecosystem. |
| Custom Tag | Only match findings that have this custom tag (set by the policy that created the finding or using the `--finding-tags` CLI option). Note that these are different and separate from the system-defined finding tags. |
| Include Path | Only match findings for dependencies or files that match this glob style file pattern. For example, `src/golang/**`. |
| Exclude Path | Do not match findings for dependencies or files that match this glob style file pattern. For example, `src/golang/**`. |
| Exclude if Dependency Name Contains | Allows you to define full or partial dependency names for which an action policy should exclude. For example, you want to exclude a specific dependency from this policy. |
| Exclude if Package Name Contains | Allows you to define full or partial package names for which an action policy should exclude. This is the resource that the finding is raised against. For example, the package indirectly or directly includes an unmaintained dependency. |
| Exclude findings for transitive dependencies via other projects | Exclude findings for transitive dependencies that can only be reached through other projects. This helps your team to not act when they do not have control of findings introduced by libraries your team developed. |
| Include GitHub Action findings | Select **Yes** to include findings for GitHub action dependencies. |
| Include Container findings | Select **Yes** to include findings for container dependencies. |
| Branch Type | Only match findings for this branch type. Set to **Default** to match findings for the default branch. Set to **Ref** to match findings for reference (non-default) branches. Set to **Pull Request** to match findings for pull requests. Note that the **Send Notification** action does not apply to pull requests, as notifications are only processed for monitored branches. |
| Code Owner | Only match findings with this code owner. For example, `@octocat` or `@octocat-team`. Case-insensitive exact matches only, no partial or approximate (fuzzy) matches. If a finding does not have a code owner, it is not matched by the policy. Code owners are automatically assigned to findings based on the `CodeOwners` object for the project, which is generated from the CODEOWNERS file in the default branch of the repository. For projects without a CODEOWNERS file, the `CodeOwners` object can be managed through the API. |

### Vulnerabilities

Matches findings that are vulnerabilities that meet specific parameters.

The following table describes the parameters.

| Parameter | Description |
| --- | --- |
| Vulnerability ID | Full vulnerability identifier. For example, `CVE-2024-3727` or `GHSA-qh2h-chj9-jffq` (case insensitive). |
| Severity | Only match findings with this severity. |
| Fix Availability | Select **Fix Available** to only match findings if a patch is available to fix the issue in the dependency. |
| Relationship | Select **Direct Dependency** to only match findings for direct dependencies, or **Transitive Dependency** to only match findings for transitive dependencies. |
| Dependency Reachability | Select **Reachable Dependency** and **Potentially Reachable Dependency** to only match findings where the vulnerable dependency is reachable. |
| Function Reachability | Select **Reachable Function** and **Potentially Reachable Function** to only match findings where the vulnerable function is reachable. |
| Exclude Test | Select **Yes** to exclude test dependencies from this policy. |
| EPSS Percentile Threshold | Only match findings with an EPSS percentile threshold equal to or higher than this threshold (0.00–100.00). The EPSS percentile threshold represents the percentile ranking among all vulnerabilities that a vulnerability will be exploited. |
| EPSS Probability Threshold | Only match findings with an EPSS probability score equal to or higher than this threshold (0.00–1.00). The EPSS probability score represents the probability [0–1] of exploitation in the wild in the next 30 days following score publication. |
| Exploited | Only match findings for CVEs that are listed in the Known Exploited Vulnerabilities (KEV) database. |
| Ecosystem | Match finding ecosystem. |
| Exclude if Dependency Name Contains | Allows you to define full or partial dependency names for which an action policy should exclude. For example, you want to exclude a specific dependency from this policy. |
| Exclude if Package Name Contains | Allows you to define full or partial package names for which an action policy should exclude. This is the resource that the finding is raised against. For example, the package indirectly or directly includes an unmaintained dependency. |
| Exclude findings for transitive dependencies via other projects | Exclude findings for transitive dependencies that can only be reached through other projects. This helps your team to not act when they do not have control of findings introduced by libraries your team developed. |
| Include GitHub Action findings | Select **Yes** to include findings for GitHub action dependencies. |
| Include Container findings | Select **Yes** to include findings for container dependencies. |
| Branch Type | Only match findings for this branch type. Set to **Default** to match findings for the default branch. Set to **Ref** to match findings for reference (non-default) branches. Set to **Pull Request** to match findings for pull requests. Note that the **Send Notification** action does not apply to pull requests, as notifications are only processed for monitored branches. |
| Code Owner | Only match findings with this code owner. For example, `@octocat` or `@octocat-team`. Case-insensitive exact matches only, no partial or approximate (fuzzy) matches. If a finding does not have a code owner, it is not matched by the policy. Code owners are automatically assigned to findings based on the `CodeOwners` object for the project, which is generated from the CODEOWNERS file in the default branch of the repository. For projects without a CODEOWNERS file, the `CodeOwners` object can be managed through the API. |

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
