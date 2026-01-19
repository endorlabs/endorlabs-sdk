---
url: https://docs.endorlabs.com/deployment/monitoring-scans/outpost/outpost-authentication/
title: Outpost authentication | Endor Labs Docs
downloaded: 2026-01-16 09:48:14
---

Outpost authentication | Endor Labs Docs



* Type to search...

[Print entire section](/deployment/monitoring-scans/outpost/outpost-authentication/_print.html)



# Outpost authentication

Learn how to authenticate Outpost.

Outpost can use the following authentication mechanisms:

* **[API Key](#api-key-authentication-for-outpost):** You can generate an Endor Labs API key and secret and configure Outpost to use it.
* **[Azure Managed Identity](#azure-managed-identity-authentication-for-outpost):** You can configure Outpost to use an Azure managed identity for authentication. Applicable if you use Azure Kubernetes Service (AKS). You must also configure a corresponding [authorization policy](../../../../administration/access-endorlabs/authorization-policies/) in Endor Labs.
* **[GCP Service Account](#gcp-service-account-authentication-for-outpost):** You can configure Outpost to use a GCP service account for authentication. Applicable if you use Google Kubernetes Engine (GKE). You must also configure a corresponding [authorization policy](../../../../administration/access-endorlabs/authorization-policies/) in Endor Labs.

## API key authentication for Outpost

You can create an Endor Labs API key and secret to authenticate your Outpost configuration. See [API keys](../../../../administration/api-keys/) for more information.

Ensure that you select `On-prem Scheduler` as the API key permissions.

![API key permissions](../../../../images/On-Prem_APIKey.png)

## Azure Managed Identity authentication for Outpost

Perform the following steps to configure Outpost to use an Azure managed identity for authentication.

1. Enable workload identity in the AKS cluster.
2. Enable OIDC provider in the AKS cluster.
3. Create an Azure managed identity.

   ```
   az identity create -g endor-group -n endor-identity
   ```

   The command creates a **zero-permission** managed identity. Store the `clientId` for later use.
4. Run the following command to retrieve the OIDC Issuer from AKS.

   ```
   OIDC_ISSUER=$(az aks show -g endor-group -n onprem-cluster --query "oidcIssuerProfile.issuerUrl" -o tsv)
   ```

   The command fetches the OIDC issuer URL for federated authentication. Ensure that you enable OIDC and Workload Identity in the AKS cluster.
5. Create federated credentials for workloads.

   Run the following command to create the scheduler federated credential.

   ```
   az identity federated-credential create \
    --name scheduler-federated-identity \
    --identity-name endor-identity \
    --resource-group endor-group \
    --issuer $OIDC_ISSUER \
    --subject system:serviceaccount:onprem-cluster:onprem-scheduler-account
   ```

   Run the following command to create the endorctl federated credential.

   ```
   az identity federated-credential create \
    --name endorctl-federated-identity \
    --identity-name endor-identity \
    --resource-group endor-group \
    --issuer $OIDC_ISSUER \
    --subject system:serviceaccount:onprem-cluster:onprem-scheduler-endorctl-account
   ```

**Warning**

The `onprem-cluster` specified in the commands is the name of the Kubernetes namespace where Outpost is to be deployed. Replace it with the actual namespace name where you want to deploy Outpost. Ensure that you create the namespace before running the commands.

The commands link the managed identity to Kubernetes service accounts and enable secure access without static credentials.
6. Configure an [authorization policy](../../../../administration/access-endorlabs/authorization-policies/) in Endor Labs with configuration from Azure.
7. Configure the Outpost integration with **Managed Identity Client ID**.

See [Outpost configuration](../outpost-configuration/) for more information on how to configure the Outpost integration.

## GCP Service Account authentication for Outpost

Perform the following steps to configure Outpost to use a GCP service account for authentication.

1. Enable workload identity in the GKE cluster.
2. Enable OIDC provider in the GKE cluster.
3. Create a new workload service account.

   ```
   gcloud iam service-accounts create endor-compute \
     --description="Endor Labs Compute Service Account" \
     --display-name="Endor Labs Compute Service Account"
   ```
4. Grant roles/iam.serviceAccountOpenIdTokenCreator to workload service account.

   ```
   gcloud projects add-iam-policy-binding endor-experiments \
    --member "serviceAccount:endor-compute@endor-experiments.iam.gserviceaccount.com" \
    --role "roles/iam.serviceAccountOpenIdTokenCreator"
   ```
5. Create a zero-permission service account for Endor Labs to perform federation.

   ```
   gcloud iam service-accounts create endor-federation \
    --description="Endor Labs Keyless Federation Service Account" \
    --display-name="Endor Labs Federation Service Account"
   ```
6. Allow the Kubernetes service accounts to impersonate the IAM workload service account.

   ```
   gcloud iam service-accounts add-iam-policy-binding endor-compute@endor-experiments.iam.gserviceaccount.com \
    --role roles/iam.workloadIdentityUser \
    --member "serviceAccount:endor-experiments.svc.id.goog[onprem-scheduler/onprem-scheduler-account]"
   ```

   ```
   gcloud iam service-accounts add-iam-policy-binding endor-compute@endor-experiments.iam.gserviceaccount.com \
    --role roles/iam.workloadIdentityUser \
    --member "serviceAccount:endor-experiments.svc.id.goog[onprem-scheduler/onprem-scheduler-endorctl-account]"
   ```
7. Configure an [authorization policy](../../../../administration/access-endorlabs/authorization-policies/) in Endor Labs with configuration from Google Cloud.
8. Configure the Outpost integration with **Service Account Name**.

   See [Outpost configuration](../outpost-configuration/) for more information on how to configure the Outpost integration.

**Warning**

Replace `endor-experiments` with the actual project name where you want to deploy Outpost. Replace `endor-federation` and `endor-compute` with the actual service account names.

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
