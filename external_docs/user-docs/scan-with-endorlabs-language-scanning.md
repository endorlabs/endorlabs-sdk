---
url: https://docs.endorlabs.com/scan-with-endorlabs/language-scanning/
title: Scan for open source risks | Endor Labs Docs
downloaded: 2026-01-16 09:46:57
---

Scan for open source risks | Endor Labs Docs



* Type to search...

[Print entire section](/scan-with-endorlabs/language-scanning/_print.html)



# Scan for open source risks

Scan and detect publicly exposed open source issues posing risks to your organization.

Endor Labs supports the following major capabilities to help teams reduce the risk and expense of software dependency management across the lifecycle of software reuse.

* **SCA** - Software composition analysis is the identification of the bill of materials for first-party software packages and the mapping of vulnerabilities to these software component versions. SCA helps teams to maintain compliance and get visibility into the risks of their software inventory.
* **Endor Scores** - Endor Labs provides a holistic risk score that includes the security, quality, popularity and activity of a package. Risk scores help in identifying leading indicators of risk in addition to if a software component is outdated, or unmaintained. Risk analysis helps teams to go beyond vulnerabilities and approach the risk of their software holistically.
* **Reachability Analysis** - Reachability analysis is Endor Labs’ capability to perform static analysis on your software packages to give context to how each vulnerability may be reached in the context of your code. This includes mapping vulnerabilities back to vulnerable functions so that deep static analysis can target vulnerabilities with higher levels of granularity as well as the identification of unused software dependencies.
* **Upgrade Impact Analysis** - Upgrade impact analysis allows security teams to set better expectations with their development teams by identifying breaking changes associated with an update of a direct dependency.

The resource requirements, both minimum and recommended, for build runners or workers executing scans using **endorctl** are listed here.

**Note**

Large applications may require additional resources to complete or enhance the scan performance.

##### Minimum Resources

| CPU | Memory |
| --- | --- |
| 4 core | 16 GB RAM |

##### Recommended Resources

| CPU | Memory |
| --- | --- |
| 8 core | 32 GB RAM |

## Supported languages

| Language | SCA | Endor Scores | Reachability Analysis | Pre-computed Reachability Analysis | Phantom Dependencies | Upgrade Impact Analysis | Install Toolchains |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [Java](../../scan-with-endorlabs/language-scanning/java/) | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ |
| [C/C++](../../scan-with-endorlabs/language-scanning/c/) | ✓ | ✓ | ✗ | ✗ | ✓ | ✗ | ✗ |
| [Python](../../scan-with-endorlabs/language-scanning/python/) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| [Rust](../../scan-with-endorlabs/language-scanning/rust/) | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✓ |
| [JavaScript](../../scan-with-endorlabs/language-scanning/javascript/) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| [Golang](../../scan-with-endorlabs/language-scanning/golang/) | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | ✓ |
| [.NET (C#)](../../scan-with-endorlabs/language-scanning/dotnet/) | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ |
| [Kotlin](../../scan-with-endorlabs/language-scanning/kotlin/) | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ |
| [Scala](../../scan-with-endorlabs/language-scanning/scala/) | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ |
| [Ruby](../../scan-with-endorlabs/language-scanning/ruby/) | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| [Swift/Objective-C](../../scan-with-endorlabs/language-scanning/swift-objective-c/) | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| [PHP](../../scan-with-endorlabs/language-scanning/php/) | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |

## Complete support matrix

The following comprehensive matrix lists the supported languages, build tools, manifest files, and supported requirements.

| Language | Package Managers / Build Tool | Manifest Files | Extensions | Supported Requirements |
| --- | --- | --- | --- | --- |
| [Java](../../scan-with-endorlabs/language-scanning/java/) | Maven | `pom.xml` | `.java` | JDK version 11-25; Maven 3.6.1 and higher versions |
|  | Gradle | `build.gradle` or `build.gradle.kts` | `.java` | JDK version 11-25; Gradle 6.0.0 and higher versions |
|  | Bazel | `workspace`, `MODULE.bazel`, `BUILD.bazel` | `.java` | JDK version 11-25; Bazel versions `5.x.x`, `6.x.x`, and `7.x.x` |
| [C/C++](../../scan-with-endorlabs/language-scanning/c/) | Not applicable | Not applicable | `.c`, `.cc`, `.cpp`, `.cxx`, `.h`, `.hpp`, `.hxx` ` | Not applicable |
| [Kotlin](../../scan-with-endorlabs/language-scanning/kotlin/) | Maven | `pom.xml` | `.kt` | JDK version 11-25; Maven 3.6.1 and higher versions |
|  | Gradle | `build.gradle` or `build.gradle.kts` | `.kt` | JDK version 11-25; Gradle 6.0.0 and higher versions |
| [Golang](../../scan-with-endorlabs/language-scanning/golang/) | Go | `go.mod`, `go.sum` | `.go` | Go 1.12 and higher versions |
|  | Bazel | `workspace`, `MODULE.bazel`, `BUILD.bazel` | `.go` | Bazel versions `5.x.x`, `6.x.x`, and `7.x.x` |
| [Rust](../../scan-with-endorlabs/language-scanning/rust/) | Cargo | `cargo.toml`, `cargo.lock` | `.rs` | Rust 1.63.0 and higher versions |
| [JavaScript](../../scan-with-endorlabs/language-scanning/javascript/) | npm | `package-lock.json`, `package.json` | `.js` | npm 6.14.18 and higher versions |
|  | pnpm | `pnpm-lock.yaml`, `package.json` | `.js` | pnpm 3.0.0 and higher versions |
|  | Yarn | `yarn.lock`, `package.json` | `.js` | Yarn all versions |
| [TypeScript](../../scan-with-endorlabs/language-scanning/javascript/) | npm | `package-lock.json`, `package.json` | `.ts` | npm 6.14.18 and higher versions |
|  | pnpm | `pnpm-lock.yaml`, `package.json` | `.ts` | pnpm 3.0.0 and higher versions |
|  | Yarn | `yarn.lock`, `package.json` | `.ts` | Yarn all versions |
| [Python](../../scan-with-endorlabs/language-scanning/python/) | `pip` | `requirements.txt` | `.py` | Python 3.6 and higher versions; pip 10.0.0 and higher versions |
|  | Poetry | `pyproject.toml`, `poetry.lock` | `.py` |  |
|  | PyPI | `setup.py`, `setup.cfg`, `pyproject.toml` | `.py` |  |
|  | UV | `uv.lock`, `pyproject.toml` | `.py` | Python 3.8 and higher versions |
|  | Bazel | `workspace`, `MODULE.bazel` | `.py` | Bazel versions `5.x.x`, `6.x.x`, and `7.x.x` |
| [.NET (C#)](../../scan-with-endorlabs/language-scanning/dotnet/) | NuGet | `*.csproj`, `package.lock.json`, `projects.assets.json`, `Directory.Build.props`, `Directory.Packages.props`, `*.props` | `.cs` | .NET 5.0 and higher versions; .NET Core 1.0 and higher versions; .NET Framework 4.5 and higher versions. |
| [Scala](../../scan-with-endorlabs/language-scanning/scala/) | sbt | `build.sbt` | `.sc` or `.scala` | sbt 1.3 and higher versions |
|  | Gradle | `build.gradle`, `build.gradle.kts` | `.sc` or `.scala` | JDK version 11-25; Gradle 6.0.0 and higher versions |
|  | Bazel | `workspace`, `MODULE.bazel` | `.sc` or `.scala` | Bazel versions `5.x.x`, `6.x.x`, and `7.x.x` |
| [Ruby](../../scan-with-endorlabs/language-scanning/ruby/) | Bundler | `Gemfile`, `*.gemspec`, `gemfile.lock` | `.rb` | Ruby 2.6 and higher versions |
| [Swift/Objective-C](../../scan-with-endorlabs/language-scanning/swift-objective-c/) | CocoaPods | `Podfile`, `Podfile.lock` | `.swift`, `.h`, `.m` | CocoaPods 0.9.0 and higher versions |
|  | SwiftPM | `Package.swift` | `.swift`, `.h`, `.m` | SwiftPM 5.0.0 and higher versions |
| [PHP](../../scan-with-endorlabs/language-scanning/php/) | Composer | `composer.json`, `composer.lock` | `.php` | PHP 5.3.2 and higher versions; Composer 2.2.0 and higher versions |

Define supported languages when running endorctl `scan` command as a comma-separated list: `c,c#,go,java,javascript,kotlin,php,python,ruby,rust,scala,swift,typescript,swifturl`

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
