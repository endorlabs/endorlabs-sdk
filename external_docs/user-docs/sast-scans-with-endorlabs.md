---
url: https://docs.endorlabs.com/sast-scans-with-endorlabs/
title: SAST scan | Endor Labs Docs
downloaded: 2025-10-23 23:27:42
---

SAST scan | Endor Labs Docs



* Type to search...
* ---

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

When you run a SAST scan, Endor Labs downloads Opengrep and works seamlessly. If you wish, you can use Semgrep instead of Opengrep with Endor Labs. See [Use Semgrep with Endor Labs](../administration/use-semgrep-with-endorlabs/) for more information.

#### Warning

If you use Semgrep with Endor Labs, SAST scan is supported on macOS and Linux, and not supported on Windows.

Endor Labs includes a set of [curated rules](../sast-scans-with-endorlabs/manage-sast-rules/). You can [create your own rules](../sast-scans-with-endorlabs/manage-sast-rules/create-sast-rule/) or [import rules](../sast-scans-with-endorlabs/manage-sast-rules/import-sast-rule/) with the rule designer.

#### Note

Ensure that the default finding policy `Report SAST results matching given criteria` is enabled so that SAST scans generate findings.

When you [scan with the SAST option enabled](../sast-scans-with-endorlabs/run-a-sast-scan/), Endor Labs uses Opengrep to scan for weaknesses in your source code based on the enabled rules and generates results based on the configured finding policies.

#### Tip

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

Endor Labs supports single-function analysis for the following languages through curated rules and custom user rules.

```
- Apex
- Bash
- C
- Cairo
- Circom
- Clojure
- CPP
- CSharp
- Dart
- Dockerfile
- Elixir
- Generic
- Go
- Hack
- Html
- Java
- Javascript
- Json
- Jsonnet
- Julia
- Kotlin
- Lisp
- Lua
- Move
- Ocaml
- PHP
- PromQL
- Protobuf
- Python
- QL
- R
- Regex
- Ruby
- Rust
- Scala
- Scheme
- Solidity
- Swift
- Terraform
- Typescript
- XML
- Yaml
```

## SAST scan with endorctl

Ensure that you complete the following prerequisites before you proceed to do a SAST scan using endorctl.

### Install endorctl

[Install endorctl](../getting-started/quickstart/quickstart-local-system/) and configure your environment to run Endor Labs scan.

### Run SAST scan with endorctl

You can run a SAST scan with endorctl with the following command.

`endorctl scan --sast -n <project namespace>`

See [Run a SAST scan](../sast-scans-with-endorlabs/run-a-sast-scan/) for more information on the command options.

## SAST scan in monitoring scans

You can enable SAST scans when you configure monitoring or supervisory scans using the Endor Labs GitHub App, Azure DevOps App, and GitLab App. See [Monitoring scans](../deployment/monitoring-scans/) for more information. To disable the storage of code snippet in SAST scans for monitoring scans, you need to create a scan profile for your monitoring scan with disable code snippet storage as enabled. Note that the setting applies to all scans that you use this scan profile and not just the monitoring scans.

## SAST scan in Endor Labs GitHub Action

You can also enable SAST scan in the Endor Labs GitHub Action. Set the scanning parameter, `scan_sast` as `true`. To disable code snippet storage for SAST scans, set `disable_code_snippet_storage` as `true`. See [Scan with GitHub Actions](../deployment/ci-scans/scan-with-github-actions/) for more information.

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
