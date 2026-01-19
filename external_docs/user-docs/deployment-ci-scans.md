---
url: https://docs.endorlabs.com/deployment/ci-scans/
title: CI Scans | Endor Labs Docs
downloaded: 2026-01-16 09:48:16
---

CI Scans | Endor Labs Docs



* Type to search...

[Print entire section](/deployment/ci-scans/_print.html)



# CI Scans

Learn various methods to deploy the Endor Labs application in your CI.

CI Scans are used to focus team’s attention and establish development workflows on the most actionable issues, prioritizing the development team’s time. CI Scans can be triggered directly from automated CI/CD pipelines, looking for new vulnerabilities relative to the baseline established for the target branch. These CI Scans provide immediate feedback to developers in the form of PR comments and can also enforce policies to break builds, block PRs, send notifications, open tickets, and more. CI scans are the most actionable method to prevent vulnerabilities from entering your repositories.

Perform CI scans using:

* [endorctl CLI](../../scan-with-endorlabs/language-scanning/)
* [Scan with GitLab pipeline](../ci-scans/scan-with-gitlab/)
* [Scan with GitHub Actions](../ci-scans/scan-with-github-actions/)
* [Scan with Circle CI](../ci-scans/scan-with-circleci/)
* [Scan with Jenkins](../ci-scans/scan-with-jenkins/)
* [Scan with Azure DevOps](../ci-scans/scan-with-azuredevops/)
* [Scan with Bitbucket](../ci-scans/scan-with-bitbucket/)
* [Scan with Google Cloud Build](../ci-scans/scan-with-google-cloud-build/)

See [scanning strategies](../../scan-with-endorlabs/scanning-strategies/) to learn techniques for effectively scanning and monitoring different versions of your projects with Endor Labs.

`endorctl` is a command line utility designed to bring the functionality of Endor Labs into your software delivery workflows. `endorctl` has several command flags to help you facilitate operational and security risk monitoring. Developers can integrate Endor Labs into Continuous Integration Workflows using the `endorctl scan`.

* `endorctl scan` - You can use endorctl scan to monitor your projects using Endor Labs, and you can update the scan information each time to keep monitoring the project for new findings. The `endorctl scan` command will scan a specific version of your repository, such as the default branch, a tagged release version, or a commit SHA.
* `endorctl scan --pr` - You can use the `endorctl scan --pr` command to scan a specific version of your source code for security and operational risks as part of your continuous integration workflows or CI runs. The `endorctl scan --pr` command performs a one-time evaluation of your project, focusing on security and operational risks, rather than providing continuous monitoring. CI runs are shown in the **Scan History** section of each project and are stored for three weeks so that you can analyze and review them on the Endor Labs user interface. See [PR scans](../../scan-with-endorlabs/pr-scans/) for more information.

Any continuous integration workflows generally run using the `endorctl scan --pr` command unless a scan is run on a created tag release, a push to the default or specific branch, or a commit SHA that will be deployed to production.

### Authenticating in CI with Keyless Authentication

Keyless Authentication enhances security and minimizes the expenses associated with secret rotation. Keyless authentication is Endor Labs recommended path to scan your projects in the CI workflows. See [Keyless Authentication](../ci-scans/keyless-authentication/) for more information.

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
