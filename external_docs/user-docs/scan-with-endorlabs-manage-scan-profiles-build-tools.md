---
url: https://docs.endorlabs.com/scan-with-endorlabs/manage-scan-profiles/build-tools/
title: Configure build tools | Endor Labs Docs
downloaded: 2026-01-29 22:20:24
---

Configure build tools | Endor Labs Docs



* Type to search...

[Print entire section](/scan-with-endorlabs/manage-scan-profiles/build-tools/_print.html)



# Configure build tools

Learn about build tools to build repeatable patterns in your scan environment.

Endor Labs uses build tools to scan projects, generate reliable Software Bill of Materials (SBOM), and detect security or operational risks. For languages like Java, Python, and .NET that depend on the build environment, it relies on specific runtime or package manager versions to ensure precise results. When tools are missing, you can define and install them in the CLI, and Endor Labs sets them up in an isolated sandbox during the scan. This feature is supported on Linux and macOS.

You need to [install and initialize](../../../endorctl/install-and-configure/) endorctl before configuring the build toolchains in a scan profile.

## Toolchain priority in GitHub App scans

[Endor Labs GitHub App](../../../deployment/monitoring-scans/github-app/) continuously monitors your projects for security and operational risks. The app monitors all the projects included in your GitHub workspace and scans run once every 24 hours.

For performing scans, the GitHub App checks the toolchain specifications in the following order:

1. Scan workflow, if present.
2. Toolchain configuration specified through endorctl API.
3. Toolchain configuration specified in `scanprofile.yaml` file.
4. Enable auto detection to automatically detect the toolchains from your manifest files.
5. Uses the system defaults.

## Configure build tools for endorctl scans

After [installing and initializing](../../../endorctl/install-and-configure/) endorctl, run the endorctl scan with the `--install-build-tools` flag to automatically download and install any missing toolchains in an isolated sandbox to properly execute language-specific scans and dependency resolution.

1. For the first time, run the endorctl scan to create a project with Endor Labs.

   ```
   endorctl scan
   ```
2. Run the following command to automatically download and install build tools as part of your scan.

   ```
   endorctl scan --install-build-tools
   ```
3. The system checks for the required toolchain specifications in the following order before installing them in the sandbox.

   * [Configure scan workflow through endorctl API](../configure-scan-workflow-through-api/)
   * [Configure toolchain profile through endorctl API](../configure-scanprofile-api/)
   * [Configure toolchain profile in the profile.yaml file](../configure-scanprofile-yaml/)
   * [Automatically detect toolchain profiles](../auto-detect-toolchains/)
   * [Uses the system defaults](#system-default-toolchain-versions)

## System default toolchain versions

If you do not provide a tool profile, the default toolchains are installed in the sandbox while performing the endorctl scan with the `install-build-tools` flag. See [Toolchain support matrix](#toolchain-support-matrix) for details on default versions.

### Toolchain support matrix

The following table outlines the toolchain profile support details across different languages and platforms.

| Dependencies | Support for API | Support for profile yaml | Support for Auto detection | Default Version | Platform |
| --- | --- | --- | --- | --- | --- |
| **Java** | Supported | Supported | Java 8, 11, 17, 21 | Java 17 | Linux, Darwin |
| **Maven** | Supported | Supported | Maven 3.8.8, 3.9.4, 3.9.5, 3.9.6, 3.9.7, 3.9.8, 3.9.9, 3.9.10, 3.9.11 | Maven 3.9.4 | Linux, Darwin |
| **Gradle** | Supported | Supported | Gradle 6.9.4, 7.6.4, 8.4, 9.0.0 | Gradle 8.4 | Linux, Darwin |
| **Python** | Supported | Supported | Python 3.8, 3.9, 3.10, 3.11, 3.12, 3.13 | Python 3.10 | Linux, Darwin |
| **NodeJS** | Supported | Supported | Node.js 16.20, 18.20, 20.19, 22.18, 24.6, 24.7, 24.8, 24.12, 25.4 | Node.js 20.10.0 | Linux, Darwin |
| **Yarn** | Supported | Supported | Yarn 1.22, 2, 3, 4 | Yarn 1.22.19 | Linux, Darwin |
| **pnpm** | Supported | Supported | pnpm 6.35, 7.33, 8.15, 9.15, 10.14, 10.15.0, 10.15.1, 10.16.0, 10.16.1 | pnpm 8.10.2 | Linux, Darwin |
| **Golang** | Supported | Supported | Golang 1.12, 1.13, 1.14, 1.15, 1.16, 1.17, 1.18, 1.19, 1.20, 1.21, 1.22, 1.24, 1.25 | Golang 1.24.6 | Linux, Darwin |
| **.NET** | Supported | Supported | .NET 6, 7, 8, 9, 10 | .NET 7.0.401 | Linux, Darwin |
| **Scala** | Supported | Supported | Scala 1.10.0, 1.11.0, 1.12.0 | Scala 1.9.0 | Linux, Darwin |
| **Rust** | Supported | Supported | Rust 1.89.0 | Rust 1.89.0 | Linux, Darwin |
| **Kotlin** | Supported | Supported |  | Java 17 | Linux, Darwin |
| **Typescript** | Supported | Supported | 16.20, 18.20, 20.19, 22.18, 24.6, 24.7, 24.8, 24.12 | Node.js 20.10.0 | Linux, Darwin |
| **Android** | Supported | Supported |  | platform-tools | Linux, Darwin |
| **PHP** | Supported | Supported |  | 8.2 | Linux |
| **Ruby** | Supported | Supported | Ruby 3.2.9, 3.3.9, 3.4.5 | Ruby 3.2.9 | Linux |

**Note**

.NET 5 and earlier versions are not supported for auto detection or manual configuration.

**Note**

If a project uses Java 8, Endor Labs installs both Java 8 and Java 17.0.11. It builds the project with Java 8 and scans it with Java 17.

## Configure automated scan parameters

Automated scan parameters are endorctl parameters and environment variables that you define in a scan profile. They apply to projects linked to that profile and help customize scan behavior during cloud scans.

You can define the following parameters in your scan profile:

* **included\_paths**: Enable to specify a list of paths to include in the scan.
* **excluded\_paths**: Enable to specify a list of paths to exclude from the scan. Excluded paths do not apply to secrets scanning. Secrets detection always scans the full repository. To filter or suppress secret findings, use policies or a `.gitleaksignore` file instead.
* **languages**: Enable to specify a list of languages to scan. If empty, default values are used.
* **call\_graph\_languages**: Enable to specify a list of languages to use for generating call graphs. If empty, default values are used.
* **additional\_environment\_variables**: Enable to specify additional environment variables to set during the scan. Only the environment variables starting with `ENDOR_` are passed to the scan, all others are ignored. See [Global flags and environment variables](../../../endorctl/environment-variables/) for a complete list of available environment variables.
* **enable\_automated\_pr\_scans**: Enables automatic scanning of pull request changes.
* **enable\_pr\_comments**: Enables adding scan results as comments in pull requests.
* **enable\_sast\_scan**: Enables SAST during the scanning process.
* **disable\_code\_snippet\_storage**: Disables the storage of code snippets.

If you are using Bazel in your build, you can further configure:

* **bazel\_configuration**: Enable to specify configuration settings for Bazel scans. See [Bazel flags](../../../endorctl/commands/scan/#bazel-flags) for more details.
* **bazel\_show\_internal\_targets**: Enable to include internal build targets in the dependency analysis.
* **bazel\_workspace\_path**: Enable to specify the path to the Bazel workspace.
* **bazel\_include\_targets**: Enable to specify Bazel targets to include in the scan.
* **bazel\_exclude\_target**: Enable to specify Bazel targets to exclude from the scan.

The following toolchain profile shows a yaml definition with configured automated scan parameters:

```
kind: AutomatedScanParameters
spec:
  automated_scan_parameters:
    included_paths:
      - python/**
    excluded_paths:
      - java/**
    languages:
      - python
    call_graph_languages:
      - python
    additional_environment_variables:
      - ENDOR_LOG_VERBOSE=true
      - ENDOR_LOG_LEVEL=debug
    enable_automated_pr_scans: true
    enable_pr_comments: true
    enable_sast_scan: true
    disable_code_snippet_storage: true
    bazel_configuration:
      bazel_show_internal_targets: true
      bazel_workspace_path: "go-bazel-repo/"
      bazel_include_targets:
      bazel_abs:
        - "//cmd:cmd"
```

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
