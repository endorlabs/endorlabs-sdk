---
url: https://docs.endorlabs.com/scan-with-endorlabs/language-scanning/kotlin/
title: Kotlin | Endor Labs Docs
downloaded: 2026-02-03 00:50:01
---

Kotlin | Endor Labs Docs



* Type to search...

[Print entire section](/scan-with-endorlabs/language-scanning/kotlin/_print.html)



# Kotlin

Learn how to implement Endor Labs in repositories with Kotlin packages.

Kotlin is a statically typed programming language that runs on the Java Virtual Machine (JVM), known for its concise syntax, null safety, and seamless integration with Java. Endor Labs supports scanning and monitoring of Kotlin projects.

Using Endor Labs, application security engineers and developers can:

* Scan their software for potential security issues and violations of organizational policy.
* Prioritize vulnerabilities in the context of their applications.
* Understand the relationships between software components in their applications.

## System specifications for deep scan

Before you proceed to run a deep scan, ensure that your system meets the following specification.

| Project Size | Processor | Memory |
| --- | --- | --- |
| Small projects | 4-core processor | 16 GB |
| Mid-size projects | 8-core processor | 32 GB |
| Large projects | 16-core processor | 64 GB |

## Software Prerequisites

* Install JDK versions between 11 and 25.0.1.
  + For JDK 8, see [Scan projects on JDK version 8](#scan-the-projects-on-jdk-version-8).
* Make sure your repository includes one or more files with `.kt` extension.
* Install Maven version 3.6.1 and higher if your project uses Maven.
* Install Gradle build system version 6.0.0 and higher, if your project uses Gradle.
  + To support lower versions of Gradle, see [Scan projects on older Gradle versions](../java/#scan-projects-on-gradle-versions-between-47-and-600).
* Your repository must include the appropriate build manifest file:
  + `pom.xml` for Maven projects.
  + `build.gradle` or `build.gradle.kts` for Gradle projects.

## Build Kotlin projects

Before initiating a scan with Endor Labs, ensure that your Kotlin projects are built successfully. Additionally, ensure that the packages are downloaded into local package caches and build artifacts are present in their standard locations. Follow the guidelines to use Gradle and Maven:

### Use Gradle

To analyze your software built with Gradle, Endor Labs requires:

* The software must be successfully built with Gradle.
* For quick scans, dependencies must be located in the local package manager cache. The standard `$GRADLE_USER_HOME/caches or /User/<<username>>/.gradle/caches` cache must exist.
* For deep scans, the target artifact must be generated on the filesystem.

To build your project with Gradle, run the following commands:

1. Specify the Gradle configuration by setting an environment variable.

```
export endorGradleKotlinConfiguration="compileClasspath"
```

To override the default configuration, use the command:

```
export endorGradleKotlinConfiguration="<configuration>"
```

When no configuration is provided, `runtimeClasspath` is used by default.

If neither the user-specified nor the default configuration exists in the project, the system falls back to the following configurations, in order:

1. `runtimeClasspath`
2. `runtime`
3. `compileClasspath`
4. `compile`

If the listed configurations are not found in the project, the system selects the first available configuration in alphabetical order.

**For Android projects**, you can set the configuration using:

```
export endorGradleAndroidConfiguration="<configuration>"
```

The default configuration for an Android application or library follows the structure used by Android Studio.

Applications: All possible combinations of application variants are examined.

Libraries: All possible combinations of library variants are examined.

The first variant in the alphabetically sorted list is then suffixed with `RuntimeClasspath`. For example, if the first variant is `configA`, the default configuration will be `configARuntimeClasspath`.

If these methods don’t yield a value, the system defaults to `releaseRuntimeClasspath`.

2. Confirm an error-free dependency resolution for your project.

```
gradle dependencies
```

or, with a Gradle wrapper.

```
./gradlew dependencies
```

3. Generate the artifact for deep analysis.

```
gradle assemble
```

or, with a Gradle wrapper.

```
./gradlew assemble
```

#### Override sub project level configuration

In a multi-build project, if you set the environment variable `endorGradleKotlinConfiguration=[GlobalConfiguration]` and/or `endorGradleAndroidConfiguration=[GlobalConfiguration]`, the specified configuration is used for dependency resolution across all projects and sub-projects in the hierarchy below.

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

To override the configuration only for the `:samples:crawler` and `:samples:guide` sub-projects, follow these steps:

1. Navigate to the root workspace, where you execute `endorctl scan`, and run `./gradlew projects` to list all projects and their names.
2. Run the following command at the root of the workspace:

```
echo ":samples:crawler=testRuntimeClasspath,:samples:guide=macroBenchMarkClasspath" >> .endorproperties
```

This creates a new file named `.endorproperties` in your root directory. This enables different configurations for the specified sub-projects in the file.

3. Run `endorctl scan` as usual.

At this point, all other projects will adhere to the `GlobalConfiguration`. However, the `:samples:crawler` sub-project will use the `testRuntimeClasspath` configuration, and the `:samples:guide` sub-project will use the `macroBenchMarkClasspath` configuration.

### Use Maven

To analyze your software built with Maven, Endor Labs requires:

* The software must be successfully built with Maven.
* For quick scans, dependencies must be located in the local package manager cache. The standard `.m2` cache must exist.
* For deep scans, the target artifact must be generated on the filesystem.

To build your project with Maven, run the following commands:

1. Confirm an error-free dependency resolution for your project.

```
mvn dependency:tree
```

2. Run `mvn install` and ensure the build is successful.

**info**

If you want to skip the execution of tests during the build, you can use `-DskipTests` to quickly build and install your projects.

```
mvn install -DskipTests
```

3. If you have multiple Kotlin modules not referenced in the root **pom.xml** file, ensure to run `mvn install` separately in each directory.

### Configure Maven private registries

Endor Labs supports fetching and scanning dependencies from private Maven package registries. Endor Labs will fetch resources from authenticated endpoints and perform the scan, allowing you to view the resolved dependencies and findings. See [Maven package manager integrations](../../../integrations/package-manager/maven-private-package-manager/) for more information on configuring private registries.

## Run a scan

To scan your repositories with Endor Labs, you can use the following options after building your Kotlin projects.

### Option 1 - Quick scan

To quickly gain insight into your software composition, initiate a quick scan using the following command:

```
endorctl scan --quick-scan
```

This scan offers a quick overview without performing reachability analysis, helping you prioritize vulnerabilities.

#### Save local results

To scan a Git project repository from the root directory and save the results locally in the results.json file, use the following command:

```
endorctl scan --quick-scan -o json | tee /path/to/results.json
```

This generates comprehensive results and analysis information, accessible from the Endor Labs user interface.

#### Access results

To access and review detailed results, sign in to the [Endor Labs user interface](https://app.endorlabs.com). Navigate to **Projects** on the left sidebar, and locate your project for a thorough examination of the scan results.

### Option 2 - Deep scan

To perform dependency resolution and reachability analysis, use deep scan with Endor Labs. This option is recommended only after successfully completion of quick scan.

```
endorctl scan
```

#### Save local scan results

To save the local results to a *results.json* file, use the following flag.

```
endorctl scan -o json | tee /path/to/results.json
```

This generates comprehensive results and analysis information, accessible from the Endor Labs user interface.

#### Analyze private packages

During deep analysis, Endor Labs thoroughly analyzes all private software dependencies that have not been previously scanned. While this initial operation may slow down scans, subsequent scans remain unaffected.

If your organization does not own specific software parts and related findings are non-actionable, you can choose to disable this analysis using the `disable-private-package-analysis` flag. Disabling private package analysis enhances scan performance but may result in a loss of insights into how applications interact with first-party libraries.

To disable private package analysis, use the following command flag:

```
endorctl scan --disable-private-package-analysis
```

#### Access scan results

To access and review detailed results, sign in to the [Endor Labs user interface](https://app.endorlabs.com). Navigate to **Projects** on the left sidebar, and locate your project for a thorough examination of the scan results.

### Scan the projects on JDK version 8

While Endor Labs primarily supports JDK versions between 11-25.0.1, you can still scan projects on JDK 8 by following these steps:

1. Build your Java project on JDK 8.
2. After successful build, switch your Java home to JDK 11 or higher versions.

```
export JAVA_HOME=/Library/Java/JavaVirtualMachines/openjdk-11.jdk/Contents/Home
```

3. Run a scan.

## Understand the scan process

Endor Labs analyzes your Kotlin code and dependencies to identify known security issues, including open-source vulnerabilities.

### How Endor Labs resolves dependencies for package versions

Endor Labs resolves Kotlin package dependencies by considering the following factors:

* For packages built with Maven, it leverages the Maven cache in the `.m2` directory of your file system. This mirrors Maven’s build process for precise results.
* For packages built with Maven, it respects the configuration settings present in the *settings.xml* file. If the file is included in your repository, any additional configuration is not necessary.
* For packages built with Gradle, it leverages Gradle and Gradle wrapper files to build and resolve dependencies.
* Endor Labs supports AAR, EAR, JAR, RAR, and WAR files.

### How Endor Labs performs static analysis on the code

Endor Labs performs static analysis on the code based on the following factors:

* Call graphs are created for your package. These are then combined with the call graphs of the dependencies in your dependency tree to form a comprehensive call graph for the entire project.
* Endor Labs performs an inside-out analysis of the software to determine the reachability of dependencies in your project.
* The static analysis time may vary depending on the number of dependencies in the package and the number of packages in the project.

### Known limitations

* If a package can not be successfully built in the source control repository, static analysis will fail.
* Spring dependencies are analyzed based on spring public entry points to reduce the impact of Inversion of Control (IOC) frameworks. Dependencies and functions are identified as reachable and unreachable in the context of a spring version and its entry points.
* Annotation processing is limited only to the usage of the code they annotate.
* Static analysis of reflection and callbacks are not supported.
* If Endor Labs fails to resolve dependencies using default Kotlin configurations, the Kotlin configuration must be specified.
* Static analysis for Kotlin projects using Gradle is only supported when the Kotlin plugin for Gradle versions 1.5.30 to 1.9.x

## Troubleshoot errors

Here are a few error scenarios that you can check for and attempt to resolve them.

* **Host system check failure errors**:
  + Java is not installed or not present in the PATH environment variable. Install Java and try again. See [Java documentation](https://www.oracle.com/java/technologies/downloads/) for more information.
  + For android applications, $ANDROID\_HOME must be specified as an environment variable.
  + The installed version of Java is lower than the required version. Install JDK versions between 11-25.0.1 and try again.
  + Java is installed but Maven or Gradle is not installed. In such cases, the dependency resolution may not be complete.
* **Unresolved dependency errors**:
  Maven is not installed properly or the system is unable to build root pom.xml. Run `mvn dependency:tree` in the root of the project and try again. In such cases, the dependency resolution may not be complete.
* **Resolved dependency errors**:
  A version of a dependency does not exist or it cannot be found. It may have been removed from the repository.
* **Call graph errors**:
  + If the project is not compiled, call graphs are not generated. Run `gradlew compileKotlin` or `gradlew compileReleaseKotlin` for android based projects before running the scan.
  + Sometimes, the project is not compiled, if a Kotlin version discrepancy exists between the required repository version and the version on the system running the scan. For example, the Kotlin required version is 1.4 but the system has lower version installed. Install the required version and try again.
* If you have a private registry and internal dependencies on other projects, you must configure the credentials of the registry. See [Configure Maven private registries](#configure-maven-private-registries).
* If you use a remote repository configured to authenticate with a client-side certificate, you must add the certificate through an endorctl parameter. Export the `ENDOR_SCAN_JVM_PARAMETERS` parameter before performing a scan. See [Maven documentation](https://maven.apache.org/guides/mini/guide-repository-ssl.html) for details.

```
export ENDOR_SCAN_JVM_PARAMETERS="-Xmx16G,-Djavax.net.ssl.keyStorePassword=changeit,
-Djavax.net.ssl.keyStoreType=pkcs12,
-Djavax.net.ssl.keyStore=/Users/myuser/Documents/nexustls/client-cert1.p12"
```

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
