---
url: https://docs.endorlabs.com/scan-with-endorlabs/language-scanning/scala/
title: Scala | Endor Labs Docs
downloaded: 2025-10-23 23:27:58
---

Scala | Endor Labs Docs



* Type to search...
* ---

[Print entire section](/scan-with-endorlabs/language-scanning/scala/_print.html)



# Scala

Learn how to implement Endor Labs in repositories with Scala packages.

Scala is a general-purpose and scalable programming language widely used by developers. Endor Labs supports the scanning and monitoring of Scala projects managed by the interactive build tool sbt.

Using Endor Labs, application security engineers and developers can:

* Scan their software for potential security issues and violations of organizational policy.
* Prioritize vulnerabilities in the context of their applications.
* Understand the relationships between software components in their applications.

## System specifications for scan

Make sure that your system has a minimum 8-core processor with 32 GB RAM to successfully scan Scala projects.

## Software prerequisites

The following prerequisites must be fulfilled:

* A manifest file for the Scala build tool, **build.sbt** must be present in your repository.
* Make sure your repository includes one or more files with `.sc` or `.scala` extension.
* If your sbt version is lower than 1.4, you must install the [sbt-dependency-graph](https://github.com/sbt/sbt-dependency-graph) plugin. The sbt-dependency-graph plug-in is by default integrated into the sbt versions 1.4 and higher.
* Make sure that the project/build.properties file has the required sbt version.

### Option 1 - Quick scan

You must be able to build your Scala projects before running a scan. The standard `.sbt` cache must exist and contain successfully downloaded dependencies.

1. Ensure your repository has a `build.sbt` file and run the following commands making sure it builds the project successfully.

   ```
   sbt compile
   ```

   ```
   sbt projects
   ```
2. Make sure `sbt dependencyTree` runs successfully inside the project directory.

## Run a scan

Perform a scan to get visibility into your software composition and resolve dependencies.

```
endorctl scan
```

You can perform the scan from within the root directory of the Git project repository, and save the local results to a *results.json* file. The results and related analysis information are available on the Endor Labs user interface.

```
endorctl scan -o json | tee /path/to/results.json
```

You can sign into the [Endor Labs user interface](https://app.endorlabs.com), click the **Projects** on the left sidebar, and find your project to review its results.

### Option 2 - Deep scan

You must be able to build your Scala projects before running a scan. The build artifact as well as the standard .sbt cache must exist and contain successfully downloaded dependencies.

1. Ensure your repository has a `build.sbt` file and run the following commands making sure it builds the project successfully.

   ```
   sbt package
   ```

   ```
   sbt projects
   ```
2. Make sure `sbt dependencyTree` runs successfully inside the project directory.

## Run a scan

Perform a scan to get visibility into your software composition and resolve dependencies.

```
endorctl scan
```

You can perform the scan from within the root directory of the Git project repository, and save the local results to a *results.json* file. The results and related analysis information are available on the Endor Labs user interface.

```
endorctl scan -o json | tee /path/to/results.json
```

You can sign into the [Endor Labs user interface](https://app.endorlabs.com), click the **Projects** on the left sidebar, and find your project to review its results.

## Understand the scan process

Endor Labs scans Scala projects by executing sbt plugins and inspecting the build.sbt file to retrieve information about direct and transitive dependencies.

* The build.sbt file is a configuration file used in Scala projects with sbt to define project settings, dependencies, and build tasks. This file provides the necessary configuration and instructions to sbt on resolving and managing project dependencies.
* The sbt dependency graph plugin visualizes the dependencies between modules in a Scala project.

Endor Labs analyzes information from both these methods to determine different components, binary files, manifest files, images, and more in the Scala codebase and presents finding policy violations, identifying, and resolving dependencies.

Using Endor Labs users can gain significant insights into the structure and relationships of their Scala project’s dependencies, aiding in managing dependencies effectively, identifying potential issues, and ensuring a well-organized and maintainable codebase.

### How Endor Labs performs static analysis on the code

Endor Labs performs static analysis based on the following factors:

* Call graphs are created for your package. These are then combined with the call graphs of the dependencies in your dependency tree to form a comprehensive call graph for the entire project.
* Endor Labs performs an inside-out analysis of the software to determine the reachability of dependencies in your project.
* The static analysis time may vary depending on the number of dependencies in the package and the number of packages in the project.

### Known Limitations

* Software composition analysis for Scala on Microsoft Windows operating systems is currently unsupported.
* Scala packages built with Gradle are not currently supported.

## Troubleshoot errors

Here are a few error scenarios that you can check for and attempt to resolve them.

* **Host system check failure errors**: These errors occur if:
  + If sbt is not installed or present in the path variable. Install sbt 1.4 or higher versions and try again.
  + If the sbt version mentioned in the project or the `build.properties` file is lower than 1.4 and the `sbt-dependency-graph` plug-in is not installed. Install the `sbt-dependency-graph` plug-in and try again.
* **Dependency graph errors** - Scala by default imports `MiniDependencyTreePlugin` which is a mini version of the `sbt-dependency-graph` plugin and it supports only `dependencyTree` command. To get complete features of the `sbt-dependency-graph` plugin, add `DependencyTreePlugin` to your `project/plugins.sbt` file and run the scan again. See [Scala documentation](https://eed3si9n.com/sbt-1.4.0#:~:text=sbt%2Ddependency%2Dgraph%20is%20in%2Dsourced) for details.

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
