---
url: https://docs.endorlabs.com/managing-policies/finding-policies/sast-policies/
title: SAST policies | Endor Labs Docs
downloaded: 2025-11-20 11:50:05
---

SAST policies | Endor Labs Docs



* Type to search...
* ---

[Print entire section](/managing-policies/finding-policies/sast-policies/_print.html)



# SAST policies

Learn about the predefined finding policy templates for SAST used in your software development environment.

Endor Labs provides the following finding policy templates for detecting SAST issues. See [Finding policies](..) for details on how to create policies from policy templates.

See [SAST severity matrix](../../../sast-scans-with-endorlabs/#sast-severity-matrix) to understand how Endor Labs assigns severity to SAST findings.

| Policy template | Description | Severity |
| --- | --- | --- |
| Report SAST results matching given rule names | Raise findings for SAST results for a given set of SAST rules. The severity of the finding is set based on the severity of the rule that created the result. If the SAST rule does not have a severity then the policy finding severity is used. | Critical |
| Report SAST results matching given criteria | Raise findings for SAST results based on a given set of criteria, such as the severity, confidence level, and/or tags. The severity of the finding is set based on the severity of the rule that created the result. If the SAST rule does not have a severity then the policy finding severity is used. | Critical |

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
