---
url: https://docs.endorlabs.com/managing-policies/exception-policies/templates/
title: Exception policy templates | Endor Labs Docs
downloaded: 2025-10-23 23:24:54
---

Exception policy templates | Endor Labs Docs



* Type to search...
* ---

[Print entire section](/managing-policies/exception-policies/templates/_print.html)



# Exception policy templates

Learn about the predefined exception policy templates and how to customize them.

Endor Labs provides the following exception policy templates that you can use to quickly create exception policies. Each exception policy template provides parameters to help you customize the conditions under which an exception is applied.

## Common

Define exceptions for common use cases such as:

* Exclude a specific finding, for a specific package, for a specific dependency.
* Exclude all findings for a specific dependency.
* Exclude all findings for a specific package.
* Exclude all vulnerabilities that do not have a patch available.

The following table describes the parameters for the common exception policy template.

| Parameter | Description |
| --- | --- |
| Vulnerability ID | The vulnerability identifier. For example, `CVE-2024-3727 or GHSA-qh2h-chj9-jffq` (case insensitive). |
| Finding Name | Match full or partial finding name. |
| Dependency Name | Match full or partial dependency name. |
| Package Name | Match full or partial package name. Do not specify a package version if you want the exception to apply to multiple versions of the package. |
| Fix Availability | Select **Fix Not Available** to apply the exception if a patch is not available for the dependency. |

## Custom (advanced)

Define exceptions based on custom criteria that are less common for findings. For example, you can exclude all findings generated based on approximate scans for a specific ecosystem.

The following table describes the parameters for the custom exception policy template.

| Parameter | Description |
| --- | --- |
| Vulnerability ID | The vulnerability identifier. For example, `CVE-2024-3727` or `GHSA-qh2h-chj9-jffq` (case insensitive). |
| Finding Name | Match full or partial finding name. |
| Dependency Name | Match full or partial dependency name. |
| Package Name | Match full or partial package name. Do not specify a package version here if you want the exception to apply to multiple versions of the package. |
| Fix Availability | Select **Fix Not Available** to apply the exception if a patch is not available for the dependency. |
| Category | Match finding category. |
| Type | Match [finding type](../../action-policies/templates/#finding-types). |
| Severity | Match finding severity. |
| Relationship | Select **Direct Dependency** to only match findings for direct dependencies, or **Transitive Dependency** to only match findings for transitive dependencies. |
| Dependency Reachability | Match findings based on the reachability of the vulnerable dependency. Select **Unreachable Dependency** to match findings where the vulnerable dependency is not reachable, **Reachable Dependency** to match findings where the vulnerable dependency is reachable, and **Potentially Reachable Dependency** to match findings where the vulnerable dependency is potentially reachable. You can choose any combination of these options. Be aware that the more options you select, the more exceptions you will create. This might result in the exclusion of important findings. |
| Function Reachability | Match findings based on the reachability of the vulnerable function. Select **Unreachable Function** to match findings where the vulnerable function is not reachable, **Reachable Function** to match findings where the vulnerable function is reachable, and **Potentially Reachable Function** to match findings where the vulnerable function is potentially reachable. Be aware that the more options you select, the more exceptions you will create. This might result in the exclusion of important findings. |
| Ecosystem | Match finding ecosystem. |
| Custom Tag | Apply exceptions to findings with this meta tag, set by the policy that generated the finding or with the `--finding-tags` CLI option. These tags are different and separate from the system defined finding tags. |
| File Path | Only match findings for dependencies or files that match this glob style file pattern. For example, `src/golang/**`. |
| Dependency Scope | Match findings based on the scope of the dependency. Select **Normal** to match findings generated for dependencies essential for the primary operation of the application, and used in a production environment. Select **Test** to match findings for dependencies required for testing purposes, such as testing frameworks and libraries not used in a production environment. You can choose either option or both. |
| Approximate Dependency | Select **Yes** to match findings that have been generated based on approximate scans. |

## Malware

Define exceptions for malware findings.

| Parameter | Description |
| --- | --- |
| Malware ID | The malware identifier. For example, `MAL-2025-2422` or `GHSA-pfwm-66hm-9h5r` or `SNYK-JS-TFJSLAYERS-9406475` (case insensitive). |
| Status | Select the status of malware finding such as **Malware** for confirmed malware, **Telemetry** if the package is not always malicious but may expose environment details, or **Unhealthy** if the package appears broken or non-functional. |
| Ecosystem | Match finding ecosystem. |
| Dependency Name | Match full or partial dependency name. |
| Dependency Scope | Match findings based on the scope of the dependency. Select **Normal** to match findings generated for dependencies essential for the primary operation of the application, and used in a production environment. Select **Test** to match findings for dependencies required for testing purposes, such as testing frameworks and libraries not used in a production environment. You can choose either option or both. |
| Exclude Approximate | Select **Yes** to match findings that are generated based on approximate scans. |

## SAST

Define exceptions for SAST findings.

| Parameter | Description |
| --- | --- |
| Rule Name | Full name of the rule. For example, `Insecure cookie-based authentication` (case insensitive). |
| SAST Tag | Only match findings with this SAST tag. For example, `A02:2021` or `OWASP-Top-10` (case insensitive). |
| Custom Tag | Only match findings with this meta tag, set by the policy that generated the finding or with the `--finding-tags` CLI option. These tags are different and separate from the system defined finding tags. |
| CWE | Only match findings with this CWE. For example, `CWE-123` or `CWE-456` (case insensitive). |
| File Scope | Only match findings with this file scope. For example, `Normal` or `Test`. |
| File Path | Only match findings for files that match this glob style file pattern. For example, `src/golang/**`. |

## Secrets

Define exceptions for secrets findings.

| Parameter | Description |
| --- | --- |
| Validation Status | Select secret validation status: **Valid**, **Invalid**, or **Unable to Validate**. |
| Custom Tag | Only match findings with this custom tag, set by the policy that generated the finding or with the `--finding-tags` CLI option. These tags are different and separate from the system defined finding tags. |
| File Path | Only match findings for files that match this glob style file pattern. For example, `src/golang/**`. |

## Vulnerabilities

Define exceptions for vulnerabilities findings.

| Parameter | Description |
| --- | --- |
| Vulnerability ID | The vulnerability identifier. For example, `CVE-2024-3727 or GHSA-qh2h-chj9-jffq` (case insensitive). |
| Fix Availability | Select **Fix Not Available** to apply the exception if a patch is not available for the dependency. |
| Severity | Match finding severity. |
| Relationship | Select **Direct Dependency** to only match findings for direct dependencies, or **Transitive Dependency** to only match findings for transitive dependencies. |
| Dependency Scope | Match findings based on the scope of the dependency. Select **Normal** to match findings generated for dependencies essential for the primary operation of the application, and used in a production environment. Select **Test** to match findings for dependencies required for testing purposes, such as testing frameworks and libraries not used in a production environment. You can choose either option or both. |
| Approximate Dependency | Select **Yes** to match findings that have been generated based on approximate scans. |

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
