---
url: https://docs.endorlabs.com/sast-scans-with-endorlabs/manage-sast-rules/import-sast-rule/
title: Import SAST rules | Endor Labs Docs
downloaded: 2025-11-20 11:48:37
---

Import SAST rules | Endor Labs Docs



* Type to search...
* ---

[Print entire section](/sast-scans-with-endorlabs/manage-sast-rules/import-sast-rule/_print.html)



# Import SAST rules

You can import Semgrep-compatible SAST rules that you create as yaml files. The files must have `yaml` or `yml` extensions and the rules should be inside a gzip or tar archive.

## Import SAST rules through the user interface

You can bulk import rules through the user interface.

1. From the left sidebar, navigate to **Policies and Rules** and select **SAST RULES**.
2. Click **Import**.

   ![Import SAST rule](../../../images/SAST_importrule.png)
3. Click **Browse** and select the archive file that contains the rules.
4. Enter the version of the rule, if required.

   If you do not enter a version and the rules already exist in the system, the rule upload may fail.

### Import SAST rules with endorctl

You can bulk import a number of rules using the following command.

`endorctl rule-set import --file-path <file> --rule-version <version> -n namespace`

| Option | Description |
| --- | --- |
| `-n`, `--namespace` | Namespace of the project with which you are working. Mandatory. |
| `—-file-path` | The path to the file that contains the rule set that should be imported. Supported file types are `.tar` and `.gz`. |
| `—rule-version` | The semantic version that applies to all the rules in the set. The command fails if there are any rules that exist with this version. |

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
