---
url: https://docs.endorlabs.com/upgrades-and-remediation/using-endor-patches/connecting-to-the-factory/
title: Connect to the Endor Labs Patch Factory | Endor Labs Docs
downloaded: 2026-01-26 10:05:43
---

Connect to the Endor Labs Patch Factory | Endor Labs Docs



* Type to search...

[Print entire section](/upgrades-and-remediation/using-endor-patches/connecting-to-the-factory/_print.html)



# Connect to the Endor Labs Patch Factory

Learn how to connect to the Endor Labs Patch Factory and use an Endor patch.

Endor Labs provides a secure Maven repository for patched versions of open source dependencies. This guide explains how to connect to the Endor Patch Factory and use Endor patches in your build tools.

See [Accessing the Endor Patch repository](../access-endor-patch-repository/) for detailed instructions on how to access the Endor Patch repository directly and configure your build tools to use Endor patches.

You can start using Endor patches with the following simple steps:

1. [Create an API key](#create-an-api-key)
2. Configure your package manager to use Endor patches
   * [Configure Gradle](#configure-gradle)
   * [Configure Maven](#configure-maven)
3. Specify the Endor Patch you want to use

## Create an API key

To gain Rest API access to Endor Labs Patch Factory, you have to generate API credentials to authenticate to the repository.

1. From **Manage**, navigate to **API Keys**.
2. Select **Generate API Key**.
3. Enter a name to identify the API key, such as “Endor Patch Factory”.
4. Select the permissions to apply to the API Key, you’ll need at least **Read Only**.
5. Select the expiration date of the API key. This may be either 30, 60, or 90 days.

Using these credentials, you can configure Endor Labs your package manager or Artifact Repository proxy to authenticate to the Endor Patch Factory.

## Configure Gradle

1. Open the `build.gradle` file of the package you’d like to configure to use patches.
2. Include a repositories section in the `build.gradle` file to establish a repository connection to the Endor Labs Patch Factory. Make sure to replace `namespace` with the name of your Endor Labs namespace.
3. Include a reference to the Endor Patch version in the `build.gradle` file.

   The following example repository section shows how to configure Gradle to use the Endor Patch Factory.

   ```
   repositories {
       mavenCentral()
       maven {
           url "https://factory.endorlabs.com/v1/namespaces/<namespace>/maven2"
           credentials {
               username "$ENDOR_API_CREDENTIALS_KEY"
               password "$ENDOR_API_CREDENTIALS_SECRET"
           }
       }
    }
   ```
4. Finally, include the Endor Labs patch version you’d like to use. For example, to use the latest patched version from Endor Labs add `-endor-latest` to the version of your dependency.

   The following example dependency section shows how to configure Gradle to use the Endor Patch Factory.

   ```
   dependencies {
       implementation("com.fasterxml.jackson.core:jackson-databind:2.9.10.3-endor-latest")
   }
   ```

## Configure Maven

1. Open the `pom.xml` file of the package you’d like to configure to use patches.
2. If there is no `<repositories>` section in the `pom.xml`, then create one.
3. Include a repositories section in the `pom.xml` file to establish a repository connection to the Endor Labs Patch Factory. Make sure to replace `<namespace>` with the name of your Endor Labs namespace.

   ```
   <repositories>
     <repository>
       <id>endorlabs</id>
       <url>https://factory.endorlabs.com/v1/namespaces/<namespace>/maven2</url>
   </repository>
   </repositories>
   ```
4. Next, open the Maven `settings.xml` file located at `$HOME/.m2/settings.xml` and add a `<server>` section to the settings file with your Endor Labs credentials.

   * The `username` value must be your API key.
   * The `password` must be your API key secret.
   * The `id` value must be same as the value provided in the `pom.xml`.

   The following example `settings.xml` file shows how to configure Maven to use the Endor Patch Factory.

   ```
   <?xml version="1.0" encoding="UTF-8"?>
   <settings xmlns="http://maven.apache.org/SETTINGS/1.0.0"
          xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
          xsi:schemaLocation="http://maven.apache.org/SETTINGS/1.0.0
                              http://maven.apache.org/xsd/settings-1.0.0.xsd">
        <servers>
           <server>
               <id>endorlabs</id>
               <username>${env.ENDOR_API_CREDENTIALS_KEY}</username>
               <password>${env.ENDOR_API_CREDENTIALS_SECRET}</password>
           </server>
        </servers>
   </settings>
   ```
5. Finally, include the Endor Labs patch version you’d like to use in to your manifest. For example, to use the latest patched version from Endor Labs include `-endor-latest` to the version of your dependency.

   The following example dependency section shows how to configure Maven to use the Endor Patch Factory.

   ```
   <dependency>
      <groupId>com.fasterxml.jackson.core</groupId>
      <artifactId>jackson-databind</artifactId>
      <version>2.9.10.3-endor-latest</version>
   </dependency>
   ```

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
