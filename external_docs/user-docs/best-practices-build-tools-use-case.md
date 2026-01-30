---
url: https://docs.endorlabs.com/best-practices/build-tools-use-case/
title: Best Practices: Build tools use cases | Endor Labs Docs
downloaded: 2026-01-29 22:23:16
---

Best Practices: Build tools use cases | Endor Labs Docs



* Type to search...

[Print entire section](/best-practices/build-tools-use-case/_print.html)



# Best Practices: Build tools use cases

Explore common build tool scenarios and strategies to configure scan profiles for accurate and reliable scans

Endor Labs relies on build tools such as compilers, runtimes, and package managers to scan applications accurately. These tools are essential for reproducing your project’s build environment during a scan. This is especially important for languages like Python, Java, or .NET, where lock files are less common and exact tool versions help ensure consistency. By specifying build tools in your scan profile, you can avoid issues like incorrect language detection, broken dependencies, or missing findings.

Scans may fail if the toolchain is incorrect or required build tools are missing. A well-configured scan profile aligns the environment with your project and ensures accurate results.
You can configure toolchains and build tools in scan profiles in multiple ways:

* [Configure scan profile through Endor Labs user interface](../../scan-with-endorlabs/manage-scan-profiles/configure-scanprofile-ui/)
* [Configure scan profile through `scanprofile.yaml`](../../scan-with-endorlabs/manage-scan-profiles/configure-scanprofile-yaml/)
* [Configure scan profile through Endor Labs API](../../scan-with-endorlabs/manage-scan-profiles/configure-scanprofile-api/)

## Auto detection of toolchains

Auto detection takes place when no scan profile or build tool is configured for a project. The process identifies the toolchain versions required by the project and compares them with the versions that Endor Labs supports. See the [toolchain support matrix](../../scan-with-endorlabs/manage-scan-profiles/build-tools/#toolchain-support-matrix) to learn more about supported versions and [auto detection](../../scan-with-endorlabs/manage-scan-profiles/auto-detect-toolchains/) to learn about the complete process.

**Note**

Use the `--install-build-tools` flag to enable auto detection in endorctl scans.

## Build tool use case scenarios

Understanding build tools use cases help you improve scan accuracy and streamline your scanning process. Here are some common use cases for build tools that show how you can customize scan profiles to better match your project’s needs.

### Configure tool versions for multi-language projects

You can configure language specific tool versions in a single scan profile based on OS and architecture. For example, to scan a multi-language repository with `Python`, `Golang`, and `Node.js`, set `Python 3.9.19`, `Golang 1.22.7`, and `Node.js 20.10.0`. During the scan, Endor Labs applies the configured toolchain version for each language. This ensures accurate builds, better dependency resolution, and improved findings.

![Multiple language repository](../../images/multi-lang-toolchain.png)

### Toolchain versions across different architectures

In a multi-architecture environment, you can configure toolchains for operating system and architecture combination to ensure scans align with system specific setups.

For example, a Linux AMD64 machine with `Python 3.8.0` installed but `Python 3.8.19` specified in the toolchain configuration will use version `3.8.19` during scans. A macOS AMD64 machine with `Python 3.10.14` installed but `Python 3.7.0` configured will use the system’s `Python 3.10.14`. Meanwhile, a macOS ARM64 machine without any version of `Python` installed and no toolchain configured will use `Python 3.12.4`, the default version supported by Endor Labs.

![Multiple architecture](../../images/multi-arch-lang.png)

### Configure custom toolchains for unsupported versions

Set up a custom toolchain version when your project depends on a specific version not provided by Endor Labs. This gives you precise control over the scanning environment and helps avoid issues caused by version mismatches.

For example, the highest supported Java version in the default list is `17`, but your project needs `23.0.2`, the scan will fail if no toolchain is configured. In such cases, create a custom build toolchain for `Java 23.0.2` in your scan profile which is linked to your project. When you re-run the scan, Endor Labs uses the configured `23.0.2` version and gives reliable results. This configuration works only in the namespace where you created the build tool. See [configure custom version for the toolchain](../../scan-with-endorlabs/manage-scan-profiles/configure-scanprofile-ui/#configure-a-custom-version-for-a-tool) to learn how to configure custom version for a toolchain.

![Custom toolchain version for Java which is not provided by Endor Labs](../../images/custom-toolchian-unsupported.png)

### Custom and default toolchain version strategy

Endor Labs selects the toolchain version for each language based on your scan profile. When you configure toolchain versions for some languages and leave others unspecified, the scan uses your specified versions and defaults to the Endor Labs toolchain matrix for the remaining languages.

For example, if your project’s scan profile specifies `Yarn 3.8.7` and `pnpm 8.10.2` but does not specify a `Node.js` version, Endor Labs will use the configured `Yarn` and `pnpm` versions, and automatically select `Node.js 20.10.0` from the default supported version list. This approach ensures your project builds successfully without requiring extra configuration.

![Default and configured](../../images/default-and-configured.png)

### Reuse build tool configurations across multiple projects

Multiple projects often require specific custom toolchain versions, which you can configure in your scan profile. For example, `Project A` needs `Python 3.13.0` and `Go 1.24.6` and `Project B` requires the same `Python` and `Go` versions, and an additional `Java 22.0.2`.
Configuring each toolchain separately for these two project can be time-consuming.

You can configure these build tools and name them `3.13.0` and `1.24.6` in your namespace. See [configure build tools](../../scan-with-endorlabs/manage-scan-profiles/configure-scanprofile-ui/#configure-build-tools) for setup instructions.

![Build tools use case 1](../../images/build-tools-use1.png)

* For Project A’s scan profile, add these reusable build tools in its scan profile.

![Build tools use case 3](../../images/build-tools-use3.png)

* For Project B’s scan profile, add the same reusable build tools and the additional Java toolchain.

![Build tools use case 2](../../images/build-tools-use2.png)

This approach reduces duplication, saves time, and ensures consistent toolchain use across projects. Note that these reusable build tool configurations are namespace specific, so only projects within your namespace can access them.

**Note**

Use clear, unique, and consistent naming for build tool and scan profiles to improve visibility and promote reuse. For example `frontend-node16`, `backend-java17`, `shared-go120`.

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
