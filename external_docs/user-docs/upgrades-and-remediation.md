---
url: https://docs.endorlabs.com/upgrades-and-remediation/
title: Upgrades and remediation | Endor Labs Docs
downloaded: 2025-11-20 11:51:27
---

Upgrades and remediation | Endor Labs Docs



* Type to search...
* ---

[Print entire section](/upgrades-and-remediation/_print.html)



# Upgrades and remediation

Learn how Endor Labs helps address security vulnerabilities through strategic software updates and patches.

Software security teams face the challenge of managing thousands of dependencies across multiple projects, each with their own vulnerability landscape and upgrade requirements. Most vulnerabilities can be resolved through version upgrades which require careful analysis of compatibility, breaking changes, and dependency conflicts.

Endor Labs provides automated upgrade analysis and remediation capabilities that transform vulnerability management from reactive issue identification to proactive, action-based risk resolution. The platform analyzes entire dependency trees to identify optimal upgrade paths and generates specific remediation recommendations using the following two key components:

[**Upgrade Impact Analysis**](./upgrade-impact-analysis/) identifies and recommends upgrades for your dependencies. By pinpointing the distinct actions that can resolve your vulnerabilities and mitigate the risks associated with updates, your security program can make more informed risk management decisions and triage issues more effectively.

[**Endor Patches**](./using-endor-patches/) provide backported security fixes to your packages, allowing you to minimize the impact of software updates. You can update the libraries with a minimally viable security patch that reduces the risks of breaking changes, bugs, or performance issues associated with an upgrade.

[**Remediation PRs in GitHub App**](./pr-remediation/) automatically generate pull requests with dependency upgrades and security fixes directly in GitHub development workflows. This capability integrates remediation recommendations into existing CI/CD processes, enabling teams to review and merge security fixes through standard code review workflows.

#### Maximum number of remediation PRs

Endor Labs creates a maximum of 20 remediation PRs per project through the GitHub App integration.

The following diagram demonstrates an example of a vulnerability prioritization process performed by security teams:

![Vulnerability Prioritization](../images/vuln_prioritization.png)

### Remediation support matrix

The following table describes the level of remediation support available for different languages.

| Language | Upgrade recommendations | Identify remediation risk for conflicts | Identify remediation risk for breaking changes |
| --- | --- | --- | --- |
| Python | ✓ | ✓ | ✓ |
| Java | ✓ | ✓ | ✓ |
| .NET (C#) | ✓ | ✓ | ✓ |
| Scala | ✓ | ✓ | ✓ |
| Kotlin | ✓ | ✓ | ✓ |
| Ruby | ✓ | ✓ | ✗ |
| Golang | ✓ | ✓ | ✗ |
| PHP | ✓ | ✓ | ✗ |
| Swift/Objective-C | ✓ | ✓ | ✗ |
| JavaScript | ✓ | ✓ | ✗ |
| Rust | ✓ | ✓ | ✗ |

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
