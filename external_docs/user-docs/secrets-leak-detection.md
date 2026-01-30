---
url: https://docs.endorlabs.com/secrets-leak-detection/
title: Detect secret leaks | Endor Labs Docs
downloaded: 2026-01-26 10:09:09
---

Detect secret leaks | Endor Labs Docs



* Type to search...

[Print entire section](/secrets-leak-detection/_print.html)



# Detect secret leaks

Detect and triage leaked secrets and credentials.

Secrets are access credentials that provide access to key resources and services, such as passwords, API keys, and personal access tokens. Attackers can target vulnerabilities in places where secret information is readily accessible to many users, with the goal of gaining unauthorized entry to the services that these secrets unlock.

The exploitation of secrets can lead to various detrimental outcomes, including:

* Data breaches through the theft of stolen secrets and credentials.
* Unauthorized access to data and resources.
* Financial losses due to fraudulent activities.
* Privacy violations due to compromised credentials.
* Legal implications and regulatory consequences.

Secret scanning helps organizations proactively identify and remediate potential security threats before they can be exploited. It is important to scan for secrets in code as developers can sometimes hard-code sensitive data such as personal access tokens or API keys directly into the code.

The following sections describe how you can scan for secrets with Endor Labs:

* [Secret Rules](../secrets-leak-detection/secret-rules/): Create and manage secret rules to scan and detect secrets.
* [Scan for Secrets](../secrets-leak-detection/scan-secrets/): Scan your codebase for secrets.
* [View secret findings](../secrets-leak-detection/view-secret-findings/): View your findings after running a secrets scan.

## Benefits of secret scanning

Endor Labs scans your source code repositories for secrets so that your teams can proactively manage the potential exposure of secrets to a broader audience than their intended recipients.

Secret scanning helps you to:

* View findings for secrets exposed in the code and take corrective action.
* Detect valid secrets in your code repositories so that you can take immediate corrective action.
* Perform regular scans to audit and get visibility into secrets that may represent security exposures in your environment.
* Detect and view invalid secrets as a proactive security approach to audit your codebase and segregate findings that you do not need to focus on.
* Use Git pre-commit hooks to detect secrets before being committed.

## Secrets deduplication

Duplicate secrets increase the attack surface and the risk of unauthorized access. Managing multiple duplicate secrets can be complex and error-prone. Endor Labs intelligently categorizes instances of identical secrets found within your application components and repositories, helping an organization achieve:

* **Efficient prioritization**: Simplifies the prioritization of widely dispersed secrets, as more occurrences signify increased exposure and risk.
* **Comprehensive visibility**: Ensures that you have a comprehensive view of all instances associated with a specific secret, facilitating effective management when the secret is discovered or undergoes changes.
* **Optimize issue handling**: Generate a single finding for multiple secrets with details, simplifying the task of managing and addressing multiple secret-related issues simultaneously.

## Incremental secret scans

You can use the `--pr-incremental` flag to perform an [incremental scan](../scan-with-endorlabs/pr-scans/#perform-incremental-pr-scan) on your pull requests or merge requests to detect secret leaks. In [monitoring scans](../deployment/monitoring-scans/), incremental scans are done by default for PR scans. Incremental scans are content-based scans. The scan detects the modified files in the diff with the baseline branch. It then performs a text-level diff between the modified file and the file in the baseline branch. Only new or changed code segments are analyzed for secrets.

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
