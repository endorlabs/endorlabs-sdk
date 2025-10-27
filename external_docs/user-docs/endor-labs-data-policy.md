---
url: https://docs.endorlabs.com/endor-labs-data-policy/
title: How Endor Labs handles your data | Endor Labs Docs
downloaded: 2025-10-27 13:00:50
---

How Endor Labs handles your data | Endor Labs Docs



* Type to search...
* ---

[Print entire section](/endor-labs-data-policy/_print.html)



# How Endor Labs handles your data

Learn about how Endor Labs handles your data

At Endor Labs, safeguarding your data is our priority. We believe that transparency builds trust, so we’re upfront about what data we handle, how we process it, and most importantly, what we don’t do!

The data that Endor Labs handles varies depending on the product you use, your deployment model, and your configured integrations. As Endor Labs continues to innovate, our data handling practices may change with the introduction of new capabilities, products, or changes to existing functionality over time.

## Deployment models

Endor Labs has two primary deployment models:

* **Hybrid scanning**: Customers can run Endor Labs CLI in their CI/CD environment. While using a hybrid scanning strategy, analysis of your software is performed inside your environment on the compute environment where a scan is running. Metadata associated with the various scan types are then sent back to Endor Labs cloud environment to your hosted tenant and stored for analysis.
* **Cloud scanning:**: Customers can integrate and deploy Endor Labs using a cloud-based scanning solution, such as the Endor Labs GitHub App. When using this approach, Endor Labs is granted access to your source code and SCM to enable continuous scanning of changes to your software and SCM configuration. During the scan, repositories are cloned into a dedicated ephemeral container, which operates in a secure and isolated environment. Once the scan is complete, the container and all associated data are deleted. The source code is completely removed after each scan, and only the metadata related to the scan is retained.

## Data common across products

* **Finding data**: Endor Labs stores information required to report on findings to on their customers security or operational risks such as vulnerability or misconfiguration information.
* **Finding location**: Endor Labs stores information required to identify the location of a finding so that corrective action may take place. This includes information such as the repository name, file name, and issue location.
* **Integration information**: Endor Labs stores information required for operation of external integrations with third parties such as Jira. These include configuration and authentication information.
* **Identity information**: Endor Labs stores identity claim information required to access and use the platform, such as email address and group claims sent by an external identity provider.
* **User telemetry**: Endor Labs stores various types of information about your usage of Endor Labs such as platform usage and scan configuration.

## Product: Endor Open Source

Endor Labs stores data about your repository, software packages, container images, and your software manifest files to report findings on known issues and re-analyze them as security intelligence feeds are continuously updated.

### [Data in SCA scans](../scan-with-endorlabs/language-scanning/)

* Analyzes repositories for manifest files and code to determine the resolved dependencies.
* Looks in dependency caches or environments to determine the dependencies resolved by a package manager.
* Assesses the source code or final artifact to create and identify a call graph for the specific version of your code in the case of SCA scanning.

### [Data in container scanning](../scan-with-endorlabs/scan-containers/)

Accesses the image on the host operating system and reviews the image digests and layers, assesses the dependencies installed at each layer and aggregates risk information based on those dependencies.

| Data Element | Examples |
| --- | --- |
| Package/Image metadata | Package version call graph, dependency graph, package name, version, dependency metadata |
| Repository metadata | Repository name, Git reference, Git SHA |
| Finding information | Security and operational risk |

## [Product: Endor SBOM Hub](../managing-sboms/)

Leverages the raw data of the SBOMs you provide for tracking. This includes the complete SBOM and metadata about risks discovered by Endor Labs.

## Product: Endor Code

Endor Code consists of the following scans:

* Secrets
* SAST
* AI models

### [Data in secret scanning](../secrets-leak-detection/)

* Endor Labs scans an existing ref or all Git logs for potential secret leaks. If an issue is identified, it will store issue location information including the Git reference, file and line numbers from which a secret is found.
* Secret validation occurs as part of a local scan, during which the discovered secret is used to validate against an external validation endpoint or API. This occurs in the environment from which the scan for secrets is run.

### [Data in SAST scanning](../sast-scans-with-endorlabs/)

During SAST scans, Endor Labs stores a snippet of vulnerable code for ease of identification of an issue.

| Data Element | Examples |
| --- | --- |
| File Location and Line numbers | Line numbers and files where a finding is discovered |
| Repository Metadata | Repository Name, Git Reference, Git SHA |
| Finding Information | Information about the specific secret leak or code weakness |

### [Data in AI Models](../ai/ai-llm/)

While scanning for AI models, Endor Labs may send snippets of code to Azure OpenAI Service to identify the model name in use.

## Endor Labs Policy and Transparency Information

For additional information, see the following relevant pages on how Endor Labs handles your data:

* [Endor Labs Sub-processors](https://www.endorlabs.com/legal/endor-labs-subprocessors)
* [Endor Labs Trust Center](https://app.drata.com/trust/9cc7b443-0c38-11ee-865f-029d78a187d9)
* [Endor Labs Privacy Policy](https://www.endorlabs.com/legal/privacy-policy)
* [Endor Labs Data Processing (DPA)](https://www.endorlabs.com/legal/endor-labs-data-processing)
* [Endor Labs Product Terms of Use](https://www.endorlabs.com/legal/terms-of-use)

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
