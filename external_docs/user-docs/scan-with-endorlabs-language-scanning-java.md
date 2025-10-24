---
url: https://docs.endorlabs.com/scan-with-endorlabs/language-scanning/java/
title: Java | Endor Labs Docs
downloaded: 2025-10-23 23:24:31
---

Java | Endor Labs Docs



* Type to search...
* ---

[Print entire section](/scan-with-endorlabs/language-scanning/java/_print.html)



# Java

Learn how to implement Endor Labs in repositories with Java packages.

Java is a high-level, object-oriented programming language widely used by developers. Endor Labs supports scanning and monitoring of Java projects.

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

## Software prerequisites

Endor Labs requires the following prerequisites in place for successful scans.

* Install JDK versions between 11 and 25
  + For JDK 8, see [Scan the projects on JDK version 8](#scan-the-projects-on-jdk-version-8)
* Make sure your repository includes one or more files with `.java` extension.
* Install Maven Package Manager version 3.6.1 and higher if your project uses Maven.
* Install Gradle build system version 6.0.0 and higher, if your project uses Gradle. To support lower versions of Gradle, see [Scan projects on Gradle versions between 4.7 and 6.0.0](#scan-projects-on-gradle-versions-between-47-and-600).
* For projects not using Maven or Gradle, make sure that your project is set up properly to scan without the `pom.xml` file. See [Scan projects without pom.xml](#scan-projects-without-pomxml) for more information.

## Build Java projects

You must build your Java projects before running a scan. Additionally, ensure that the packages are downloaded into the local package caches and that the build artifacts are present in the standard locations.

### Use Gradle

To analyze your software built with Gradle, Endor Labs requires that the software be able to be successfully built. To perform a quick scan, dependencies must be located in the local package manager cache. The standard $GRADLE\_USER\_HOME/caches or `/User/<username>/.gradle/caches` must exist and contain successfully downloaded dependencies. To perform a deep scan the target artifact must be generated on the file system as well.

To build your project with Gradle, use the following procedure:

1. If you would like to run a scan against a custom configuration, specify the Gradle configuration by setting an environment variable.

   ```
      export endorGradleJavaConfiguration="<configuration>"
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

In a multi-build project, if you set the environment variable `endorGradleJavaConfiguration=[GlobalConfiguration]`, the specified configuration is used for dependency resolution across all projects and subprojects in the hierarchy below.

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

### Use Maven

To analyze your software built with Maven, Endor Labs requires that the software be able to be successfully built. To perform a quick scan, dependencies must be located in the local package manager cache. The standard `.m2` cache must exist and contain successfully downloaded dependencies. To perform a deep scan the target artifact must be generated on the file system as well.

To build your project with Maven, use the following procedure:

1. Ensure that you can resolve the dependencies for your project without error by running the following command.

   ```
   mvn dependency:tree
   ```
2. Run `mvn install` and make sure the build is successful.

   #### info

   If you want to skip the execution of tests during the build, you can use `-DskipTests` to quickly build and install your projects.

   ```
   mvn install -DskipTests
   ```
3. If you have multiple Java modules not referenced in the root pom.xml file, make sure to run `mvn install` separately in all the directories.

#### Configure private Maven package repositories

Endor Labs supports fetching and scanning dependencies from private Maven package registries. Endor Labs will fetch resources from authenticated endpoints and perform the scan, allowing you to view the resolved dependencies and findings. See [Maven package manager integrations](../../../integrations/package-manager/maven-private-package-manager/) for more information on configuring private registries.

## Run a scan

Use the following options to scan your repositories. Perform a scan after building the projects.

### Option 1 - Quick scan

Perform a quick scan to get quick visibility into your software composition. This scan won’t perform reachability analysis to help you prioritize vulnerabilities.

```
endorctl scan --quick-scan
```

You can perform the scan from within the root directory of the Git project repository, and save the local results to a *results.json* file. The results and related analysis information are available on the Endor Labs user interface.

```
endorctl scan --quick-scan -o json | tee /path/to/results.json
```

You can sign in to the [Endor Labs user interface](https://app.endorlabs.com), click the **Projects** on the left sidebar, and find your project to review its results.

### Option 2 - Deep scan

Use the deep scan to perform dependency resolution, reachability analysis, and generate call graphs. You can do this after you complete the quick scan successfully.

```
endorctl scan
```

Use the following flags to save the local results to a *results.json* file. The results and related analysis information are available on the Endor Labs user interface.

```
endorctl scan -o json | tee /path/to/results.json
```

When deep analysis is performed all private software dependencies are completely analyzed by default if they have not been previously scanned. This is a one-time operation and will slow down initial scans, but won’t impact subsequent scans.

Organizations might not own some parts of the software internally and the related findings are not actionable by them. They can choose to disable this analysis using the flag `disable-private-package-analysis`. By disabling private package analysis, teams can enhance scan performance but may lose insights into how applications interact with first-party libraries.

Use the following command flag to disable private package analysis:

```
endorctl scan --disable-private-package-analysis
```

You can sign in to the [Endor Labs user interface](https://app.endorlabs.com), click the **Projects** on the left sidebar, and find your project to review its results.

### Scan projects without pom.xml

Endor Labs supports projects that do not use Maven or Gradle, and have no `pom.xml` in the following cases.

#### Note

Run the scans with the `--quick-scan` parameter if you prefer to scan the project without reachability.

#### Uber jars

If there is an uber jar (fat jar) that contains all application classes and dependency jars of the project, you can set the environment variable, `ENDOR_JVM_USE_ARTIFACT_SCAN` as true and run the scan.

```
export ENDOR_JVM_USE_ARTIFACT_SCAN=true
endorctl scan --package --path=<jar/ear/war location> --project-name=<project name>
```

For example:

```
export ENDOR_JVM_USE_ARTIFACT_SCAN=true
endorctl scan --package --path=/Users/johndoe/projects/project21.jar --project-name=Project21
```

#### Application dependencies in classpath

If you do not have an uber jar with dependencies, but only have application dependency files (like jar, war, or ear), you can set the path to these files in the environment variable, `ENDOR_JVM_USE_ARTIFACT_SCAN_CLASSPATH` and run the scan.

```
export ENDOR_JVM_USE_ARTIFACT_SCAN=true
export ENDOR_JVM_USE_ARTIFACT_SCAN_CLASSPATH=<path that contains application depedencies>
endorctl scan --package --path=<jar/ear/war location> --project-name=<project name>
```

For example:

```
export ENDOR_JVM_USE_ARTIFACT_SCAN=true
export ENDOR_JVM_USE_ARTIFACT_SCAN_CLASSPATH=/Users/johndoe/caches/modules/files-2.1
endorctl scan --package --path=/Users/johndoe/projects/project21.jar --project-name=Project21
```

#### Application classes and dependencies extracted as first-party class files

If application class files and dependency jar files are extracted as first-party class files, you can provide the first-party files in an environment variable, `ENDOR_JVM_FIRST_PARTY_PACKAGE`.

```
export ENDOR_JVM_USE_ARTIFACT_SCAN=true
export ENDOR_JVM_FIRST_PARTY_PACKAGE="<dependency/application 1>,<dependency/application 2>,...,<dependency/application N>"
endorctl scan --package --path=<jar/ear/war location> --project-name=<project name>
```

For example:

Your project jar has the following structure where `com.org.doe` and `com.org.deer` are application class files and dependencies.

```
fawn.jar
├── com.org.doe
│   ├── A.class
│   └── B.class
├── com.org.deer
│   ├── Util.class
│   └── Utilities.class
├── com.org.dep1
│   ├── Dep1.class
│   └── Dep2.class
└── com.org.dep2
    ├── 2Dep1.class
    └── 2Dep2.class
```

```
export ENDOR_JVM_USE_ARTIFACT_SCAN=true
export ENDOR_JVM_FIRST_PARTY_PACKAGE="com.org.doe,com.org.deer"
endorctl scan --package --path=/Users/johndoe/projects/fawn.jar --project-name=Fawn
```

### Scan the projects on JDK version 8

Endor Labs supports JDK versions between 11-25, however, you can scan projects on JDK 8 using the following procedure:

1. [Build your Java project](#build-java-projects) on JDK 8.
2. After building, switch your Java home to JDK 11 or higher versions.

   ```
   export JAVA_HOME=/Library/Java/JavaVirtualMachines/openjdk-11.jdk/Contents/Home
   ```
3. [Run a scan](#understand-the-scan-process)

### Scan projects on Gradle versions between 4.7 and 6.0.0

To scan Java projects on Gradle versions between 4.7 and 6.0.0, make sure to

1. Check the version of your project using:

   ```
   ./gradlew --version
   ```
2. The project must have a Gradle wrapper. You can generate the Gradle wrapper using:

   ```
   --gradle-version <your required version>.
   ```

   Endor Labs prioritizes Gradle wrapper over Gradle and it is a recommended best practice to use [Gradle Wrapper](https://docs.gradle.org/current/userguide/gradle_wrapper.html).
3. Before executing the endorctl scan, ensure the project can be built in your required version.

   ```
   Execute ./gradlew assemble.
   ```
4. Use `--bypass-host-check` during endorctl scan to execute scans on projects that have Gradle versions lower than 6.0.0.

## Understand the scan process

Endor Labs analyzes your Java code and dependencies to detect known security issues, including open-source vulnerabilities and generates call graphs.

### How Endor Labs resolves dependencies for package versions

Endor Labs resolves the dependencies for Java packages based on the following factors:

* For packages built using Maven, it leverages the Maven cache in the `.m2` directory of your file system to resolve the package’s dependencies and mirrors Maven’s build process for the most accurate results.
* For Maven, Endor Labs respects the configuration settings present in the *settings.xml* file. If this file is included in your repository, you need not provide any additional configuration.
* For packages built using Gradle, it uses Gradle and Gradle wrapper files to build packages and resolve dependencies.
* Endor Labs supports EAR, JAR, RAR, and WAR files.

### How Endor Labs performs static analysis on the code

Endor Labs performs static analysis on the Java code based on the following factors:

* Call graphs are created for your package. These are then combined with the call graphs of the dependencies in your dependency tree to form a comprehensive call graph for the entire project.
* Endor Labs performs an inside-out analysis of the software to determine the reachability of dependencies in your project.
* The static analysis time may vary depending on the number of dependencies in the package and the number of packages in the project.

### Known limitations

* If a package can not be successfully built in the source control repository, static analysis will fail.
* Spring dependencies are analyzed based on spring public entry points to reduce the impact of Inversion of Control (IOC) frameworks. Dependencies and functions are identified as reachable and unreachable in the context of a spring version and its entry points.
* Annotation processing is limited only to the usage of the code they annotate.
* Static analysis of reflection and callbacks are not supported.
* Endor Labs requires JDK 11 to generate call graphs for Java projects. Gradle versions lacking JDK 11 support are not compatible.

## Troubleshoot errors

Here are a few error scenarios that you can check for and attempt to resolve them.

* **Host system check failure errors**:

  + Java is not installed or not present in the PATH environment variable. Install Java and try again. See [Java documentation](https://www.oracle.com/java/technologies/downloads/) for more information.
  + The installed version of Java is lower than the required version. Install JDK versions between 11-25 and try again.
  + Java is installed but Maven or Gradle is not installed. In such cases, the dependency resolution may not be complete.
* **Unresolved dependency errors**:
  Maven is not installed properly or the system is unable to build root pom.xml. Run `mvn dependency:tree` in the root of the project and try again. In such cases, the dependency resolution may not be complete.
* **Resolved dependency errors**:
  A version of a dependency does not exist or it cannot be found. It may have been removed from the repository.
* **Gradle variant incompatibility message**:
  Gradle performs JVM toolchain checks for subprojects or dependencies and may raise errors indicating a Java version mismatch between dependencies declared in Gradle manifest and Java home setup.

  Example error message:

  *Incompatible because this component declares a component for use during compile-time, compatible with Java version 21 and the consumer needed a component for use during runtime, compatible with Java version 17*
  - To resolve this and taking advantage of Java’s backward compatibility, instruct Gradle to use the higher version of JDK detected in the error message. For example, for the message above, specify `org.gradle.java.home=<path of java>` in `.gradle/gradle.properties`.
  The path needs to be to the root of the directory `bin/java`. For example, if your Java is at `/Users/Downloads/jdk-21/Contents/Home/bin/java`, specify `org.gradle.java.home=/Users/Downloads/jdk-21/Contents/Home`.
  - If you are scanning a purely Java 8 Gradle project and if you encounter the above error, set `org.gradle.java.home` to point to Java 8 home, before you execute the endorctl scan.
  - A general guideline for determining which Java version to use, is to match the Java version specified in `.gradle`/`gradle.properties` with the one used for building your Gradle project.
* **Call graph errors**:
  - The project can not be built because a dependency cannot be located in the repository.
  - Sometimes, the project is not built, if a Java version discrepancy exists between the required repository version and the version on the system running the scan. For example, the Java required version is 1.8 but the system has 12 installed. Install the required version and try again.
* If you have a private registry and internal dependencies on other projects, you must configure the credentials of the registry. See [Configure Maven private registries](#configure-private-maven-package-repositories).
* If you have a large repository or if the scan fails with out-of-memory issues, you may need to increase the JVM heap size before you can successfully scan. Export the `ENDOR_SCAN_JVM_PARAMETERS` environment variable with additional JVM parameters before performing the scan as shown below:

  ```
  export ENDOR_SCAN_JVM_PARAMETERS="-Xmx32G"
  ```
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
