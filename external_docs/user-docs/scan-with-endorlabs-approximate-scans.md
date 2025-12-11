---
url: https://docs.endorlabs.com/scan-with-endorlabs/approximate-scans/
title: Approximate scans | Endor Labs Docs
downloaded: 2025-12-11 11:35:46
---

Approximate scans | Endor Labs Docs



* Type to search...
* ---

[Print entire section](/scan-with-endorlabs/approximate-scans/_print.html)



# Approximate scans

Learn about approximate scans in Endor Labs

Endor Labs performs an approximate scan in situations where dependency resolution is impossible. This can happen due to build errors or incomplete dependency information. In such cases, an approximate scan estimates dependencies based on the available, unresolved dependency data.

Since an approximate scan relies on unresolved dependency information, it is not as accurate as a scan based on resolved dependency information. However, an approximate scan can still provide valuable insights and help you identify potential issues.

## How an approximate scan works

The approximate scan looks at the unresolved dependency data and estimates the resolved version based on the information available.

For example, if the version is pinned then the approximate scan uses that version. If the version is not specified, then it uses the latest version. The scan generates the findings based on these approximations.

False positives can occur if the actual resolved version is different from the approximated version, or if the same dependency is included in multiple places.

**Warning**

Endor Labs automatically performs an approximate scan if full dependency resolution fails. You cannot disable approximate scans, and you cannot initiate an approximate scan manually.

Review the scan logs to identify the root cause of the dependency resolution failures that resulted in the approximate scan. See [Scan History](../../managing-projects/scan-history) for more information on investigating previous scans and dependency resolution errors. You can also use the `--droid-gpt` / `ENDOR_SCAN_DROID_GPT` option with the endorctl scan command or the GitHub App to get analysis and recommendations from [DroidGPT](../../ai/droidgpt/) regarding the scan failures. See [Enable DroidGPT error logging](../../ai/droidgpt/#Enable-DroidGPT-error-logging) for more information about DroidGPT error logging.

## Ignore findings from approximate scans

If you know the approximate scan is inaccurate and want to ignore the findings, add an [exception policy](../../managing-policies/exception-policies/).

See [create an exception policy from a template](../../managing-policies/exception-policies/#create-an-exception-policy-from-a-template) for details on how to create an exception policy.

When you create the exception policy, choose the following options:

* Select **Custom** as the policy template when you **Define Exception Criteria**.
* Select **Yes** for the **Approximate Dependency** option.

You can refine the exception policy by adding more criteria like **Source Code Ecosystem** and **Dependency Scope**. See [custom exception policy template](../../managing-policies/exception-policies/templates/#custom-exception-policy-template) for more information on the fields you can use to refine the exception policy. Alternatively, you can create your own exception policy [from scratch](../../managing-policies/exception-policies/).

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
