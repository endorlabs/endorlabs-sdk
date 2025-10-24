---
url: https://docs.endorlabs.com/scan-with-endorlabs/manage-scan-profiles/auto-detect-toolchains/
title: Enable auto detection | Endor Labs Docs
downloaded: 2025-10-23 23:25:36
---

Enable auto detection | Endor Labs Docs



* Type to search...
* ---

[Print entire section](/scan-with-endorlabs/manage-scan-profiles/auto-detect-toolchains/_print.html)



# Enable auto detection

Learn how to automatically detect toolchains used in your repository.

The system can automatically detect toolchains required for your projects based on the manifest files present in your repository. Auto detection is supported for Java, Python, Go and .NET(C#) projects. Only the Long Term Support (LTS) versions of the toolchains are supported in auto detection. See the [Toolchain support matrix](../build-tools/#toolchain-support-matrix) for a complete list of supported toolchain versions for auto detection.

### How auto detection works

Endor Labs begins auto detection by scanning your project repository to locate manifest files and identify the languages used in your project. Based on the results, it runs language specific detectors to extract version information. Each detector operates independently and follows a consistent process. It reviews the associated manifest or build configuration files to determine the toolchain version. If a file contains multiple version fields, the detector uses a fixed priority order to select the most appropriate one.

After identifying a version, the detector sends the version details to the assigner. The assigner checks the Endor Labs toolchain support matrix to verify if the version is supported for the host operating system and architecture. If it doesn’t find an exact match, it selects the closest supported version based on the major version number. This version will be the toolchain used for your project scan.

For example, when analyzing Java projects, the Java detector checks config files like `pom.xml` or `build.gradle` to find the Java version used in the project.

```
flowchart TD
  subgraph C["Detectors find versions of detected languages"]
    L1["language 1 detector"]
    Lang["..."]
    L2["language n detector"]
  end
  A(["Scan Repository"])
  B["Detect Languages"]
  D["Assigners"]
  F{"Exact match"}
  G(["Select closest supported version by matching major version"])
  H(["Select exact supported version"])
  I["Yes"]
  J["No"]
  K["Match version with Endor Labs suported versions"]

  A --> B --> C --> D --> K --> F
  F --> I --> H
  F --> J --> G

  %% Force black border on subgraph
  classDef subgraphStyle stroke:#000000,stroke-width:1px,fill:#00F078;
  class C subgraphStyle
  classDef JavaStyle fill:#D3D3D3;
  class L1,L2,Lang JavaStyle
  classDef blueText fill:#3FE1F3,stroke:#000000,color:#000000;
  class I,J,K blueText

  %% NEW: Bigger node style and class
  classDef largeNode fill:#00F078,stroke:#000000,color:#000000;
  class A,B,D,E largeNode

  %% Optional: force large box padding via dummy <br> line
  style C width:520px
```

### Config files scanned for version detection

The following table lists the config files Endor Labs scans to detect the language and version used in your project.

| Language | Build Tool | Config File |
| --- | --- | --- |
| Java | Maven | `pom.xml` |
| Java | Gradle | `build.gradle`, `gradle-wrapper.properties` |
| .NET |  | `global.json`, `*.csproj` |
| Golang |  | `go.mod` |
| Python |  | `setup.py`, `.python-version`, `pyproject.toml` |
| NodeJS |  | `package.json`, `.nvmrc`, `.node-version` |
| Yarn |  | `package.json`, `.yarnrc.yml`, `yarnrc` |
| pnpm |  | `package.json` |

The following examples illustrate how to define versions in each config file.

Java with Maven

Config file: `pom.xml`

Define the Java version using any one of the following options:

* Using version fields

  ```
  <properties>
    <maven.compiler.source>1.8</maven.compiler.source>
    <maven.compiler.target>1.8</maven.compiler.target>
    <maven.compiler.release>11</maven.compiler.release>
    <java.version>17</java.version>
  </properties>
  ```
* Using plugin configuration

  ```
  <build>
    <plugins>
      <plugin>
        <artifactId>maven-compiler-plugin</artifactId>
        <version>3.8.1</version>
        <configuration>
        <source>11</source>
        <target>11</target>
        </configuration>
      </plugin>
    </plugins>
  </build>
  ```




Java with Gradle

Config file: `build.gradle`

Define the Java version using `sourceCompatibility` and `targetCompatibility`.

```
sourceCompatibility='17'
targetCompatibility='17'
```

Ensure the Gradle wrapper version is defined in `gradle/wrapper/gradle-wrapper.properties`.

```
distributionUrl=https\://services.gradle.org/distributions/gradle-7.6-all.zip
```




Python

Specify the Python version in any of the following config files.

setup.py

Use `python_requires` inside the `setup()` block.

```
setup(
    ...
    python_requires='>=3.8, <4'
)
```




pyproject.toml

Use `requires-python` to define the Python version range.

```
[project]
requires-python = ">=3.8, <4.0"

[tool.poetry.dependencies]
python = "3.12.1"
```




.python-version

Specify the exact Python version.

```
3.12.1
```




Node.js

Specify the NodeJS version in any of the following config files.

package.json

Use `engines.node`

```
"engines": {
  "node": ">=16.0.0 <19"
}
```




.nvmrc

Specify the exact NodeJS version.

```
18.17.1
```




.node-version

Specify the exact NodeJS version.

```
18.17.1
```




Yarn

Specify the Yarn version in any of the following config files.

package.json

Use `engines.yarn`

```
"engines": {
  "yarn": ">=1.22.0 <2.0.0"
}
```




.yarnrc.yml

Use `yarnPath`

```
yarnPath: ".yarn/releases/yarn-3.2.1.cjs"
```




.yarnrc

Use `yarnPath`

```
yarnPath: ".yarn/releases/yarn-3.2.1.cjs"
```




PNPM

Config file: `package.json`

Specify the pnpm version using `engines.pnpm`

```
"engines": {
  "pnpm": ">=6.0.0"
}
```




.NET

Specify the .NET version using any of the following config files.

global.json

Use `sdk.version`

```
{
  "sdk": {
    "version": "7.0.203"
  }
}
```




\*.csproj

Use `TargetFramework` or `TargetFrameworks`

```
<TargetFramework>net6.0</TargetFramework>
```




Golang

Config file: `go.mod`

Use the `go` directive.

```
module github.com/example/project

go 1.21
```

#### Note

Auto detection is best-effort and works only if your project’s config files are correctly configured.

### Enable auto detection for endorctl scans

To enable auto detection for endorctl scans, run:

```
endorctl scan --install-build-tools --enable-build-tools-version-detection
```

#### Warning

Enabling these options downloads the necessary build toolchains during each scan. This works well for one-time scans but may cause scan failures in CI environments due to intermittent network issues.

### Enable auto detection in GitHub App

When using the GitHub App, you can enable auto detection either by a project or enable it for all projects in a tenant.

* To enable the auto detection by a project, update the project’s `meta.annotations` with `"ENDOR_SCAN_ENABLE_BUILD_TOOLS_VERSION_DETECTION":"true"`.

  ```
  meta:
    annotations: {"ENDOR_SCAN_ENABLE_BUILD_TOOLS_VERSION_DETECTION":"true"}
  ```

  ```
    endorctl api update -r Project --uuid=<project-uuid> -i
  ```
* To enable auto detection across all projects in a tenant, update the system config’s `meta.annotations` with `"ENDOR_SCAN_ENABLE_BUILD_TOOLS_VERSION_DETECTION":"true"`.

  ```
  meta:
    annotations: {"ENDOR_SCAN_ENABLE_BUILD_TOOLS_VERSION_DETECTION":"true"}
  ```

  ```
  endorctl api update -r SystemConfig --uuid=<system-config-uuid> -i
  ```

The updates are applied during the next scheduled scan or whenever you perform a manual re-scan.

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
