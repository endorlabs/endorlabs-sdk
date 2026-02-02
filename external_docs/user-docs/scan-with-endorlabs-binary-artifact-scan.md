---
url: https://docs.endorlabs.com/scan-with-endorlabs/binary-artifact-scan/
title: Scan artifacts and binaries | Endor Labs Docs
downloaded: 2026-01-29 22:23:52
---

Scan artifacts and binaries | Endor Labs Docs



* Type to search...

[Print entire section](/scan-with-endorlabs/binary-artifact-scan/_print.html)



# Scan artifacts and binaries

Detect and manage software supply chain risks by scanning software binaries and artifacts using Endor Labs.

You can now perform endorctl scan on your binaries and artifacts without requiring access to source code or build systems. Scan Java and Python packages that are pre-built, bundled, or downloaded into your local system by specifying a file path to your artifact or binary package.

Endor Labs scans the specified package, producing vital scan artifacts such as details about resolved dependencies and transitive dependencies, along with comprehensive call graphs. It enables you to acquire valuable insights and improve the security and reliability of the software components.

## System specifications for deep scan

Before you proceed to run a deep scan, ensure that your system meets the following specification.

| Project Size | Processor | Memory |
| --- | --- | --- |
| Small projects | 4-core processor | 16 GB |
| Mid-size projects | 8-core processor | 32 GB |
| Large projects | 16-core processor | 64 GB |

### File format specifications

| Language | Package file formats |
| --- | --- |
| Java | JAR, WAR, EAR, .zip, tar.gz, and tar |
| Python | EGG(tar.gz) and Wheel(.whl) |

When scanning archive formats such as `.zip`, `tar`, and `.tar.gz`, we support embedded package formats including `.jar`, `.ear`, `.war`, and `.whl.` We also support `.tar.gz` archives that contain Python package metadata such as egg-info.

You can scan JAR, WAR, and EAR package file formats built using Maven or Gradle with a `pom.xml` configuration file. To scan packages without a `pom.xml` configuration, see [Scan Java packages without pom.xml](../language-scanning/java/#scan-projects-without-pomxml-beta).

### Software prerequisites

If you have a private registry and internal dependencies on other projects, you must configure private registries for the Python and Java projects. See [Configure package manager integrations](../../integrations/package-manager/) for more information.

## Understand the scan arguments

Use `--package` as an argument to scan artifacts or binaries. You must provide the path of your file using `--path` and specify a name for your project using `--project-name`.

```
endorctl scan --package --path --project-name
```

## Run the scan

Use the following options to scan your repositories.

### Option 1 - Quick scan

Perform a quick scan of the local packages to get quick visibility into your software composition. This scan won’t perform reachability analysis to help you prioritize vulnerabilities.

**Syntax**:

```
endorctl scan --quick-scan --package --path=<<specify-the-path-of-your-file>> --project-name=<<specify-a-name-for-the-project>>
```

**Example**:

```
endorctl scan --quick-scan --package --path=/Users/username/packages/logback-classic-1.4.10.jar --project-name=package-scan-for-java
```

### Option 2 - Deep scan

Use the deep scan to perform dependency resolution, reachability analysis, and generate call graphs. You can do this after you complete the quick scan successfully.

**Syntax**:

```
endorctl scan --package --path=<<specify-the-path-of-your-file>> --project-name=<<specify-a-name-for-the-project>>
```

**Example**:

```
endorctl scan --package --path=/Users/username/packages/logback-classic-1.4.10.jar --project-name=java-package-scan
```

## View results

You can sign into the [Endor Labs user interface](https://app.endorlabs.com), click the **Projects** on the left sidebar, and find your project using the name you entered to review its results.

You can view the list of projects created for scanning packages using the parameter `Project Platform Source` matches `PLATFORM_SOURCE_BINARY` to search on **Projects**.

![package scan search results](../../images/package_scan_search_results.png)

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
