---
url: https://docs.endorlabs.com/deployment/ci-scans/keyless-authentication/google-keyless-auth/
title: Keyless authentication in Google Cloud | Endor Labs Docs
downloaded: 2026-01-16 09:49:53
---

Keyless authentication in Google Cloud | Endor Labs Docs



* Type to search...

[Print entire section](/deployment/ci-scans/keyless-authentication/google-keyless-auth/_print.html)



# Keyless authentication in Google Cloud

Learn how to implement keyless authentication in Google Cloud.

To enable Keyless Authentication in GCP you’ll first need permissions to create service accounts and assign these accounts roles to GCP.

The workflow to enable keyless authentication is:

1. Create a service account with no permissions for federation.
2. If you do not attach a service account to compute resources or use the default service account, we recommend creating a new service account for the compute resources. Create a service account to attach to compute resources and impersonate the federation service account.
3. Create an authorization policy to allow the federation service account to authenticate to Endor Labs.
4. Provision the compute resources with the appropriate permissions.
5. Test Keyless authentication.

### Create GCP service accounts and authorization policies

To create your service accounts, first export your GCP project name as an environment variable:

```
export PROJECT=<insert-gcp-project>
```

Once you’ve set the environment variable you’ll create a service account that will be used to federate access to Endor Labs and will be provided permission to access the Endor Labs APIs:

**Step 1:** Create a federation service account called `endorlabs-federation`:

```
gcloud iam service-accounts create endorlabs-federation --description="Endor Labs Keyless Federation Service Account" --display-name="Endor Labs Federation Service Account"
```

We’ll also create a second service account, that will have access to impersonate the `endorlabs-federation` account. We’ll call this `endorlabs-compute-service`.

This is needed if you don’t already have service accounts for your compute resources. If you do, you need to modify the existing permissions to allow the existing service account to create a federation token.

**Step 2:** Create a keyless authentication service account to assign to compute resources called `endorlabs-compute-service`:

```
gcloud iam service-accounts create endorlabs-compute-service --description="Endor Labs Service account for keyless authentication" --display-name="Endor Labs Compute Instance SA"
```

Finally, we’ll assign `endorlabs-compute-service` permissions to impersonate the `endorlabs-federation` account to authenticate to Endor Labs through OIDC.

**Step 3:** Assign the `serviceAccountOpenIdTokenCreator` role to the `endorlabs-compute-service` service account:

```
gcloud projects add-iam-policy-binding $PROJECT --member="serviceAccount:endorlabs-compute-service@$PROJECT.iam.gserviceaccount.com" --role="roles/iam.serviceAccountOpenIdTokenCreator"
```

Once we’ve created the necessary account permissions we will create an authorization policy in Endor Labs to allow the account `endorlabs-federation` to your Endor Labs tenant:

Use the following command to create an authorization policy in Endor Labs.

**Note**

Make sure to replace `<your-tenant>` with your Endor Labs tenant name and `<insert-your-project>` with your GCP project name in the following command.

```
endorctl api create -r AuthorizationPolicy -d '{
    "tenant_meta": { "namespace": "<your-tenant>" },
    "meta": {
        "name": "Keyless Auth",
        "kind": "AuthorizationPolicy",
        "tags": ["gcp"]
     },
     "spec": {
        "clause": ["email=endorlabs-federation@<insert-your-project>.iam.gserviceaccount.com", "gcp"],
        "target_namespaces": ["<your-tenant>"],
        "propagate": true,
        "permissions": {
            "rules": {},
            "roles": [
                "SYSTEM_ROLE_CODE_SCANNER"
            ]
        },
    }
}'
```

You’ve now set up the foundation of keyless authentication. You’ll now need to provision your compute resources with the appropriate GCP scopes and service account.

See [Provisioning and Testing Keyless Authentication for GKE workloads](#provisioning-and-testing-keyless-authentication-for-gke-workloads) for instructions on setting up GKE for keyless authentication.

See [Provisioning and Testing Keyless Authentication for GCP Virtual Machine Instances](#provisioning-and-testing-keyless-authentication-for-gcp-virtual-machine-instances) for instructions on setting up a virtual machine instance for keyless authentication.

### Provision and test keyless authentication for GKE workloads

#### Prerequisites

The following prerequisites are required to setup keyless authentication on GKE workloads:

* Workload identity is enabled on the target GKE cluster. See the [GCP documentation on using workload identity](https://cloud.google.com/kubernetes-engine/docs/how-to/workload-identity) for instructions on migrating existing cluster node pools or creating new clusters to use GCP workload identity.
* The gcloud auth plugin is installed and operational on your machine. See the [GCP instructions on enabling the gcloud auth plugin](https://cloud.google.com/blog/products/containers-kubernetes/kubectl-auth-changes-in-gke) for more details.
* The kubectl CLI is installed. See [the Kubernetes documentation](https://kubernetes.io/docs/tasks/tools/) for instructions.

#### Procedure

1. (Optional) Create a GKE cluster with workload identity enabled if you do not already have a GKE cluster
2. Authenticate to the GKE cluster
3. (Optional) Create a namespace for Endor Labs scans
4. Create a Kubernetes service account to impersonate your GKE compute service account
5. Bind your Kubernetes service account to your GCP compute service account
6. Annotate your Kubernetes service account with your GCP service account to complete your binding
7. Test a scanning workload using keyless authentication

### Set up and test keyless authentication in GKE

The following instructions require you to export the following environment variables to appropriately run:

* The GCP Project as PROJECT
* The GKE cluster as CLUSTER\_NAME

```
export PROJECT=<Insert_GCP_Project>
export CLUSTER_NAME=<GKE_CLUSTER>
```

**Optional Step 1:** To create a GKE cluster with workload identity enabled if you do not already have a GKE cluster with workload identity enabled run the following command:

```
gcloud container clusters create keyless-test --workload-pool=endor-github.svc.id.goog --scopes https://www.googleapis.com/auth/cloud-platform
```

**Step 2:** To authenticate to your GKE cluster run the following command:

```
gcloud container clusters get-credentials $CLUSTER_NAME
```

**Optional Step 3:** To create a namespace for Endor Labs scans run the following command:

```
kubectl create namespace endorlabs
```

**Step 4:** To create a Kubernetes service account to impersonate your GKE compute service account run the following command:

```
kubectl create serviceaccount endorlabs-compute-service -n endorlabs
```

**Step 5:** To bind your Kubernetes service account to your GCP compute service account run the following command:

**Note**

Make sure to replace `<insert-your-project>` in the following command with your GCP project name.

```
gcloud iam service-accounts add-iam-policy-binding endorlabs-compute-service@$PROJECT.iam.gserviceaccount.com --role roles/iam.workloadIdentityUser --member "serviceAccount:<insert-your-project>.svc.id.goog[endorlabs/endorlabs-compute-service]"
```

**Step 6:** To annotate your Kubernetes service account with your GCP service account to complete your binding run the following command:

**Note**

If you have created a different service account name replace *endorlabs-compute-service* with the appropriate service account name.

```
kubectl annotate serviceaccount endorlabs-compute-service -n endorlabs iam.gke.io/gcp-service-account=endorlabs-compute-service@$PROJECT.iam.gserviceaccount.com
```

Step 7: Test scan your project with keyless authentication

You’ve set up and configured keyless authentication. Now you can run a test scan to ensure you can successfully scan projects using keyless authentication.

## Provision and Test Keyless Authentication for GCP Virtual Machine Instances

The following high-level procedure describes the required steps to use keyless authentication with a GCP virtual machine instance:

**Procedure:**

1. Create a virtual machine instance with the appropriate scopes
2. Download and install endorctl on the virtual machine instance
3. Launch a test scan with keyless authentication

### Set up and Test Keyless authentication on a GCP virtual machine instance

The following instructions require you to export the following environment variables to appropriately run:

* The GCP Project as PROJECT

```
export PROJECT=<Insert_GCP_Project>
```

To successfully test keyless authentication first you’ll need to provision a compute resource with the service account `endorlabs-compute-service@$PROJECT.iam.gserviceaccount.com` and the scope `https://www.googleapis.com/auth/cloud-platform`:

**Step 1:** To create a virtual machine instance with the appropriate scopes run the following command:

```
gcloud compute instances create test-keyless --service-account endorlabs-compute-service@$PROJECT.iam.gserviceaccount.com --scopes https://www.googleapis.com/auth/cloud-platform
```

**Step 2:** To download and install endorctl on the virtual machine instance run the following series of commands:

First, SSH to the virtual machine instance you’ve created to test:

```
gcloud compute ssh --zone "us-west1-b" "test-keyless"  --project $PROJECT
```

Then download and install the latest version of `endorctl`. See [our documentation for instructions on downloading the latest version](../../../../endorctl/install-and-configure/)

To scan with keyless authentication you must use the flag `--gcp-service-account=endorlabs-federation@<insert-your-project>.iam.gserviceaccount.com` for federated access to Endor Labs such as in the below example:

```
endorctl api list --gcp-service-account=endorlabs-federation@<insert-your-project>.iam.gserviceaccount.com -r Project -n <insert-your-tenant> --count
```

If this scan runs successfully you’ve tested and scanned a project with keyless authentication to Endor Labs.

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
