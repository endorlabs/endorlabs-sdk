---
url: https://docs.endorlabs.com/administration/access-endorlabs/authentication-providers/custom-identity-providers/entraid-oidc-azure/
title: Set up Entra ID for SSO using OIDC | Endor Labs Docs
downloaded: 2026-01-29 22:22:45
---

Set up Entra ID for SSO using OIDC | Endor Labs Docs



* Type to search...

[Print entire section](/administration/access-endorlabs/authentication-providers/custom-identity-providers/entraid-oidc-azure/_print.html)



# Set up Entra ID for SSO using OIDC

Learn how to setup Microsoft Entra ID as a custom external identity provider for SSO with Endor Labs.

Integrate Endor Labs with Microsoft Entra ID (formerly Azure Active Directory) to use SSO through OpenID Connect (OIDC) protocol.

**Note**

Endor Labs honors the session duration set in OIDC, after which the user needs to reauthenticate. The token expiration claims (`exp`) control the session duration in OIDC. If your token does not include an expiration claim, the session duration defaults to four hours. The session duration cannot exceed four hours. If you set a session duration for more than four hours in the token expiration claim, the session duration defaults to four hours.

Complete the following tasks to configure Microsoft Entra ID for SSO through OIDC:

1. [Create and configure an OIDC application in Azure](#create-and-configure-an-oidc-application-in-azure)
2. [Create Entra ID SSO in Endor Labs](#create-entra-id-sso-in-endor-labs)

**Note**

You must have administrator access to configure the application end-to-end in Azure.

## Create and configure an OIDC application in Azure

Set up an application in Azure to enable OIDC configuration with Endor Labs.

1. Sign in to the [Azure portal](https://portal.azure.com/auth/login/).
2. Navigate to **App Registrations**.
3. Click **New Registration** to create a new application.
4. Enter `Endor Labs OIDC` as the name of your application.
5. Under **Supported Account Types**, select **Accounts in this organizational directory only (Single tenant)**.
6. Select **Web** as the platform under **Redirect URI**, then enter `https://api.endorlabs.com/v1/auth/oidc/callback` as the value.
7. Click **Register**.
8. Once you’ve set up your application, navigate to **Authentication** in your application.
9. Enter `https://api.endorlabs.com/v1/auth/oidc/logout` in **Front-channel logout URL**.
10. Click **Save**.

### Configure token claims in your application

Once you’ve created your application, you need to configure token claims to identify and authorize users.

1. Navigate to **Manage** > **Token configuration** in your application.
2. Select **Add optional claim**.
3. Choose **ID** as the **Token type**.
4. Select **email** and **upn (User Principal Token)** from the claims.
5. Click **Add**.
6. To use groups, select **Add groups claim**.
7. Choose **Security groups** to limit the scope to groups assigned to the application.
8. Choose **Group ID** as the **Token type**.
9. Click **Save**.

### Create a client secret

Create a client secret to allow Endor Labs to securely authenticate with the application.

1. Navigate to **Manage** > **Certificates & secrets** in your application.
2. Select **New client secret**.
3. Enter a description and select the expiry of the client secret.
4. Click **Add**.
5. Copy the **Value** immediately and store it in a secure location.

### Collect required values

To configure the custom identity provider in Endor Labs, you must retrieve the **Application (client) ID** and **Directory (tenant) ID** from your Azure application.

1. Navigate to **App Registrations**.
2. Select your application.
3. Select **Overview** from the left sidebar.
4. Copy the **Application (client) ID** and **Directory (tenant) ID**.

## Create Entra ID SSO in Endor Labs

Provide the Identity Provider details to configure Microsoft Entra ID in Endor Labs and allow users to seamlessly and securely sign in to Endor Labs.

**Note**

You must be an Endor Labs administrator to configure custom identity providers and authorization policies.

1. Sign in to Endor Labs.
2. Select **Access Control** under **Manage** in the left sidebar.
3. Select **Customer Identity Provider**.
4. Select the **TYPE OF IDENTITY PROVIDER** as **OIDC**.
5. Enter the **IDENTITY PROVIDER NAME** as **Microsoft Entra ID**.
6. In the **DISCOVERY URL** enter your discovery URL. This typically consists of your Directory (tenant) ID followed by `/.well-known/openid-configuration`.

   For example, `https://login.microsoftonline.com/abcd1234-5678-90ef-ghij-1234567890kl/v2.0/.well-known/openid-configuration`.
7. Enter the client ID and client secret from Azure that you copied earlier.
8. Under **Advanced Configuration**, enter the following in **scopes**: **email**, **openid**, and **profile**. Press **enter** after every entry to add each attribute successfully.
9. If you are configuring group-based authentication ensure to add **groups** in **claim names**.
10. Click **Save Configuration**.

**Note**

Based on your Microsoft Entra ID configuration, you may need additional Azure claim names as scopes in Endor Labs. Consult your Microsoft administrator for additional guidance.

### Configure your Authorization Policy

Once you’ve configured your custom identity provider in Endor Labs you must configure an authorization policy for your users and groups.

To set up an authorization policy:

1. Sign in to Endor Labs.
2. Select **Access Control** > **Auth Policy** from the left sidebar.
3. Select **Add Auth Policy**.
4. Enter **Microsoft Entra ID** as your identity provider.
5. Select the permissions you’d like to assign your user or group.
6. Under claims update your **Key**. Use **email** to assign individual users through email or **groups** to assign a user by group.
7. Assign the value to the key as the email of the user or **group id** you would like to authorize. This value is case-sensitive.
8. Repeat as needed for any additional users or groups.

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
