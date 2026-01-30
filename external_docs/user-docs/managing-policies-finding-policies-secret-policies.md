---
url: https://docs.endorlabs.com/managing-policies/finding-policies/secret-policies/
title: Secret policies | Endor Labs Docs
downloaded: 2026-01-26 10:07:40
---

Secret policies | Endor Labs Docs



* Type to search...

[Print entire section](/managing-policies/finding-policies/secret-policies/_print.html)



# Secret policies

Learn about the out-of-the-box finding policies and templates for secret detection.

## Policies for secret detection

Endor Labs comes with the following out-of-the-box finding policies to detect leaked secrets.
See [Finding Policies](..) for details on how to **enable**, **disable**, or **edit** out-of-the-box policies.

**Note**

Note: The out-of-the-box secret policies can be deleted and re-created from the corresponding policy templates. See [Policy templates for secret detection](#policy-templates-for-secret-detection) below.

| Policy | Description | Severity |
| --- | --- | --- |
| Valid Secrets | Use this template to scan the code for active secrets. When a secret is valid, it means that the secret meets the necessary criteria or requirements to be considered acceptable or legitimate within a given context. For example, GitHub personal access tokens of an employee that are not yet expired and can be used to access an organization’s codebase. | Critical |
| Invalid Secrets | Scan the code for any secrets that are no longer valid. | Low |
| Secrets without validation rules | Detect secrets that cannot be validated either because there is no validator or the validation failed for any reason. | Medium |

## Policy templates for secret detection

Endor Labs provides the following finding policy templates for detecting secrets.
See [Finding Policies](..) for details on how to create policies from policy templates.

| Policy template | Description | Severity |
| --- | --- | --- |
| Valid Secrets | Use this template to scan the code for active secrets. When a secret is valid, it means that the secret meets the necessary criteria or requirements to be considered acceptable or legitimate within a given context. For example, GitHub personal access tokens of an employee that are not yet expired and can be used to access an organization’s codebase. | Critical |
| Invalid Secrets | Use this template to scan the code for any secrets that are no longer valid. | Low |
| Secrets without validation rules | Use this template to detect secrets that cannot be validated either because there is no validator or the validation failed for any reason. | Medium |
| Define custom secret token policy rules | Use this template to detect secrets in the code using a custom secret rule to detect secrets of any service that may not be included in the other rules. | Critical |

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
