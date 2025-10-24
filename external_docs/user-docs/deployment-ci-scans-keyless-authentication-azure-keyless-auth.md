---
url: https://docs.endorlabs.com/deployment/ci-scans/keyless-authentication/azure-keyless-auth/
title: Keyless authentication for Azure | Endor Labs Docs
downloaded: 2025-10-23 23:25:42
---

Keyless authentication for Azure | Endor Labs Docs



* Type to search...
* ---

[Print entire section](/deployment/ci-scans/keyless-authentication/azure-keyless-auth/_print.html)



# Keyless authentication for Azure

Learn how to implement keyless authentication for Azure.

To enable keyless authentication in Azure, you need to configure your Azure virtual machine with a managed identity and create an authorization policy in Endor Labs.

Complete the following tasks to set up keyless authentication in Azure.

1. [Enable Azure Managed Identity for the virtual machine in the Azure Portal.](#enable-azure-managed-identity)
2. [Configure the Azure virtual machine.](#configure-the-azure-virtual-machine)
3. [Create an authorization policy in Endor Labs.](#create-an-authorization-policy-in-endor-labs)

## Enable Azure managed identity

You must enable Azure Managed Identity for your virtual machine from the Azure portal. For more information, refer to [Azure managed identity](https://learn.microsoft.com/en-us/entra/identity/managed-identities-azure-resources/how-to-configure-managed-identities?pivots=qs-configure-portal-windows-vm).

## Configure the Azure virtual machine

You need to configure the Azure virtual machine with endorctl and configure endorctl to use Azure Managed Identify.

### Verify the connection to the Azure virtual machine instance

Log in to your Azure virtual machine and run the following command.

```
curl -s -H Metadata:true "http://169.254.169.254/metadata/instance?api-version=2021-02-01"
```

The command returns the metadata details of the virtual machine instance in the raw json format.

### Download endorctl on the virtual machine instance

Download and install the latest version of endorctl in your virtual machine. See [endorctl](../../../../endorctl/install-and-configure/) for the various methods available to install endorctl.

The following example shows how you can download the endorctl binary directly.

```
## Download the latest CLI for Windows AMD64
curl -O https://api.endorlabs.com/download/latest/endorctl_windows_amd64.exe
## Check the expected checksum of the binary file
curl https://api.endorlabs.com/sha/latest/endorctl_windows_amd64.exe
## Verify the expected checksum and the actual checksum of the binary match
certutil -hashfile .\endorctl_windows_amd64.exe SHA256
## Rename the binary file
ren endorctl_windows_amd64.exe endorctl.exe
```

### Set the environment variable

Set the environment variable `ENDOR_AZURE_CREDENTIALS_MANAGED_IDENTITY_ENABLE` to true in your virtual machine instance.

```
export ENDOR_AZURE_CREDENTIALS_MANAGED_IDENTITY_ENABLE=true
```

Run the following command to check the status of the environment variable.

```
echo $ENDOR_AZURE_CREDENTIALS_MANAGED_IDENTITY_ENABLE
```

If the variable is set, then the command returns `true`.

## Create an authorization policy in Endor Labs

Create an authorization policy for Azure in the Endor Labs user interface. See [set up authorization policy](../../../../administration/access-endorlabs/authorization-policies/#set-up-authorization-policies) for more information on creation an authorization policy.

Choose the following parameters when you create the authorization policy.

* Select **Azure** as the **Identity Provider**.
* Select **Code Scanner** in **Permissions**.
* Enter the following values for the claims:

  + Tenant ID: Identifies your Azure organization.
  + App ID: Identifies the application requesting access.
  + Object ID: Unique ID assigned to the virtual machine.
  + Subscriptions: Azure subscriptions linked to the identity.

![azure authorization policy](../../../../images/azure-auth-policy.png)

### Test keyless authentication

Once the authorization policy is set up, you can test keyless authentication using endorctl.

For example, run the following command to fetch the number of projects in a namespace with keyless authentication set up.

```
endorctl api list -r Project -n demo --enable-azure-managed-identity --count
```

The following example shows the response for the preceding command when keyless authentication is successful.

```
{
  "count_response": {
    "count": 3
  }
}
```

You’ve set up and configured keyless authentication. Now you can run a test scan to ensure you can successfully scan projects using keyless authentication with Azure.

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
