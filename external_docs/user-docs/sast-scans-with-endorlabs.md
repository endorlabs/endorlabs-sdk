---
url: https://docs.endorlabs.com/sast-scans-with-endorlabs/
title: SAST scan | Endor Labs Docs
downloaded: 2026-01-29 22:23:23
---

SAST scan | Endor Labs Docs



* Type to search...

[Print entire section](/sast-scans-with-endorlabs/_print.html)



# SAST scan

Static Application Security Testing (SAST) is an automated security analysis methodology that examines application code to identify potential security vulnerabilities.

SAST has the following characteristics:

* **White-box Testing**: Provides full visibility into application internals
* **Non-runtime Analysis**: Performs scans without code execution
* **Early Detection**: Identifies vulnerabilities during development phases
* **Language Support**: Analyzes multiple programming languages and frameworks

Endor Labs integrates [Opengrep](https://www.opengrep.dev/) to provide SAST scan with endorctl.

Opengrep is an open-source, static analysis tool that finds bugs and vulnerabilities in the source code using pattern matching. Opengrep parses the source code, applies pattern matching based on rules, and reports matches based on the rule specifications. Opengrep rules are in the yaml format.

When you run a SAST scan, Endor Labs downloads Opengrep and works seamlessly.

Endor Labs includes a set of [curated rules](../sast-scans-with-endorlabs/manage-sast-rules/). You can [create your own rules](../sast-scans-with-endorlabs/manage-sast-rules/create-sast-rule/) or [import rules](../sast-scans-with-endorlabs/manage-sast-rules/import-sast-rule/) with the rule designer.

**Note**

Ensure that the default finding policy `Report SAST results matching given criteria` is enabled so that SAST scans generate findings.

When you [scan with the SAST option enabled](../sast-scans-with-endorlabs/run-a-sast-scan/), Endor Labs uses Opengrep to scan for weaknesses in your source code based on the enabled rules and generates results based on the configured finding policies.

**Tip**

Endor Labs does not scan the files included in the `.gitignore` files during SAST scan. You can also use the `nosemgrep` annotation in the code to skip SAST scan. Refer to the [Semgrep Documentation](https://semgrep.dev/docs/ignoring-files-folders-code#ignore-code-through-nosemgrep) for more information.

SAST scan results are available in the Findings page. See [View SAST Findings](../sast-scans-with-endorlabs/viewing-sast-findings/) for more information.

You can create exception policies to exclude results from the findings page. See [Create exception policy](../sast-scans-with-endorlabs/create-exception-policy/) for more information.

You can create a finding policy using predefined templates to control which SAST results appear as findings. See [SAST policies](../managing-policies/finding-policies/sast-policies/) for more information.

## SAST severity matrix

Endor Labs determines the severity of findings by combining two factors from the SAST rule: impact and confidence. Impact measures the potential consequences if a security issue were to be exploited. Confidence represents how certain the system is that a detected pattern indicates a genuine security issue rather than a false positive.

The following matrix shows how Endor Labs resolves severity by combining impact and confidence.

|  |  |  |  |
| --- | --- | --- | --- |
| High Impact | Medium | High | Critical |
| Medium Impact | Low | Medium | High |
| Low Impact | Low | Low | Medium |
|  | Low Confidence | Medium Confidence | High Confidence |
| --- | --- | --- | --- |

## Language support

Endor Labs supports single-function analysis for the following languages through curated rules and custom user rules:

`Apex` `Bash` `C` `Cairo` `Circom` `Clojure` `C++` `C#` `Dart` `Dockerfile` `Elixir` `Generic` `Go` `Hack` `HTML` `Java` `JavaScript` `JSON` `Jsonnet` `Julia` `Kotlin` `Lisp` `Lua` `Move` `OCaml` `PHP` `PromQL` `Protobuf` `Python` `QL` `R` `Regex` `Ruby` `Rust` `Scala` `Scheme` `Solidity` `Swift` `Terraform` `TypeScript` `XML` `YAML`

## SAST scan with endorctl

Ensure that you complete the following prerequisites before you proceed to do a SAST scan using endorctl.

### Install endorctl

[Install endorctl](../getting-started/quickstart/quickstart-local-system/) and configure your environment to run Endor Labs scan.

### Run SAST scan with endorctl

You can run a SAST scan with endorctl with the following command.

`endorctl scan --sast -n <project namespace>`

See [Run a SAST scan](../sast-scans-with-endorlabs/run-a-sast-scan/) for more information on the command options.

## SAST scan in monitoring scans

You can enable SAST scans when you configure monitoring or supervisory scans using the Endor Labs GitHub App, Azure DevOps App, Bitbucket App, and GitLab App. See [Monitoring scans](../deployment/monitoring-scans/) for more information. To disable the storage of code snippet in SAST scans for monitoring scans, you need to create a scan profile for your monitoring scan with disable code snippet storage as enabled. This setting applies to all scans that you use this scan profile, not just the monitoring scans.

## SAST scan in Endor Labs GitHub Action

You can also enable SAST scan in the Endor Labs GitHub Action. Set the scanning parameter, `scan_sast` as `true`. To disable code snippet storage for SAST scans, set `disable_code_snippet_storage` as `true`. See [Scan with GitHub Actions](../deployment/ci-scans/scan-with-github-actions/) for more information.

## SAST incremental scans

You can use the `--pr-incremental` flag to perform an [incremental scan](../scan-with-endorlabs/pr-scans/#perform-incremental-pr-scan) on your pull requests or merge requests for SAST. In [monitoring scans](#sast-scan-in-monitoring-scans), incremental scans are done by default for PR scans. Endor Labs only scans the files that have changed since the last scan on the baseline branch. Endor Labs computes a diff between the target branch and the baseline branch to identify the changed files. Any modified file is sent through Opengrep to fully scan for SAST issues, and unchanged files are skipped. Endor Labs does not perform chunk-level or line-level code diff analysis for SAST. If there are more than 1000 modified files, Endor Labs performs a complete scan.

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
