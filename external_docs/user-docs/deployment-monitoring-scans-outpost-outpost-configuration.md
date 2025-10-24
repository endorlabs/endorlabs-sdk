---
url: https://docs.endorlabs.com/deployment/monitoring-scans/outpost/outpost-configuration/
title: Outpost configuration | Endor Labs Docs
downloaded: 2025-10-23 23:26:03
---

Outpost configuration | Endor Labs Docs



* Type to search...
* ---

[Print entire section](/deployment/monitoring-scans/outpost/outpost-configuration/_print.html)



# Outpost configuration

Learn about the configuration for Outpost.

After you [set up your Kubernetes cluster](../outpost-requirements/) and [set up authentication](../outpost-authentication/), you can configure the Outpost integration.

## Configure Outpost integration

To set up Outpost in your environment, you need to configure the integration through the Endor Labs user interface and deploy it to your Kubernetes cluster.

Perform the following steps to configure Outpost:

1. Select **Integrations** from the left sidebar.
2. Click **Configure** under **On-Prem Integration**.

   ![Outpost configuration](../../../../images/OutpostConfiguration.png)
3. Choose from the following authentication methods:

   * **API**: Use the Endor Labs API key authentication for Outpost. You need to enter the API key and API secret. See [API key authentication for Outpost](../outpost-authentication/#API-key-authentication-for-Outpost) for more information.
   * **Azure**: Use the Azure managed identity authentication for Outpost. You need to enter the Azure managed identity client ID. See [Azure Managed Identity authentication for Outpost](../outpost-authentication/#azure-managed-identity-authentication-for-outpost) for more information.
   * **Google**: Use the GCP service account authentication for Outpost. You need to enter the GCP service account name. See [GCP Service Account authentication for Outpost](../outpost-authentication/#gcp-service-account-authentication-for-outpost) for more information.
4. Click **Advanced** to configure the following parameters:

   * Select **Enable Build Tool Caching** to enable build tool caching. Bazel remote cache is installed and the build tools are cached in the cluster.
   * Enter the number of concurrent scans that Outpost can run in **Max Running Scans**.
   * Enter the maximum duration of a scan in **Max Duration**.
5. Click **Enable Scheduler** to store the configuration and enable Outpost.
6. Click **Download Helm Values** to download the `endor-outpost-values.yaml` file.

   You can choose to customize the values before you deploy Outpost.

   You can also extract the chart from `oci://endorcipublic.azurecr.io/charts/onprem-scheduler` and refer the default `values.yaml` for all the available options. See [Helm Chart Values](#helm-chart-values) for more information.
7. Run the following command to deploy Outpost in your Kubernetes cluster.

   ```
   helm install endorlabsscheduler oci://endorcipublic.azurecr.io/charts/onprem-scheduler \
   -n <your Kubernetes namespace> \
   -f endor-outpost-values.yaml
   ```

   The command installs the Outpost scheduler on your Kubernetes cluster.

   #### Important

   If you use GCP service account authentication, you need to configure annotations for the service account in Helm values.

   Add the following annotations to the Helm chart values before you run the Helm install command.

   ```
   scheduler:
    .
    .
     serviceAccount:
       create: true
       annotations:
         iam.gke.io/gcp-service-account: "endor-scanner-sa@project-name-123456.iam.gserviceaccount.com"
   endorctl:
    .
    .
     serviceAccount:
       create: true
       annotations:
         iam.gke.io/gcp-service-account: "endor-scanner-sa@project-name-123456.iam.gserviceaccount.com"
   ```

   If you run the Helm command directly, update the generated Helm command to set the annotations with the following options:

   ```
   --set scheduler.serviceAccount.annotations.iam.gke.io/gcp-service-account="<GCP_SERVICE_ACCOUNT_NAME>@<GCP_PROJECT_NAME>.iam.gserviceaccount.com"
   --set endorctl.serviceAccount.annotations.iam.gke.io/gcp-service-account="<GCP_SERVICE_ACCOUNT_NAME>@<GCP_PROJECT_NAME>.iam.gserviceaccount.com"
   ```

   For example:

   ```
   helm install endorlabsscheduler oci://endorcipublic.azurecr.io/charts/onprem-scheduler \
       -n <k8s-ns> \
       --set endorAPI=https://api.staging.endorlabs.com \
       --set endorNamespace=nryn \
       --set auth.gcpServiceAccountName=endor-scanner-sa@project-name-123456.iam.gserviceaccount.com \
       --set scheduler.serviceAccount.annotations.iam.gke.io/gcp-service-account="endor-scanner-sa@project-name-123456.iam.gserviceaccount.com" \
       --set endorctl.serviceAccount.annotations.iam.gke.io/gcp-service-account="endor-scanner-sa@project-name-123456.iam.gserviceaccount.com" \
       --set bazelremote.install=false
   ```

   The annotations are automatically added to the Helm chart values if you choose Azure managed identity authentication.
8. If you do not want to customize the values, the Helm command with your configured values appears in the user interface. You can copy the command and run it on your Kubernetes cluster.

   For example, the following command appears on the user interface when you configure the integration on the `endor` Kubernetes namespace with the Azure managed identity authentication and build tool caching enabled. The root Endor Labs namespace is `endor`.

   ```
   helm install endorlabsscheduler oci://endorcipublic.azurecr.io/charts/onprem-scheduler \
        -n endor \
        --set endorAPI=https://api.endorlabs.com \
        --set endorNamespace=endor \
        --set auth.azureManagedIdentityClientID=12a34b56-7c89-0d1e-2f34-567g890h1234 \
        --set bazelremote.install=true
   ```

   You can copy the command and run it on your Kubernetes cluster to deploy Outpost.

## Update Outpost configuration

To update the Outpost configuration, you need to uninstall the existing Helm chart and install a new one with the updated values.

Run the following command to uninstall the existing Helm chart.

```
helm uninstall endorlabsscheduler -n <your namespace>
```

You can update the configuration in the user interface to generate a new Helm chart or command, or you can manually update the values in the `endor-outpost-values.yaml` file. We recommend that you update the configuration in the user interface even if you manually update and install the Helm chart.

Perform the following steps to update the configuration in the user interface:

1. Select **Integrations** from the left sidebar.
2. Click **Manage** under **On-Prem Integration**.
3. Update the configuration and click **Enable Scheduler** to update the configuration.
4. Apply the updated values with the `helm install` command as described in [Configure Outpost integration](#configure-outpost-integration).

Generally, you need to update the configuration when the authentication expires. API keys have a maximum validity period of one year. The expiry of Azure managed identity and GCP service accounts depends on the expiry of the corresponding authorization policy.

## View Outpost logs

You can view the Outpost logs in the Endor Labs platform.

Perform the following steps to view the Outpost logs:

1. Select **Integrations** from the left sidebar.
2. Click **View Logs** under **On-Prem Integration**.

   ![Outpost logs](../../../../images/OutpostLogs.png)

   You can copy the logs to the clipboard or download the logs.

   By default, the logs are brief logs are displayed. You can select **Show Verbose Logs** to view the detailed logs.

   The log level is set as **All** by default. You can select **Info** to view the info logs and **Debug** to view the debug logs.

## Helm Chart Values

Run the following command to extract the default values for the Outpost Helm chart.

```
helm pull oci://endorcipublic.azurecr.io/charts/onprem-scheduler --untar
```

The `values.yaml` file in the `onprem-scheduler` directory contains the default values for the Outpost Helm chart.

The following yaml file shows the default values in the `values.yaml` file.

```
# Default values for onprem-scheduler.
# This file is YAML-formatted.

# Base URL for the Endor Labs platform [Do not modify]
endorAPI: "https://api.endorlabs.com"

# Your organization's namespace in Endor Labs [Do not modify unless there is a change in your tenant]
endorNamespace: "required"

# Log level for scheduler and endorctl. Optional.
logLevel: "info"

# Log output format for scheduler. Optional.
logOutput: "json"

# Authentication configuration - use ONE of the following methods.
# NOTE: Only one authentication method (apiKey & apiSecret, gcpServiceAccountName,
# or azureManagedIdentityClientID) must be set.
auth:
  # Option 1: API Key authentication. Enter the Endor Labs API key and secret.
  # You can also create Kubernetes secrets for the API key and secret and provide the secret names instead of directly entering the values.
  apiKey: ""
  apiSecret: ""

  # Option 2: GCP Service Account authentication. Enter the GCP service account name.
  # NOTE: Ensure service accounts are created with workload identity annotations.
  gcpServiceAccountName: ""

  # Option 3: Azure Managed Identity authentication. Enter the Azure managed identity client ID.
  # NOTE: Ensure service accounts are created with workload identity annotations.
  azureManagedIdentityClientID: ""

scheduler:
  # Maximum number of scans that you want to run concurrently. Optional.
  maxRunningJobs: 20

  # Scheduler container image settings.
  image:
    # Container repository for the scheduler image [Do not modify]
    repository: "endorcipublic.azurecr.io/scheduler"

    # Image version to use [Do not modify]
    tag: "latest"

    # Image pull policy [Do not modify]
    pullPolicy: "Always"

  # Labels for the scheduler deployment. Optional.
  labels: {}

  # Annotations for the scheduler deployment. Optional.
  annotations: {}

  # Labels for the scheduler pod. Optional.
  podLabels: {}

  # Annotations for the scheduler pod. Optional.
  podAnnotations: {}

  serviceAccount:
    # Specifies whether a service account should be created. Optional.
    create: false

    # Name of the service account to use for scheduler. Optional.
    name: ""

    # Labels for the scheduler service account. Optional.
    labels: {}

    # Annotations for the scheduler service account. Optional.
    annotations: {}

  # Pod-level security context for the scheduler. Optional.
  podSecurityContext: {}

  # Container-level security context for the scheduler. Optional.
  securityContext: {}

  # Resource constraints for the scheduler pod. Optional.
  resources:
    requests:
      cpu: 512m
      memory: 512Mi

  healthProbes:
    # Port used to perform health checks. Optional.
    port: 8080

    # Readiness probe for the scheduler pod. Optional.
    readinessProbe:
      enabled: true
      failureThreshold: 2
      successThreshold: 1
      periodSeconds: 5
      timeoutSeconds: 1
      initialDelaySeconds: 10

    # Liveness probe for the scheduler pod. Optional.
    livenessProbe:
      enabled: true
      failureThreshold: 4
      periodSeconds: 10
      successThreshold: 1
      timeoutSeconds: 1
      initialDelaySeconds: 0

  # Node selector for the scheduler pod. Optional.
  nodeSelector: {}

  # Tolerations for the scheduler pod. Optional.
  tolerations: []

  # Affinity settings for the scheduler pod. Optional.
  affinity: {}

  # Volumes for the scheduler pod. Optional.
  volumes: []

  # Volume mounts for the scheduler pod. Optional.
  volumeMounts: []

  # Additional environment variables for the scheduler pod. Optional.
  additionalEnvs: []

endorctl:
  # Maximum runtime duration in minutes for a scan. Optional. Default value is 60.
  maxDuration: 1440

  bazelRemote:
    # Bazel remote cache service name.
    # Refer bazelremote values below. Optional.
    serviceName: "bazel-remote-cache"

    # Bazel remote cache GRPC service port.
    # Refer bazelremote values below. Optional.
    servicePort: 9092

  # Endorctl container image settings.
  image:
    # Container repository for the endorctl image [Do not modify]
    repository: "endorcipublic.azurecr.io/endorctl_bare"

    # Image version to use [Do not modify]
    tag: "latest"

    # Image pull policy [Do not modify]
    pullPolicy: "Always"

  # Labels for the endorctl job. Optional.
  labels: {}

  # Annotations for the endorctl job. Optional.
  annotations: {}

  # Labels for the endorctl pod. Optional.
  podLabels: {}

  # Annotations for the endorctl pod. Optional.
  podAnnotations: {}

  serviceAccount:
    # Specifies whether a service account should be created. Optional.
    create: false

    # Name of the service account to use for endorctl. Optional.
    name: ""

    # Labels for the endorctl service account. Optional.
    labels: {}

    # Annotations for the endorctl service account. Optional.
    annotations: {}

  # Pod-level security context for the endorctl. Optional.
  podSecurityContext: {}

  # Container-level security context for the endorctl. Optional.
  securityContext: {}

  # Resource constraints for the endorctl job. Optional.
  resources: {}

  # Node selector for the endorctl pod. Optional.
  nodeSelector: {}

  # Tolerations for the endorctl pod. Optional.
  tolerations: []

  # Affinity settings for the endorctl pod. Optional.
  affinity: {}

  # Volumes for the endorctl pod. Optional.
  volumes: []

  # Volume mounts for the endorctl pod. Optional.
  volumeMounts: []

  # Backoff limit for the endorctl job. Optional.
  backoffLimit: 0

  # TTL seconds after finished for the endorctl job. Optional.
  ttlSecondsAfterFinished: 100

  # Additional environment variables for the endorctl pod. Optional.
  additionalEnvs: []

#
# DEPENDENCIES
#

# Bazel remote cache configuration. Optional. Not enabled by default.
bazelremote:
  # Whether to install the Bazel remote cache component
  install: false

  image:
    # Container repository for the Bazel remote cache image [Do not modify]
    repository: "buchgr/bazel-remote-cache"

    # Specific version of the Bazel remote cache to use [Do not modify]
    tag: "v2.4.1"

    # Image pull policy [Do not modify]
    pullPolicy: "IfNotPresent"

  # Full name of the chart. Optional.
  fullnameOverride: "bazel-remote-cache"

  # Bazel-remote config to provision inside of the container. Optional.
  conf: |-
    # https://github.com/buchgr/bazel-remote#example-configuration-file
    dir: /data
    max_size: 500
    experimental_remote_asset_api: true
    access_log_level: all
    port: 8080
    grpc_port: 9092

  ## For advanced bazel-remote configuration options,
  ## Refer https://github.com/slamdev/helm-charts/tree/master/charts/bazel-remote#readme
```

## Post-deployment configuration

After deploying Outpost to your Kubernetes cluster, you need to set up the appropriate Endor Labs app to integrate with your source code management system. This integration enables Outpost to scan your repositories.

You can install Endor Labs apps for the following source code managers:

* [GitHub Cloud](../../github-app/)
* [GitLab Cloud and self-hosted](../../gitlab-app/)
* [Bitbucket Data Center](../../bitbucket-datacenter-app/)
* [Bitbucket Cloud](../../bitbucket-cloud/)
* [Azure DevOps Cloud](../../azure-app/)

## Configure Outpost on GitLab self-hosted with self-signed certificates

When you configure Outpost on GitLab self-hosted with self-signed certificates, you need to add the self-signed certificate to the Outpost Helm chart values.

#### Note

Proper certificate validation is crucial for secure communication between Outpost and your GitLab self-hosted instance. Ensure that the self-signed certificate is valid and properly configured to prevent any security issues.

Perform the following steps to add the self-signed certificate to the Outpost Helm chart values and deploy Outpost with GitLab self-hosted.

1. Download the self-signed certificate from the GitLab self-hosted instance.
2. Create a `kubectl configmap` using the certificate in the Outpost cluster.

   ```
   kubectl create configmap gitlab-cert --from-file=<cert-name>=<path-of-the-certificate> -n <name-of-the-namespace>
   ```

   For example:

   ```
   kubectl create configmap gitlab-cert --from-file=gitlab-dev-CA.pem=/Users/doe/Downloads/gitlab-dev-CA.pem -n onprem-scheduler
   ```
3. [Configure Outpost and download `endor-outpost-values.yaml` file.](#configure-outpost-integration)
4. Modify the values yaml file to volume mount the certificate in the scheduler and endorctl image.

   ```
   endorAPI: "https://api.endorlabs.com"
   endorNamespace: "<Endor Labs namespace>"
   auth:
     apiKey: "<apiKey>"
     apiSecret: "<apiSecret>"
   scheduler:
     image:
       repository: "endorcipublic.azurecr.io/scheduler"
       tag: "latest"
       pullPolicy: "Always"
     volumes:
       - name: gitlab-cert
         configMap:
           name: gitlab-cert
     volumeMounts:
       - name: gitlab-cert
         mountPath: /etc/ssl/certs/gitlab-dev-CA.pem
         subPath: gitlab-dev-CA.pem
   endorctl:
     image:
       repository: "endorcipublic.azurecr.io/endorctl_bare"
       tag: "latest"
       pullPolicy: "Always"
     volumes:
       - name: gitlab-cert
         configMap:
           name: gitlab-cert
     volumeMounts:
       - name: gitlab-cert
         mountPath: /etc/ssl/certs/gitlab-dev-CA.pem
         subPath: gitlab-dev-CA.pem
   ```
5. Run the following command to deploy Outpost in your Kubernetes cluster.

   ```
   helm install endorlabsscheduler oci://endorcipublic.azurecr.io/charts/onprem-scheduler \
   -n <your Kubernetes namespace> \
   -f endor-outpost-values.yaml
   ```
6. [Install the GitLab App.](../../gitlab-app/)

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
