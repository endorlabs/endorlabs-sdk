---
url: https://docs.endorlabs.com/administration/access-endorlabs/authentication-providers/custom-identity-providers/okta-oidc/
title: Set up Okta for SSO using OIDC | Endor Labs Docs
downloaded: 2026-02-03 00:50:05
---

Set up Okta for SSO using OIDC | Endor Labs Docs



* Type to search...

[Print entire section](/administration/access-endorlabs/authentication-providers/custom-identity-providers/okta-oidc/_print.html)



# Set up Okta for SSO using OIDC

Learn how to setup Okta as a custom external identity provider for SSO with Endor Labs

Endor Labs integrates with Okta to use SSO through OpenID Connect (OIDC) protocol.

**Tip**

Endor Labs honors the session duration set in OIDC, after which the user needs to reauthenticate. The token expiration claims (`exp`) control the session duration in OIDC. If you do not have token expiration claims, the default session duration is four hours. Session duration cannot be more than four hours. If you set a session duration for more than four hours in the token expiration claim, the session duration defaults to four hours.

Complete the following tasks to configure Okta for SSO through OIDC.

## Create and configure an OIDC application in Okta

In Okta, configure the Endor Labs application as an OIDC application and generate a single sign-on URL and certificate.

**Tip**

You must be an Okta administrator to configure the application end-to-end in Okta.

1. Sign in to the Okta admin account.
2. Navigate to **Applications** > **Applications**.
3. To create an app integration, click **Create App Integration**.
4. Select **OIDC - OpenID Connect**.
5. Under Application type select **Web Application** and click **Next**.
6. Enter the following details in **General Settings** and click **Next**.

   * **App integration name**: Enter Endor Labs.
   * **App Logo (optional)**: Upload the Endor Labs logo in PNG, JPG, or GIF format. The logo size must be less than 1 MB.
   * **Sign-in redirect URIs**: Enter `https://api.endorlabs.com/v1/auth/oidc/callback`
   * **Sign-out redirect URIs**: Enter `https://api.endorlabs.com/v1/auth/oidc/logout`
   * Under **Assignments**: Select if you’d like to assign all users or only a specified group then click **Save**.
7. Once you’ve set up your application, some additional configuration is required. Navigate to **Sign On** in the application.
8. Under **OpenID Connect ID Token** select **Edit**.
9. Select **Groups claim type** as **Filter** and ensure **groups** is selected with the **Matches Regex** filter of `.*` or a regex matching your group or groups name.
10. Click **Save Configuration**.

### Assign the appropriate users and groups to the application

Once you’ve created your Application you need to assign the appropriate users and groups as assignments.

1. Select **Assignments** in your newly created application.
2. Click **Assign** and select **Assign to people** or **Assign to groups** if you are configuring group authorization.
3. Search for and select the group you’d like to assign and click **Done**.

### Get Identity Provider details from Okta

Once you’ve created your Okta app and assigned groups you must retrieve your Okta
the Okta identity provider SSO details to configure Okta in Endor Labs.

1. Select **Sign On**.
2. From **Metadata Details**, copy the **Metadata URL**.
3. Save the following details and have them handy if you’d like to manually configure SAML:
   * **Sign-On URL**: The SAML SSO URL of Okta.
   * **Issuer**: The unique ID of Okta for Endor Labs.
   * **Signing Certificate**: The public key certificate of Okta.

## Configure Okta OIDC SSO in Endor Labs

Provide the Identity Provider SSO details to configure Okta SSO in Endor Labs and allow users to seamlessly and securely sign in to Endor Labs.

**Tip**

You must be an Endor Labs administrator to configure custom identity providers and authorization policies.

1. Sign in to Endor Labs.
2. Select **Access Control** under **Manage** in the left sidebar.
3. Select **Customer Identity Provider**.
4. Select the **TYPE OF IDENTITY PROVIDER** as **OIDC**.
5. Enter the **IDENTITY PROVIDER NAME** as **Okta OIDC**.
6. Under **DISCOVERY URL** enter your discovery URL. This is usually your Okta domain followed by `/.well-known/openid-configuration`. For example, `https://endorlabs.okta.com/.well-known/openid-configuration`.
7. Enter your Client ID and Client Secret from Okta.
8. Under **Advanced Configuration** enter the following scopes in the **scopes** section: **email**, **groups**, **profile**. Press **enter** after every entry to add each attribute successfully.
9. If you are configuring group-based authentication ensure to add **groups** in the **Claim Names** section.
10. Click **Save Configuration**.

**Note**

Based on your Okta configuration you may need additional claim names or scopes. Consult your Okta administrator for additional guidance.

### Configure your Authorization Policy

Once you’ve configured your custom identity provider in Endor Labs you must configure an authorization policy for your users and groups.

To set up an authorization policy:

1. Sign in to Endor Labs.
2. Select **Access Control** > **Auth Policy** from the left sidebar.
3. Select **Add Auth Policy**.
4. Enter **Okta OIDC** as your identity provider.
5. Select the permissions you’d like to assign your user or group.
6. Under claims update your **Key**. Use **email** to assign individual users through email or **groups** to assign a user by group.
7. Assign the value to the key as the email of the user or group you would like to authorize. This value is case-sensitive.
8. Repeat as needed for any additional users or groups.

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
