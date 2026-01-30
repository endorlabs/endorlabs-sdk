---
url: https://docs.endorlabs.com/getting-started/quickstart/quickstart-local-system/
title: Quick start with endorctl | Endor Labs Docs
downloaded: 2026-01-26 10:07:34
---

Quick start with endorctl | Endor Labs Docs



* Type to search...

[Print entire section](/getting-started/quickstart/quickstart-local-system/_print.html)



# Quick start with endorctl

Get up and running quickly with endorctl.

This guide provides step-by-step instructions to set up and configure an Endor Labs tenant while getting started with your first project scan in your local system.

Use the following steps to scan your first project with Endor Labs:

1. [Install Endor Labs on your local system](#install-endor-labs-on-your-local-system)
2. [Authenticate to Endor Labs](#authenticate-to-endor-labs)
3. [Clone your repository](#clone-your-repository)
4. [Scan your first project](#run-your-first-scan)
5. [Review your results](#review-the-results-of-your-project)

## Install Endor Labs on your local system

Install or update the Endor Labs CLI (endorctl) for your operating system.

### macOS

* Homebrew
* npm
* Apple Silicon Executable
* Intel Executable

```
brew tap endorlabs/tap
brew install endorctl
```

```
npm install -g endorctl

# Run the following command to get the npm global bin directory:
npm config get prefix

# Open your shell configuration file and insert the path you obtained with the above command:
export PATH="/path/to/npm/global/bin:$PATH"

# Reload your shell configuration and verify endorctl is installed:
endorctl --version
```

```
# Download the latest CLI for MacOS ARM64
curl https://api.endorlabs.com/download/latest/endorctl_macos_arm64 -o endorctl

# Verify the checksum of the binary
echo "$(curl -s https://api.endorlabs.com/sha/latest/endorctl_macos_arm64)  endorctl" | shasum -a 256 -c

# Modify the permissions of the binary to ensure it is executable
chmod +x ./endorctl

# Create an alias endorctl of the binary to ensure it is available in other directory
alias endorctl="$PWD/endorctl"
```

```
# Download the latest CLI for MacOS AMD64
curl https://api.endorlabs.com/download/latest/endorctl_macos_amd64 -o endorctl

# Verify the checksum of the binary
echo "$(curl -s https://api.endorlabs.com/sha/latest/endorctl_macos_amd64)  endorctl" | shasum -a 256 -c

# Modify the permissions of the binary to ensure it is executable
chmod +x ./endorctl

# Create an alias endorctl of the binary to ensure it is available in other directory
alias endorctl="$PWD/endorctl"
```

### Linux

* npm
* AMD64 Executable
* ARM64 Executable

```
npm install -g endorctl

# Run the following command to get the npm global bin directory:
npm config get prefix

# Open your shell configuration file and insert the path you obtained with the above command:
export PATH="/path/to/npm/global/bin:$PATH"

# Reload your shell configuration and verify endorctl is installed:
endorctl --version
```

```
# Download the latest CLI for Linux amd64
curl https://api.endorlabs.com/download/latest/endorctl_linux_amd64 -o endorctl

# Verify the checksum of the binary
echo "$(curl -s https://api.endorlabs.com/sha/latest/endorctl_linux_amd64)  endorctl" | sha256sum -c

# Modify the permissions of the binary to ensure it is executable
chmod +x ./endorctl

# Create an alias endorctl of the binary to ensure it is available in other directory
alias endorctl="$PWD/endorctl"
```

```
# Download the latest CLI for Linux arm64
curl https://api.endorlabs.com/download/latest/endorctl_linux_arm64 -o endorctl

# Verify the checksum of the binary
echo "$(curl -s https://api.endorlabs.com/sha/latest/endorctl_linux_arm64)  endorctl" | sha256sum -c

# Modify the permissions of the binary to ensure it is executable
chmod +x ./endorctl

# Create an alias endorctl of the binary to ensure it is available in other directory
alias endorctl="$PWD/endorctl"
```

### Windows

* npm
* Executable

```
npm install -g endorctl

# Run the following command to get the npm global bin directory:
npm config get prefix

# Add the path from the above command to the System property 'Path' in your Environment variable settings.

# Open a new Command prompt and verify endorctl is installed:
endorctl --version
```

```
# Download the latest CLI for Windows
curl -O https://api.endorlabs.com/download/latest/endorctl_windows_amd64.exe

# Check the expected checksum of the binary file
curl https://api.endorlabs.com/sha/latest/endorctl_windows_amd64.exe

# Verify the expected checksum and the actual checksum of the binary match
certutil -hashfile .\endorctl_windows_amd64.exe SHA256

# Rename the binary file
ren endorctl_windows_amd64.exe endorctl.exe
```

For more details, see [Install and configure endorctl](../../../endorctl/install-and-configure/)

## Authenticate to Endor Labs

Run `endorctl init` and your browser window will open automatically. Select your authentication provider from the available options and complete the authentication process. Endor Labs supports multiple identity providers, including Google, GitHub, GitLab, email link authentication, and a Custom Identity Provider through Enterprise SSO. Examples of enterprise SSO solutions include Google, GitHub, GitLab, or your organization’s specific provider.

![Authenticate to Endor Labs](../../../images/init-auth-mode.png)

For more information, see [Install and configure endorctl](../../../endorctl/install-and-configure/).

You can also specify your supported authentication provider manually:

* Google
* GitHub
* GitLab
* Email
* SSO

```
endorctl init --auth-mode=google
```

```
endorctl init --auth-mode=github
```

```
endorctl init --auth-mode=gitlab
```

```
endorctl init --auth-email=<insert_email_address>
```

```
endorctl init --auth-mode=sso --auth-tenant=<insert-your-tenant>
```

## Clone your repository

Upon successful authentication to Endor Labs using `endorctl`, proceed to clone the repository you intend to scan. If you prefer initiating with a dummy app for scanning, feel free to skip to the next step.

To clone a Git repository, use the `git clone` command followed by the clone link of the repository. You can find the URL on the repository’s page on a platform like GitHub or GitLab. For example,

```
git clone https://github.com/username/repo-name.git
```

Replace `https://github.com/username/repo-name.git` with the actual URL of the Git repository you want to clone.

Navigate to the repository you’ve cloned.

```
cd <repo-name>
```

## Run your first scan

Endor Labs supports three distinct scan types. See each section for instructions on how to run each scan type with Endor Labs.

* [Scan for OSS risk](#scan-for-oss-risk)
* [Scan for leaked secrets](#scanning-for-leaked-secrets)
* [Scan for GitHub misconfigurations](#scan-for-github-misconfigurations)

**Note**

When performing a scan, you can specify a [namespace](../../../endorctl/environment-variables/#global-flags-and-variables). If left unspecified, projects are created in the root namespace of the tenant. This is important if the user or token has restricted access to specific namespaces. See [Namespaces in Endor Labs](../../../administration/namespaces/) to learn more about namespaces.

### Scan for OSS risk

Follow these steps to scan with Endor Labs for open source risk:

1. [Install software prerequisites](#install-software-prerequisites)
2. [Clone your repository](#clone-your-repository)
3. [Build your software](#build-your-software)
4. [Scan with Endor Labs for OSS risk](#scan-your-project-for-oss-risk)

**Tip**

See the walkthrough on [scanning an example repository](#scanning-an-example-repository) using `endorctl` to learn how to perform a scan.

#### Install software prerequisites

The following prerequisites must be met to scan with Endor Labs for OSS risk:

* A local installation of Git or the ability to clone repositories in CI. See the [Git documentation for instructions on installing Git](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git)
* A runtime environment and build tools for supported software development languages your team uses must be installed on any system used for testing. For more information, see [Supported languages and frameworks](../../../scan-with-endorlabs/language-scanning/).

For more information on supported languages, package managers and build systems and the requirements for each language, see their respective page.

| Language | Package Managers / Build Tools | Manifest files | Runtime Requirements |
| --- | --- | --- | --- |
| [Java](../../../scan-with-endorlabs/language-scanning/java/) | Maven | `pom.xml` | JDK version 11-25; Maven 3.6.1 and higher versions |
|  | Gradle | `build.gradle` | JDK version 11-25; Gradle 6.0.0 and higher versions |
|  | Bazel | `workspace`, `MODULE.bazel`, `BUILD.bazel` | JDK version 11-25; Bazel versions `5.x.x`, `6.x.x`, and `7.x.x` |
| [Kotlin](../../../scan-with-endorlabs/language-scanning/kotlin/) | Maven | `pom.xml` | JDK version 11-25; Maven 3.6.1 and higher versions |
|  | Gradle | `build.gradle` | JDK version 11-25; Gradle 6.0.0 and higher versions |
| [Golang](../../../scan-with-endorlabs/language-scanning/golang/) | Go | `go.mod`, `go.sum` | Go 1.12 and higher versions |
|  | Bazel | `workspace`, `MODULE.bazel`, `BUILD.bazel` | Bazel versions `5.x.x`, `6.x.x`, and `7.x.x` |
| [Rust](../../../scan-with-endorlabs/language-scanning/rust/) | Cargo | `cargo.toml`, `cargo.lock` | Rust 1.63.0 and higher versions |
| [JavaScript](../../../scan-with-endorlabs/language-scanning/javascript/) | npm | `package-lock.json`, `package.json` | npm 6.14.18 and higher versions |
| [TypeScript](../../../scan-with-endorlabs/language-scanning/javascript/) | npm | `package-lock.json`, `package.json` | npm 6.14.18 and higher versions |
|  | Yarn | `yarn.lock`, `package.json` | Yarn all versions |
| [Python](../../../scan-with-endorlabs/language-scanning/python/) | pip | `requirements.txt` | Python 3.6 and higher versions; pip 10.0.0 and higher versions |
|  | Poetry | `pyproject.toml`, `poetry.lock` |  |
|  | PDM | `pyproject.toml`, `pdm.lock` |  |
|  | UV | `pyproject.toml`, `uv.lock` | Python 3.8 and higher versions |
|  | PyPI | `setup.py`, `setup.cfg`, `pyproject.toml` |  |
|  | Bazel | `workspace`, `MODULE.bazel` | Bazel versions `5.x.x`, `6.x.x`, and `7.x.x` |
| [.NET (C#)](../../../scan-with-endorlabs/language-scanning/dotnet/) | NuGet | `*.csproj`, `package.lock.json`, `projects.assets.json`, `Directory.Build.props`, `Directory.Packages.props`, `*.props` | .NET 5.0 and higher versions; .NET Core 1.0 and higher versions; .NET Framework 4.5 and higher versions. Call graphs are supported for .NET 7.0.1 and higher versions. |
| [Scala](../../../scan-with-endorlabs/language-scanning/scala/) | sbt | `build.sbt` | sbt 1.3 and higher versions |
|  | Gradle | `build.gradle`, `build.gradle.kts` | JDK version 11-25; Gradle 6.0.0 and higher versions |
| [Ruby](../../../scan-with-endorlabs/language-scanning/ruby/) | Bundler | `Gemfile`, `*.gemspec`, `gemfile.lock` | Ruby 2.6 and higher versions |
| [Swift/Objective-C](../../../scan-with-endorlabs/language-scanning/swift-objective-c/) | CocoaPods | `Podfile`, `Podfile.lock` | CocoaPods 0.9.0 and higher versions |
|  | SwiftPM | `Package.swift` | SwiftPM 5.0.0 and higher versions |
| [PHP](../../../scan-with-endorlabs/language-scanning/php/) | Composer | `composer.json`, `composer.lock` | PHP 5.3.2 and higher versions; Composer 2.2.0 and higher versions |

For more information, see [endorctl commands](../../../endorctl/commands/) and [working with the API](../../../endorctl/commands/api/).

#### Build your software

To run a complete and accurate scan with Endor Labs, ensure that the software can be successfully built, incorporating well-formatted manifest files. To maximize the benefits of an Endor Labs OSS scan, you should perform a comprehensive testing as a post-build step, either locally or in a CI pipeline. Use the following commands to verify that the software can be built successfully with well-formatted manifest files before initiating the scan.

* Java (Maven)
* Java (Gradle)
* JavaScript (npm)
* JavaScript (yarn)
* JavaScript (pnpm)
* .NET (dotnet)
* PHP (composer)
* Golang
* Python (pip)
* Python (poetry)
* Ruby (bundler)
* Swift/Objective-C
* Scala (sbt)
* Scala (Gradle)
* Rust (Cargo)

```
mvn dependency:tree
mvn clean install
```

```
gradle dependencies --configuration runtimeClasspath
./gradlew assemble
# Use `gradle assemble` if you do not have a gradle wrapper in your repository
```

```
npm install
```

```
yarn install
```

```
pnpm install
```

```
dotnet restore
dotnet build
```

```
composer install
```

```
go mod tidy
```

```
python3 -m venv venv
source venv/bin/activate
venv/bin/python3 -m pip install
```

```
poetry install
```

```
bundler install
```

```
pod install
```

```
sbt projects
sbt compile
sbt dependencyTree
```

```
gradle dependencies --configuration runtimeClasspath
./gradlew assemble
# Use `gradle assemble` if you do not have a gradle wrapper in your repository
```

```
cargo build
```

#### Scan your project for OSS risk

To scan and monitor all packages in a given repository from the root of the repository, run the following command:

```
endorctl scan
```

If your project contains multiple programming languages, you can specify them as a comma-separated list using the `--languages` flag:

```
endorctl scan --languages=<languages-list>
```

Where `<languages-list>` should be provided as a comma-separated list from the supported languages: `c,c#,go,java,javascript,kotlin,php,python,ruby,rust,scala,swift,typescript,swifturl`.

#### Scanning an example repository

To scan an example repository `https://github.com/OWASP-Benchmark/BenchmarkJava.git`, you must perform the following steps after [successfully authenticating](#authenticate-to-endor-labs) to Endor Labs:

1. Clone the repository `https://github.com/OWASP-Benchmark/BenchmarkJava.git`

   ```
   git clone https://github.com/OWASP-Benchmark/BenchmarkJava.git
   ```
2. Navigate to the repository on your local system

   ```
   cd BenchmarkJava
   ```
3. Build the repositories package with Maven:

   ```
   mvn clean install
   ```
4. Scan the repository

   ```
   endorctl scan
   ```

### Scanning for leaked secrets

The following procedure should be used to scan with Endor Labs for potential secrets leaked into your source code.

To scan for all potentially leaked secrets in the checked out branch of your repository, run the following command:

```
endorctl scan --secrets
```

Often, secrets are leaked outside the context of your repositories main branch and can be found in older branches or those that are under active development. To identify these, Endor Labs inspects the Git logs of the repository.

To scan for all potentially leaked secrets in all branches of your repository, run the following command:

```
endorctl scan --secrets --git-logs
```

### Scan for GitHub misconfigurations

Endor Labs allows teams to scan their repository for configuration best practices in alignment with organizational policy.

#### Pre-requisites

To scan the GitHub repository, you must have:

* The GitHub repository HTTPS clone URL
* A personal access token with access administrative access to the repository. For help creating a personal access token see [GitHub documentation](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens).

If you are on a self-hosted GitHub Enterprise Server, you should also have:

* The GitHub API URL (This is typically the FQDN of the GitHub server)
* A local copy of the CA Certificate if the certificate is self-signed or from a private CA

#### Running a misconfiguration scan

To scan a GitHub repository for misconfigurations:

1. Export your personal access token as an environment variable:

   ```
   export GITHUB_TOKEN=<personal_access_token>
   ```
2. Scan the repository to retrieve configuration information and analyze the configuration against organizational policy or configuration best practices:

   ```
   endorctl scan --repository-http-clone-url=https://github.com/<organization>/<repository>.git --github
   ```

For source control systems on the GitHub Enterprise Server, you must set the `--github-api-url` flag to your GitHub Enterprise server domain name:

```
endorctl scan --github-api-url=https://<fully_qualified_domain_name_to_GitHub_Enterprise_Server> --repository-http-clone-url=https://<fully_qualified_domain_name_to_GitHub_Enterprise_Server>/<organization>/<repository>.git --github
```

## Review the results of your project

* Sign in to the [Endor Labs user interface](https://app.endorlabs.com), click **Projects** on the left sidebar.
* The Findings section provides a summary of vulnerabilities found in each project, categorized by severity:

  + C: Critical
  + H: High
  + M: Medium
  + L: Low
* Under **Packages**, the number indicates the identified packages. Click on the icon next to the number to open a right sidebar containing the following details :

  + Project metadata: Information such as UUID, repository details, dependencies, and repository versions.
  + Findings: A breakdown of the detected vulnerabilities categorized by dependency, package, repository, secrets, and CI workflows.
  + Tools used during analysis: A list of tools involved in the scanning process.
* Select your project to view its details. See [Findings](../../../managing-projects/view-findings/) for more information.

![Locally Scanned Project](../../../images/locally-scanned-project.png)

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
