---
url: https://docs.endorlabs.com/upgrades-and-remediation/using-endor-patches/access-endor-patch-repository/
title: Accessing the Endor Patch repository | Endor Labs Docs
downloaded: 2025-10-23 23:27:32
---

Accessing the Endor Patch repository | Endor Labs Docs



* Type to search...
* ---

[Print entire section](/upgrades-and-remediation/using-endor-patches/access-endor-patch-repository/_print.html)



# Accessing the Endor Patch repository

Learn how to retrieve and use Endor Patches versions of dependencies using direct URLs and build tool configurations.

Endor Labs provides patched versions of open source dependencies through a secure Maven repository. This guide explains how to access these patched artifacts using direct URLs and configure your build tools to automatically use Endor Patches.

## Repository Access

The Endor Patch repository is accessible through the following URL.

```
https://factory.endorlabs.com/v1/namespaces/$NAMESPACE/maven2
```

You’ll need API credentials from Endor Labs to access the repository. These credentials are used for authentication when downloading artifacts. See [Connecting to the Endor Patch Factory](../connecting-to-the-factory/) for detailed instructions on how to connect to the Endor Patch Factory and get your API credentials.

## Direct URL Access

You can directly download specific artifacts from the Endor Patch repository using their Maven coordinates. The URL structure follows the standard Maven repository format.

```
https://factory.endorlabs.com/v1/namespaces/$NAMESPACE/maven2/{groupId}/{artifactId}/{version}/{artifactId}-{version}.{extension}
```

### Example: Downloading a JAR file

Run the following command to download the Jackson Databind library with Endor patches.

```
curl -L --user "$ENDOR_API_CREDENTIALS_KEY:$ENDOR_API_CREDENTIALS_SECRET" \
  -O "https://factory.endorlabs.com/v1/namespaces/$NAMESPACE/maven2/com/fasterxml/jackson/core/jackson-databind/2.9.10.3-endor-latest/jackson-databind-2.9.10.3-endor-latest.jar"
```

### Example: Downloading a POM file

Run the following command to download the corresponding POM file.

```
curl -L --user "$ENDOR_API_CREDENTIALS_KEY:$ENDOR_API_CREDENTIALS_SECRET" \
  -O "https://factory.endorlabs.com/v1/namespaces/$NAMESPACE/maven2/com/fasterxml/jackson/core/jackson-databind/2.9.10.3-endor-latest/jackson-databind-2.9.10.3-endor-latest.pom"
```

## Build Tool Configuration

### Maven Configuration for build tools

Configure Maven to use the Endor Patch repository by adding it to your `pom.xml` file.

```
<repositories>
  <repository>
    <id>endorlabs</id>
    <name>Endor Labs Patch Repository</name>
    <url>https://factory.endorlabs.com/v1/namespaces/$NAMESPACE/maven2</url>
    <releases>
      <enabled>true</enabled>
    </releases>
    <snapshots>
      <enabled>false</enabled>
    </snapshots>
  </repository>
</repositories>
```

Add authentication credentials to your Maven `settings.xml` file.

```
<servers>
  <server>
    <id>endorlabs</id>
    <username>${env.ENDOR_API_CREDENTIALS_KEY}</username>
    <password>${env.ENDOR_API_CREDENTIALS_SECRET}</password>
  </server>
</servers>
```

### Gradle Configuration for build tools

Configure Gradle to use the Endor Patch repository in your `build.gradle` file.

```
repositories {
    mavenCentral()
    maven {
        name = "Endor Labs Patch Repository"
        url = uri("https://factory.endorlabs.com/v1/namespaces/$NAMESPACE/maven2")
        credentials {
            username "$ENDOR_API_CREDENTIALS_KEY"
            password "$ENDOR_API_CREDENTIALS_SECRET"
        }
    }
}
```

## Using Endor Patches in Dependencies

### Maven Dependencies for dependencies

Specify Endor Patch versions in your `pom.xml` file.

```
<dependencies>
  <!-- Use the latest Endor patch for Jackson Databind -->
  <dependency>
    <groupId>com.fasterxml.jackson.core</groupId>
    <artifactId>jackson-databind</artifactId>
    <version>2.9.10.3-endor-latest</version>
  </dependency>

  <!-- Use a specific Endor patch version with date -->
  <dependency>
    <groupId>com.fasterxml.jackson.core</groupId>
    <artifactId>jackson-databind</artifactId>
    <version>2.9.10.3-endor-2024-07-10</version>
  </dependency>

  <!-- Use auto-patching (original version number) -->
  <dependency>
    <groupId>com.fasterxml.jackson.core</groupId>
    <artifactId>jackson-databind</artifactId>
    <version>2.9.10.3</version>
  </dependency>
</dependencies>
```

### Gradle Dependencies for dependencies

Specify Endor Patch versions in your `build.gradle` file.

```
dependencies {
    // Use the latest Endor patch for Jackson Databind
    implementation("com.fasterxml.jackson.core:jackson-databind:2.9.10.3-endor-latest")

    // Use a specific Endor patch version with date
    implementation("com.fasterxml.jackson.core:jackson-databind:2.9.10.3-endor-2024-07-10")

    // Use auto-patching (original version number)
    implementation("com.fasterxml.jackson.core:jackson-databind:2.9.10.3")
}
```

## Automatic Patching

With auto patching enabled, you can use the original version numbers and Endor Labs will automatically provide the patched versions.

Auto patching requires you to perform the following tasks:

1. Configure the Endor Patch repository as the first priority in your build tools.
2. Enable auto patching in your Endor Labs settings.

See [Automatic patching](../auto-patching/) for detailed setup instructions.

## Version Naming Convention

Endor Patch versions follow these naming conventions:

* `{original-version}-endor-latest`: Latest available patch for the original version
* `{original-version}-endor-{YYYY-MM-DD}`: Specific patch version with date stamp
* `{original-version}`: Auto patching version (uses original version number without suffix)

For example, if for Jackson Databind `v2.9.10.3`, the following versions are available:

* `v2.9.10.3-endor-latest`: Latest patch for Jackson Databind `v2.9.10.3`
* `v2.9.10.3-endor-2024-07-10`: Patch from July 10, 2024 for Jackson Databind `v2.9.10.3`
* `2.9.10.3`: Auto patching version (no suffix needed)

## Repository Manager Configuration

For enterprise environments, configure your repository manager to proxy the Endor Patch repository. Detailed setup instructions are available in the dedicated guides:

* [Configure Sonatype Nexus Repository](../configure-nexus-repository/) - Complete setup for Nexus Repository Manager
* [Configure JFrog Artifactory](../configure-jfrog-artifactory/) - Complete setup for JFrog Artifactory

### Basic Configuration

Both repository managers require these basic settings:

* **Repository URL**: `https://factory.endorlabs.com/v1/namespaces/$NAMESPACE/maven2`
* **Authentication**: Use your Endor API credentials (key and secret)
* **Repository Type**: Maven 2
* **Policy**: Release only (no snapshots)

## Verification and Testing

The following sections describe how to verify that your build tool can resolve dependencies and that you can download artifacts directly.

### Verify Artifact Download

Run the following command to test that you can download artifacts directly.

```
# Test with curl
curl -I --user "$ENDOR_API_CREDENTIALS_KEY:$ENDOR_API_CREDENTIALS_SECRET" \
  "https://factory.endorlabs.com/v1/namespaces/$NAMESPACE/maven2/com/fasterxml/jackson/core/jackson-databind/2.9.10.3-endor-latest/jackson-databind-2.9.10.3-endor-latest.jar"
```

### Verify Build Integration

Run the following commands to test that your build tool can resolve dependencies.

* Maven

  ```
  mvn dependency:resolve -Dclassifier=sources
  ```
* Gradle

  ```
  ./gradlew dependencies
  ```

## Debugging

You can use the following commands to debug your build tool configuration.

* Test repository connectivity

  ```
  curl -v --user "$ENDOR_API_CREDENTIALS_KEY:$ENDOR_API_CREDENTIALS_SECRET" \
  "https://factory.endorlabs.com/v1/namespaces/$NAMESPACE/maven2/"
  ```
* Check Maven repository configuration

  ```
  mvn help:effective-settings
  ```
* Check Gradle repository configuration

  ```
  ./gradlew buildEnvironment
  ```

## Security Considerations

Ensure you follow these security best practices:

* Store API credentials securely using environment variables or secure credential storage
* Rotate API keys regularly
* Use repository managers in enterprise environments for better security and caching
* Verify artifact checksums when downloading directly

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
