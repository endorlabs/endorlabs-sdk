---
url: https://docs.endorlabs.com/managing-policies/finding-policies/oss-policies/
title: Open-source policies | Endor Labs Docs
downloaded: 2025-12-11 11:33:23
---

Open-source policies | Endor Labs Docs



* Type to search...
* ---

[Print entire section](/managing-policies/finding-policies/oss-policies/_print.html)



# Open-source policies

Learn about the out-of-the-box finding policies for open source risk management.

Open source risk policies generally fall into one of several categories:

* Vulnerabilities - Known vulnerabilities associated with a software component.
* Operational Risk - Issues that may make it more expensive to address any application impacting bug, including a security vulnerability.
* License Risk - Issues that may cause legal or compliance risk associated with your software.

## Policies for open source risk management

Endor Labs comes with the following out-of-the-box finding policies to detect open source risks.
See [Finding Policies](..) for details on how to **enable** or **disable** out-of-the-box policies.

| Policy | Description | Severity |
| --- | --- | --- |
| Malware | Malicious software in dependencies pose significant security risks to your applications and infrastructure. Raise findings for packages containing known malware or suspicious code patterns that may indicate malicious intent. | Critical |
| Vulnerabilities | Vulnerabilities indicate security weaknesses or flaws in the dependencies used by a software project. They can pose risks to the overall security and stability of a project. Raises findings for projects where vulnerabilities are detected. | Critical |
| Flag Phantom Dependencies | Raises findings for dependencies that are used in source code but not declared in the package’s manifest files. These dependencies are called phantom dependencies and are detected during deep scans. They are not detected during a `--quick-scan`. | Medium |
| License Risks | Raises findings for dependencies where the repository is either missing a license or has license related problems, for example multiple conflicting licenses. | Medium |
| Outdated Dependencies | Outdated dependencies are software libraries, frameworks, or modules that are being used in a project but have newer versions available. They are usually superseded by newer releases that offer bug fixes, security patches, improved functionality, or better performance. Raises findings for projects with outdated software libraries, frameworks, or modules. | Medium |
| Recently Released Dependencies | Recent releases of dependencies are more likely to introduce supply chain risk and breaking changes. Raise findings for dependencies with releases that are newer than the given threshold, or “cooldown” period (default: 48 hours). | Medium |
| Unmaintained Dependencies | Unmaintained dependencies refer to external libraries, frameworks, or modules that are no longer actively maintained or supported by their developers. These dependencies may have reached end-of-life, without updates, bug fixes, security patches, or any form of support. Raises findings for projects with unmaintained packages. | Medium |
| Unpinned Direct Dependencies | Unpinned direct dependencies indicate the absence of a specific version or range of versions for a dependency. This can lead to potential issues because different versions of dependencies may introduce changes, bug fixes, or even breaking changes, which can impact the project’s behavior or stability. Raises findings for projects with unpinned dependencies. | Medium |
| Unused Direct Dependencies | Unused direct dependencies are listed in a project’s configuration or dependency file and are not utilized or referenced in the project’s source code. Raise findings for projects with unused direct dependencies. | Medium |
| Low Endor Activity Scores | Projects with low Endor Labs activity scores are less likely to be kept up to date. They are susceptible to software bugs and security risks. Raise findings for packages with low Endor Labs activity scores. | Low |
| Missing Source Code | If you cannot audit the source code associated with a software component, there is limited visibility that can result in operational and security risks. Raises findings for packages with missing source code. | Low |
| Low Endor Quality Scores | Projects with low Endor Labs quality scores are highly likely to be susceptible to security and operational risks. Raise findings for packages with low Endor Labs quality scores. | Low |
| Potential Typosquats | Typosquat is a malicious practice where a domain name closely resembles popular or legitimate domain names but contains typographical errors. This can deceive or exploit users who make mistakes while typing the intended website’s URL or package name. Raises findings for packages that contain potential typosquats. | Low |
| Low Endor Popularity Scores | A popularity score indicates how well the software component is being used by developers. Raise findings for repositories that have low popularity scores. | Low |

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
