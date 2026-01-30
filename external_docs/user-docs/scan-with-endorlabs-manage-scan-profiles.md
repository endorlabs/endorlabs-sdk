---
url: https://docs.endorlabs.com/scan-with-endorlabs/manage-scan-profiles/
title: Scan profiles | Endor Labs Docs
downloaded: 2026-01-26 10:09:14
---

Scan profiles | Endor Labs Docs



* Type to search...

[Print entire section](/scan-with-endorlabs/manage-scan-profiles/_print.html)



# Scan profiles

Learn how to build repeatable patterns by configuring scan profiles in your scan environment.

A scan profile is a configuration that defines the scan parameters, and toolchains for each build setup required for a scan. Use scan profiles to ensure accurate scans and reduce failures caused by missing or mismatched dependencies. Associate a project with an appropriate scan profile to ensure that each scan uses the correct configuration. You can also [configure automated scan parameters](../manage-scan-profiles//build-tools/#configure-automated-scan-parameters) in your scan profile to customize scan behavior in cloud environments.

Build tools in a scan profile help recreate the project’s build environment, ensuring reliable dependency resolution and accurate scans. See [build tools](../manage-scan-profiles/build-tools/) to configure them and view the toolchains supported by Endor Labs.

Use one of the following methods to create a scan profile:

* [Configure scan profile through the Endor Labs user interface](../manage-scan-profiles/configure-scanprofile-ui/)
* [Configure scan profile through the Endor Labs API](../manage-scan-profiles/configure-scanprofile-api/)
* [Configure scan profile through `scanprofile.yaml` file](../manage-scan-profiles/configure-scanprofile-yaml/)

## Scan workflow

A scan workflow is a predefined sequence of scan steps that runs within a project. Each step applies a specific scan profile, enabling you to target different parts of your codebase. Analytics are generated once the entire workflow completes.

A project can have only one scan workflow at a time. Use scan workflows to combine multiple scan profiles and apply them selectively—for example, when your project uses different languages or build tools across various components.

Use the following method to create a scan workflow:

* [Configure scan workflow through the Endor Labs API](../manage-scan-profiles/configure-scan-workflow-through-api/)
* [Configure scan workflow through the Endor Labs user interface](../manage-scan-profiles/configure-scanworkflow-through-ui/)

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
