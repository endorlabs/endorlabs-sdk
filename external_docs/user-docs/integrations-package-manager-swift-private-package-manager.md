---
url: https://docs.endorlabs.com/integrations/package-manager/swift-private-package-manager/
title: Private package manager integration for Swift | Endor Labs Docs
downloaded: 2025-11-20 11:51:33
---

Private package manager integration for Swift | Endor Labs Docs



* Type to search...
* ---

[Print entire section](/integrations/package-manager/swift-private-package-manager/_print.html)



# Private package manager integration for Swift

Learn how to configure Endor Labs to access private Swift package repositories for dependency resolution and security scanning.

Configure Endor Labs to integrate with private Swift package repositories to access proprietary dependencies during security scanning and analysis. When your Swift projects depend on packages hosted in private or corporate repositories, Endor Labs requires authentication credentials to resolve these dependencies and generate a complete bill of materials.

This integration enables Endor Labs to:

* Access private Swift packages during dependency resolution
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
7. Click **Advanced** and select **Propagate this policy to all child namespaces** to apply the package manager integration to all child namespaces.

   #### Maven

   Select **Use this package manager as a plugin repository** to designate this package manager as a plugin repository for Maven.
8. Select **Add Package Manager**.

If you want to delete a package manager integration, click the trash can icon at the far right of the integration.

### Authenticate to Swift private package repositories

To connect to private repositories of Swift Package Manager enter the package manager URL and the package registry credentials such as username and password.

![Basic Authentication for package manager integrations](../../../images/package-manager-swift.png)

### Test private package manager connection

1. Select **Manage** > **Integrations** from the left sidebar.
2. Click **Manage** in the package manager configuration you want to customize.
3. Click the vertical three dots of the package manager configured and select **Test Connection**.

#### Note

The integration does not perform authentication or authorization checks on the package manager repository.

## Package manager integration for SwiftPM using API

Use endorctl to create a package manager resource for your private swift registry and authenticate using one of the following methods:

* Basic authentication using username and password
* Authentication token

### Basic authentication using username and password

Run the following command to create a package manager resource and authenticate to Swift registry using basic authentication credentials with scope.

Replace:

* `namespace` with your namespace.
* `username` with your username
* `xxxx` with your password.
* `scope` with your scope. For example, `"scope":"abc-corp"`.

```
endorctl api create -r PackageManager -n <namespace> -d '
{
    "meta": {
        "name": "test swift",
        "description": "setup swift registry with basic auth"
    },
    "spec": {
        "swift": {
            "priority": 1,
            "url": "package manager url",
            "basic_auth": {
                "username": "username",
                "password": "xxxx"
            },
            "scope": "scope"
        }
    },
    "propagate": false
}'
```

### Authentication token

Run the following command to create a package manager resource and authenticate to Swift registry using authentication token with scope.

Replace:

* `namespace` with your namespace
* `token` with your Swift registry authentication token.
* `scope` with your scope. For example, `"scope":"abc-corp"`.

```
endorctl api create -r PackageManager -n <namespace> -d '
{
   "meta": {
       "name": "test swift",
       "description": "setup swift registry with token"
   },
   "spec": {
       "swift": {
           "priority": 1,
           "url": "package manager url",
           "token": "authentication token",
           "scope": "scope"
       }
   },
   "propagate": false
} '
```

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
