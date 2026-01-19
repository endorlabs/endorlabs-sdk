---
url: https://docs.endorlabs.com/integrations/package-manager/maven-private-package-manager/
title: Private package manager integration for Maven | Endor Labs Docs
downloaded: 2026-01-16 09:49:56
---

Private package manager integration for Maven | Endor Labs Docs



* Type to search...

[Print entire section](/integrations/package-manager/maven-private-package-manager/_print.html)



# Private package manager integration for Maven

Learn how to configure Endor Labs to access private Maven repositories for dependency resolution and security scanning.

Configure Endor Labs to integrate with private Maven repositories to access proprietary dependencies during security scanning and analysis. When your Maven projects depend on artifacts hosted in private or corporate repositories, Endor Labs requires authentication credentials to resolve these dependencies and generate a complete bill of materials.

This integration enables Endor Labs to:

* Access private Maven artifacts during dependency resolution
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

7. Specify the package manager URL. Some example formats include:

   * `https://maven.pkg.github.com/<your org>`
   * `https://gitlab.example.com/api/v4/projects/<project_id>/packages/maven`
   * `https://gitlab.example.com/api/v4/groups/<group_id>/packages/maven`
8. Click **Advanced** and select **Propagate this policy to all child namespaces** to apply the package manager integration to all child namespaces.
9. Select **Use this package manager as a plugin repository** to designate the package manager as a plugin repository for Maven.
10. Select **Add Package Manager**.

If you want to delete a package manager integration, click the trash can icon at the far right of the integration.

### Authenticate to Maven private package repositories

To connect to private repositories of Maven enter the package manager URL and the package registry credentials such as username and password.

![Maven package manager integrations](../../../images/maven-package-manager.png)

### Test private package manager connection

1. Select **Manage** > **Integrations** from the left sidebar.
2. Click **Manage** in the package manager configuration you want to customize.
3. Click the vertical three dots of the package manager configured and select **Test Connection**.

**Note**

The integration does not perform authentication or authorization checks on the package manager repository.

## Private package manager integration for Maven using API

Use endorctl to create a package manager resource through an API call and configure authentication for accessing private repositories during scans.

**Note**

Maven package manager configurations apply only to Maven build projects and not to Gradle build projects that use Maven repositories.

Run the following command to create a package manager resource and authenticate to private repository.

Replace:

* `username` with your package registry username
* `xxxx` with your package registry password
* `namespace` with your namespace.

```
endorctl api create  -r PackageManager -n <namespace> -d '
{
    "meta": {
        "name": "test",
        "description": "test"
    },
    "spec": {
        "maven": {
            "priority": 1,
            "url": "package manager url",
            "user": "username",
            "password": "xxxx"
        }
    },
    "propagate": true
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
