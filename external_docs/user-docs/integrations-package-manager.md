---
url: https://docs.endorlabs.com/integrations/package-manager/
title: Set up custom package repositories | Endor Labs Docs
downloaded: 2025-10-23 23:24:36
---

Set up custom package repositories | Endor Labs Docs



* Type to search...
* ---

[Print entire section](/integrations/package-manager/_print.html)



# Set up custom package repositories

Learn how to configure custom package repositories for dependency resolution.

Suppose your software components are private and are hosted in an internal package repository. In that case, you must provide authentication credentials to the registry, to create a complete bill of materials or perform static analysis.

You must set up custom package repositories if:

* Your software package isn’t scanned as part of a post-build or install step
* You are using the Endor Labs GitHub App
* you are implementing scans across your environment for quick visibility
* Authentication information to your private package repository is hosted outside of the repository

If your software components are private and hosted in AWS CodeArtifact, set up an OpenID Connect provider in AWS and create roles with trust policies to allow Endor Labs access to your CodeArtifact repositories. See [Configure package manager integrations with AWS](./aws-codeartifact/).

You can authenticate to private package artifact repositories using mutual TLS. See [mTLS authentication](./mtls-authentication/) to learn how to set up and authenticate.

## Package manager integration support matrix

The following support matrix details support for package manager integrations:

| Language | Ecosystem | Support | mTLS |
| --- | --- | --- | --- |
| [Java](./maven-private-package-manager/) | Maven (`mvn://`) | ✓ | ✓ |
| [JavaScript](./npm-private-package-manager/) | npm (`npm://`) | ✓ | ✓ |
| [Python](./pypi-private-package-manager/) | PyPI (`pypi://`) | ✓ | ✓ |
| [Gradle](./gradle-private-package-manager/) | Gradle Properties | ✓ | ✓ |
| [.NET/C#](./nuget-private-package-manager/) | NuGet (`nuget://`) | ✓ | ✗ |
| [Swift](./swift-private-package-manager/) | Swift (`swift://`) | ✓ | ✗ |
| [Ruby](./rubygems-private-package-manager/) | Gem (`gem://`) | ✓ | ✗ |
| [PHP](./packagist-private-package-manager/) | Composer (`composer://`) | ✓ | ✗ |

#### Note

Private package manager integrations for Golang and Rust are not supported.

## Change package manager integration priority

Package manager integrations allow you to set the priority of each package repository used by a package manager in your tenant namespace. This defines the location from which a package manager looks when it attempts to resolve dependencies for a software package.

To change the package manager integration priority:

1. Click and hold the integration you would like to change the priority of.
2. Drag the integration to the priority spot that is most frequently used by your organization.

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
