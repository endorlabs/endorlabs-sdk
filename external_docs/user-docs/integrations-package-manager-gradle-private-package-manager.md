---
url: https://docs.endorlabs.com/integrations/package-manager/gradle-private-package-manager/
title: Private package manager integration for Gradle | Endor Labs Docs
downloaded: 2026-01-26 10:08:31
---

Private package manager integration for Gradle | Endor Labs Docs



* Type to search...

[Print entire section](/integrations/package-manager/gradle-private-package-manager/_print.html)



# Private package manager integration for Gradle

Learn how to configure Endor Labs to access private Gradle repositories for dependency resolution and security scanning.

Configure Endor Labs to integrate with private Gradle repositories to access proprietary dependencies during security scanning and analysis. When your Gradle projects depend on artifacts hosted in private or corporate repositories, Endor Labs requires authentication credentials to resolve these dependencies and generate a complete bill of materials.

This integration enables Endor Labs to:

* Access private Gradle artifacts during dependency resolution
* Generate comprehensive security analysis including private dependencies
* Maintain complete visibility into your software supply chain

## Configure package manager integration

Endor Labs integrates with your self-hosted package repositories and source control systems to give you visibility into your environment. Package manager integrations allow users to simplify scanning using custom repositories.

Endor Labs generally respects package authentication and configuration settings and a package manager integration is usually not required to scan private packages successfully.

* Use package manager integrations to simplify scanning when authentication to private repositories is not part of standard manifest or settings files.
* Package manager integrations allow you to set custom repositories for each package ecosystem and the priority of each repository for scanning.

To set up a package manager integration:

1. Sign in to Endor Labs.
2. Select **Manage** > **Integrations** from the left sidebar.
3. Click **Manage** in the package manager configuration you want to customize.
4. Select **Add Package Manager**.
5. Enter the name of the package manager.
6. Select either **Basic** or **AWS Code Artifactory** as **Authentication Type**.

   See [AWS authentication](../aws-codeartifact/) for more information.

7. Enter the package registry property key and property value.
8. Click **Advanced** and select **Propagate this policy to all child namespaces** to apply the package manager integration to all child namespaces.
9. Select **Add Package Manager**.

If you want to delete a package manager integration, click the trash can icon at the far right of the integration.

### Authenticate to Gradle private package repositories

To connect to private Gradle repositories, enter the package registry credentials such as property key and property value.

![Basic Authentication for package manager integrations](../../../images/package-manager-gradle.png)

### Test private package manager connection

1. Select **Manage** > **Integrations** from the left sidebar.
2. Click **Manage** in the package manager configuration you want to customize.
3. Click the vertical three dots of the package manager configured and select **Test Connection**.

**Note**

The integration does not perform authentication or authorization checks on the package manager repository.

## Private package manager integration for Gradle using API

Configure private package manager integration with Gradle to authenticate and fetch dependencies from private repositories during scans.

Gradle requires valid credentials, such as AWS access keys and GitHub or GitLab tokens, to access private repositories and fetch dependencies. Provide these credentials through the endorctl API call for GitHub App scans to run successfully.

The variable names you define (like `mavenAccessKey`, `mavenSecretKey`) must exactly match the property names used inside your `build.gradle` file when configuring credentials. For more information on how to align variable names with your build configuration, refer to [Declaring private repositories.](https://docs.gradle.org/current/userguide/declaring_repositories.html#sub:declaring-custom-repository-basics)

**Note**

You can configure these credentials for the scans performed through the GitHub App.

### Set Gradle credentials

Use endorctl to configure your repository credentials. You can set the necessary Gradle properties, allowing access to private repositories during the Gradle build process.

For example, to authenticate with an AWS S3-backed Maven repository, run the following commands to set the `mavenAccessKey` and `mavenSecretKey` properties. Replace `namespace` with your namespace.

```
endorctl api create -n <namespace> -r PackageManager -d '{
    "meta": {
        "name": "gradle properties"
    },
    "spec": {
        "gradle": {
            "property_key_name": "mavenAccessKey",
            "property_key_value": "your-access-key"
        }
    }
}'
```

```
endorctl api create -n <namespace> -r PackageManager -d '{
    "meta": {
        "name": "gradle properties"
    },
    "spec": {
        "gradle": {
            "property_key_name": "mavenSecretKey",
            "property_key_value": "your-secret-key"
        }
    }
}'
```

These credentials will then be available to your Gradle build at scan time. All values configured through the API are automatically exported as environment variables.

### Considerations

When configuring Gradle credentials, consider the following scenarios:

#### AWS credentials with scan profile

If a scan profile is linked to your project, AWS credentials are directly written into `~/.gradle/gradle.properties` and require exact key matches. You can use one of the following combinations:

* `AWS_ACCESS_KEY` and `AWS_SECRET_KEY`
* `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`

#### Authenticate using mutual TLS

Use mutual TLS to securely authenticate to artifact repositories. Currently, mutual TLS can be configured only through the API. See [mTLS authentication](../mtls-authentication/) for more information.

### Fetch package manager

Run the following command to fetch the package manager using the UUID:

```
endorctl api get -r packageManager -n <your namespace>  --uuid <take uuid from list command>
```

### Delete package manager

Run the following command to delete the package manager using the UUID:

```
endorctl api delete -r packageManager -n <your namespace>  --uuid <take uuid from list command>
```

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
