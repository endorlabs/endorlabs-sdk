---
url: https://docs.endorlabs.com/sast-scans-with-endorlabs/run-a-sast-scan/
title: Run a SAST scan | Endor Labs Docs
downloaded: 2026-01-26 10:06:57
---

Run a SAST scan | Endor Labs Docs



* Type to search...

[Print entire section](/sast-scans-with-endorlabs/run-a-sast-scan/_print.html)



# Run a SAST scan

To run a SAST scan on a project run the following command.
`endorctl scan --sast -n <project namespace>`

You can run the `endorctl scan --sast` command with the following options.

| Option | Description |
| --- | --- |
| `-n`, `--namespace` | Namespace of the project with which you are working. Mandatory. |
| `--include-path` | Limit the scan to the specified file paths or directories using Glob style expressions. For example, `--include-path="src/java/**”`, scans all the files under `src/java`, including any subdirectories, while `--include-path="src/java/*”,` only includes the files directly under `src/java`. Paths must be relative to the root of the repository. Use quotes to ensure that your shell does not expand wildcards. |
| `--exclude-path` | Specify one or more file paths or directories using Glob style expressions. For example, `--include-path="src/java/**”`, scans all the files under `src/java`, including any subdirectories, while `--include-path="src/java/*”,` only includes the files directly under `src/java`. Paths must be relative to the root of the repository. Use quotes to ensure that your shell does not expand wildcards. |
| `--disable-code-snippet-storage` | Specify the flag to disable storing the code snippet that violates the SAST policy. |
| `--path` | The path to issue the scan. |

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
