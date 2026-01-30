---
url: https://docs.endorlabs.com/scan-with-endorlabs/language-scanning/scala/
title: Scala | Endor Labs Docs
downloaded: 2026-01-26 10:09:07
---

Scala | Endor Labs Docs



* Type to search...

[Print entire section](/scan-with-endorlabs/language-scanning/scala/_print.html)



# Scala

Learn how to implement Endor Labs in repositories with Scala packages.

Scala is a general-purpose and scalable programming language widely used by developers. Endor Labs supports the scanning and monitoring of Scala projects managed by either the interactive build tool sbt or Gradle.

Using Endor Labs, application security engineers and developers can:

* Scan their software for potential security issues and violations of organizational policy.
* Prioritize vulnerabilities in the context of their applications.
* Understand the relationships between software components in their applications.

## System specifications for scan

Make sure that your system has a minimum 8-core processor with 32 GB RAM to successfully scan Scala projects.

## Software prerequisites

* Install JDK versions between 11 and 25.0.1.
  + For JDK 8, see [Scan projects on JDK version 8](../java/#scan-the-projects-on-jdk-version-8).
* Make sure your repository includes one or more files with `.scala` or `.sc` extension.
* Install sbt version 1.4 or higher if your project uses sbt.
  + For sbt versions lower than 1.4, install the [sbt-dependency-graph](https://github.com/sbt/sbt-dependency-graph) plugin, which is included by default in sbt 1.4 and later.
  + Ensure that the `project/build.properties` file specifies the required sbt version.
* Install Gradle build system version 6.0.0 and higher, if your project uses Gradle.
  + To support lower versions of Gradle, see [Scan projects on older Gradle versions](../java/#scan-projects-on-gradle-versions-between-47-and-600).
* Your repository must include the appropriate build manifest file:
  + `build.sbt` for sbt projects.
  + `build.gradle` or `build.gradle.kts` for Gradle projects.

## Build Scala projects

Before initiating a scan with Endor Labs, ensure that your Scala projects are built successfully. Additionally, ensure that the packages are downloaded into local package caches and build artifacts are present in their standard locations. Follow the guidelines to build projects using sbt or Gradle.

### Use Gradle

To analyze your software built with Gradle, you must successfully build the software. To perform a quick scan, locate the dependencies in the local package manager cache. Ensure that the standard `$GRADLE_USER_HOME/caches` or `/User/<username>/.gradle/caches` exists and contains successfully downloaded dependencies. To perform a deep scan, generate the target artifact on the file system as well.

To build your project with Gradle, use the following procedure:

1. To run a scan against a custom configuration, specify the Gradle configuration by setting an environment variable.

   ```
      export endorGradleScalaConfiguration="<configuration>"
   ```

   When no configuration is provided, `runtimeClasspath` is used by default.

   If neither the user-specified nor the default configuration exists in the project, the system falls back to the following configurations, in order:

   1. `runtimeClasspath`
   2. `runtime`
   3. `compileClasspath`
   4. `compile`

   If the listed configurations are not found in the project, the system selects the first available configuration in alphabetical order.
2. Ensure that you can resolve the dependencies for your project without errors by running the following command:

   For Gradle wrapper:

   ```
      ./gradlew dependencies
   ```

   For Gradle:

   ```
      gradle dependencies
   ```
3. Run `./gradlew assemble` or `gradle assemble` to resolve dependencies and to create an artifact that may be used for deep analysis.

#### Override subproject level configuration

In a multi-build project, if you set the environment variable `endorGradleScalaConfiguration=[GlobalConfiguration]`, the specified configuration is used for dependency resolution across all projects and subprojects in the hierarchy below.

```
\--- Project ':samples'
     +--- Project ':samples:compare'
     +--- Project ':samples:crawler'
     +--- Project ':samples:guide'
     +--- Project ':samples:simple-client'
     +--- Project ':samples:slack'
     +--- Project ':samples:static-server'
     +--- Project ':samples:tlssurvey'
     \--- Project ':samples:unixdomainsockets'
```

To override the configuration only for the `:samples:crawler` and `:samples:guide` subprojects, follow these steps:

1. Navigate to the root workspace, where you execute `endorctl scan`, and run `./gradlew projects` to list all projects and their names.
2. Run the following command at the root of the workspace:

   ```
   echo ":samples:crawler=testRuntimeClasspath,:samples:guide=macroBenchMarkClasspath" >> .endorproperties
   ```

   This creates a new file named `.endorproperties` in your root directory. This enables different configurations for the specified subprojects in the file.
3. Run `endorctl scan`.

At this point, all other projects will adhere to the `GlobalConfiguration`. However, the `:samples:crawler` subproject will use the `testRuntimeClasspath` configuration, and the `:samples:guide` subproject will use the `macroBenchMarkClasspath` configuration.

#### Configure private Gradle package repositories

Endor Labs supports fetching and scanning dependencies from private Gradle package registries. Endor Labs will fetch resources from authenticated endpoints and perform the scan, allowing you to view the resolved dependencies and findings. See [Gradle package manager integrations](../../../integrations/package-manager/gradle-private-package-manager/) for more information on configuring private registries.

### Use sbt

To analyze your software built with sbt, you must successfully build the software.

* The standard `.sbt` cache must exist and contain all required dependencies for both quick and deep scans.
* For deep scans, the build artifact must exist on the filesystem.
* Make sure `sbt dependencyTree` runs successfully inside the project directory.

#### Quick scan

Run a quick scan to rapidly assess your dependencies using only the compiled code and cached packages.

1. Run the following commands to build the project successfully. Ensure your repository has a `build.sbt` file.

   ```
   sbt compile
   ```

   ```
   sbt projects
   ```
2. [Run an endorctl scan](#run-a-scan).

#### Deep scan

Run a deep scan to enable advanced static analysis features by generating packaged artifacts.

1. Run the following commands to build the project successfully. Ensure your repository has a `build.sbt` file.

   ```
   sbt package
   ```

   ```
   sbt projects
   ```
2. [Run an endorctl scan](#run-a-scan).

## Run a scan

Run an endorctl scan to get visibility into your software composition and resolve dependencies.

```
endorctl scan
```

You can perform the scan from within the root directory of the Git project repository and save the local results to a *results.json* file. The results and related analysis information are available on the Endor Labs user interface.

```
endorctl scan -o json | tee /path/to/results.json
```

Sign in to the [Endor Labs user interface](https://app.endorlabs.com), click **Projects** on the left sidebar, and find your project to review its results.

**Note**

If your project includes both sbt and Gradle build systems, Endor Labs scans your project using only one build system to avoid scanning the same packages multiple times. When both are present, Gradle has higher priority for dependency resolution.

## Understand the scan process

Endor Labs scans Scala projects by executing sbt plugins and inspecting the `build.sbt` file to retrieve information about direct and transitive dependencies.

* The `build.sbt` file is a configuration file used in Scala projects with sbt to define project settings, dependencies, and build tasks. This file provides the necessary configuration and instructions to sbt on resolving and managing project dependencies.
* The sbt dependency graph plugin visualizes the dependencies between modules in a Scala project.
* For packages built using Gradle, it uses Gradle and Gradle wrapper files to build packages and resolve dependencies.
* Endor Labs supports EAR, JAR, RAR, and WAR files.

Endor Labs analyzes information from both these methods to determine different components, binary files, manifest files, images, and more in the Scala codebase. It presents finding policy violations, identifies dependencies, and resolves them.

Using Endor Labs, users can gain significant insights into the structure and relationships of their Scala project’s dependencies. This aids in managing dependencies effectively, identifying potential issues, and ensuring a well-organized and maintainable codebase.

### How Endor Labs performs static analysis on the code

Endor Labs performs static analysis based on the following factors:

* Call graphs are created for your package. These are then combined with the call graphs of the dependencies in your dependency tree to form a comprehensive call graph for the entire project.
* Endor Labs performs an inside-out analysis of the software to determine the reachability of dependencies in your project.
* The static analysis time may vary depending on the number of dependencies in the package and the number of packages in the project.

### Known limitations

Endor Labs does not currently support software composition analysis for Scala on Microsoft Windows operating systems.

## Troubleshoot errors

Here are a few error scenarios that you can check for and attempt to resolve them.

* **Host system check failure errors**: These errors occur if:
  + sbt is not installed or present in the path variable. Install sbt 1.4 or higher versions and try again.
  + The sbt version mentioned in the project or the `build.properties` file is lower than 1.4 and the `sbt-dependency-graph` plug-in is not installed. Install the `sbt-dependency-graph` plug-in and try again.
  + Java is not installed or not present in the PATH environment variable. Install Java and try again. See [Java documentation](https://www.oracle.com/java/technologies/downloads/) for more information.
  + The installed version of Java is lower than the required version. Install JDK versions between 11 and 25.0.1 and try again.
  + Java is installed but sbt or Gradle is not installed. In such cases, the dependency resolution may not be complete.
* **Dependency graph errors**: Scala by default imports `MiniDependencyTreePlugin`, which is a mini version of the `sbt-dependency-graph` plugin and supports only the `dependencyTree` command. To get complete features of the `sbt-dependency-graph` plugin, add `DependencyTreePlugin` to your `project/plugins.sbt` file and run the scan again. See [Scala documentation](https://eed3si9n.com/sbt-1.4.0#:~:text=sbt%2Ddependency%2Dgraph%20is%20in%2Dsourced) for details.

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
