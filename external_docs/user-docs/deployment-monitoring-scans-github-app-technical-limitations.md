---
url: https://docs.endorlabs.com/deployment/monitoring-scans/github-app/technical-limitations/
title: Technical limitations of the Endor Labs GitHub App | Endor Labs Docs
downloaded: 2026-01-26 10:07:15
---

Technical limitations of the Endor Labs GitHub App | Endor Labs Docs



* Type to search...

[Print entire section](/deployment/monitoring-scans/github-app/technical-limitations/_print.html)



# Technical limitations of the Endor Labs GitHub App

Understand the technical limitations associated with the GitHub App.

The Endor Labs GitHub App provides visibility across a GitHub organization, but it has technical limitations that do not account for the unique requirements of your application.

## Custom package build steps

Endor Labs requires executing custom build steps outside of standard package manager commands to build software packages and get an accurate bill of materials and perform static analysis. Sometimes, a complete bill of materials may not be generated, or static analysis may not be performed if custom steps are required for your software to build. Applications that require custom build steps may need to be implemented in a CI environment to successfully get an accurate bill of materials.

## Custom resource profiles

Large applications may require significant memory allocations to perform static analysis on a package. The services scanning the GitHub App use 16 GB of memory by default. Applications that require more memory may not obtain vulnerability prioritization information using the GitHub App. Scan large applications in a CI environment using a runner with sufficient resource allocations.

## Authentication for private software components

Private software components hosted in an internal package repository may require authentication credentials to create a complete bill of materials or perform static analysis.

If your authentication information to your private package repository is hosted outside the repository, you will need to configure a package manager integration. See [Set up package manager integration](../../../../integrations/package-manager/) for more details. If your package repository is inaccessible from the public internet, you can work with Endor Labs to evaluate options.

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
