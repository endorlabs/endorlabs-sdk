---
url: https://docs.endorlabs.com/integrations/microsoft-defender-for-cloud/
title: Set up Microsoft Defender for Cloud integration with Endor Labs | Endor Labs Docs
downloaded: 2026-02-03 00:50:08
---

Set up Microsoft Defender for Cloud integration with Endor Labs | Endor Labs Docs



* Type to search...

[Print entire section](/integrations/microsoft-defender-for-cloud/_print.html)



# Set up Microsoft Defender for Cloud integration with Endor Labs

Learn how to integrate Defender for Cloud with Endor Labs to close the gap between Application and Cloud security.

Defender for Cloud, a Cloud-Native Application Protection Platform (CNAPP), provides comprehensive security for hybrid-cloud and multi-cloud environments. It offers advanced threat protection, security posture management, and seamless integration with development workflows. Integrate Defender for Cloud with Endor Labs to mature your security programs. With reachability analysis available directly within the Defender for Cloud console, you can prioritize what to fix based on exploitability without needing to switch tools. And with attack paths showing everywhere vulnerable code is running throughout the SDLC and in the cloud, you have a new way prioritize which vulnerabilities to remediate first.

You can correlate SCA findings with runtime alerts to view code-to-runtime attack paths. You can trace vulnerabilities found in open source software (OSS) dependencies directly to potential exploit paths in cloud environments. This allows you to prioritize remediation efforts more effectively and reduce risk across the entire software development lifecycle.

Code-to-runtime context also reveals toxic combinations of security issues. For example, there is a reachable vulnerability in an open source package, which is used on an internet reachable cloud workload. You can see a full attack path, from code committed to Azure DevOps, GitHub, or GitLab, to runtime workloads deployed on Azure, AWS, or Google Cloud Platform.

## Prerequisites

Complete the prerequisites in Endor Labs and Defender for Cloud before you can configure the integration.

## Prerequisites in Endor Labs

Ensure that you complete the prerequisites in Endor Labs so that your environment is set up properly to provide findings to Defender for Cloud.

* [Create a namespace in which you want to manage the repositories.](../../administration/namespaces/)

  You can also use an existing namespace in Endor Labs.
* [Deploy Endor Labs in your environment so that the namespace is populated with the repositories that you want to monitor using Defender for Cloud.](../../deployment/)
* [Create an API key and secret that you can use in the Defender for Cloud integration.](../../administration/api-keys/)

  Ensure that the API key has the `Read-Only` permission. We recommend that you set the expiry to 180 days or one year to avoid constant refresh of the key.

## Prerequisites in Defender for Cloud

Complete the prerequisites in Defender for Cloud so that your environment is properly set up so that your repositories are properly set up for integration, and you have sufficient permissions to manage the integration with Endor Labs.

* Enable [Defender CSPM](https://learn.microsoft.com/en-us/azure/defender-for-cloud/tutorial-enable-cspm-plan) on the subscription where you wish to see code-to-runtime contextualization.
* A user with [Security Administrator](https://learn.microsoft.com/en-us/entra/identity/role-based-access-control/permissions-reference#security-administrator) or [Global Administrator](https://learn.microsoft.com/en-us/entra/identity/role-based-access-control/permissions-reference#global-administrator) permissions on the tenant to create the connector to Endor Labs.
* Add repositories that you want to monitor in the tenant.

  [Contributor](https://learn.microsoft.com/en-us/azure/role-based-access-control/built-in-roles/privileged#contributor) or [Security Admin](https://learn.microsoft.com/en-us/azure/role-based-access-control/built-in-roles/security#security-admin) permissions on an Azure subscription to create DevOps connectors to Azure DevOps or GitHub.

  For Azure DevOps, Project Collection Administrator is required to onboard the organization.

  For GitHub, Owner is required to onboard the organization.
* To monitor results, provide a user with at least [Security Reader](https://learn.microsoft.com/en-us/azure/role-based-access-control/built-in-roles/security#security-reader) or [Reader](https://learn.microsoft.com/en-us/azure/role-based-access-control/built-in-roles/general#reader) permissions on the subscription with the DevOps connector.
* To view the attack paths and code-to-runtime capabilities, the container registry can be in Azure, AWS, GCP, or Docker Hub. The Kubernetes cluster can be in Azure, AWS, or GCP.

  If you use Azure Kubernetes Cluster (AKS) and Azure Container Registry (ACR) with an [admin account](https://learn.microsoft.com/en-us/azure/container-registry/container-registry-authentication?tabs=azure-cli#admin-account) in the Azure subscription. The [ACR must be attached to the AKS](https://learn.microsoft.com/en-us/azure/aks/cluster-container-registry-integration?tabs=azure-cli#configure-acr-integration-for-an-existing-aks-cluster) so that you can deploy images from ACR to AKS.

## Configure Defender for Cloud integration

You need to configure the integration in Defender for Cloud.

1. In Defender for Cloud, navigate to **Management** > **Environment Settings**.
2. Select **Add Integration** > **Endor Labs**.
3. Enter a name for the integration.
4. Enter the following information from your Endor Labs environment when you configure the integration:

   * [Endor Labs namespace that you want to integrate](../../administration/namespaces/)
   * [Endor Labs API key](../../administration/api-keys/)
   * [Endor Labs API secret](../../administration/api-keys/)
5. Click **Save**.

Once the integration is set up, Endor Labs data is available in Defender for Cloud.

## Prioritize findings by exploitability

From the Defender for Cloud console, you can use Endor Labs’ function-reachability analysis to prioritize what to fix based on exploitability.

1. Select **General** > **Cloud Security Explorer**.
2. Select **Query Builder**.
3. Build a query that searches code repositories that have vulnerabilities with reachable functions.

   ![Defender for Cloud Query Builder](../../images/mdcquerybuilder.png)
4. Click **Search** to list results based on the search query.

   ![Defender for Cloud Search Results](../../images/mdcsearchresults.png)
5. Select a repository to view more details on the vulnerabilities.

   ![Defender for Cloud Result Details](../../images/mdcresultdetails.png)

   You can review the findings and also navigate to Endor Labs user interface to view more information on the findings.

## Detect vulnerable code running in the cloud

From the Defender for Cloud console, you can view an attack path that visualizes everywhere vulnerable code is running throughout the SDLC and in the cloud.

Select **General** > **Attack Path Explorer** to view an attack path of vulnerable code running in a cluster.

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
