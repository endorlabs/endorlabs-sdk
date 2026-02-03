---
url: https://docs.endorlabs.com/administration/access-endorlabs/authentication-providers/custom-identity-providers/
title: Set up SSO with Endor Labs | Endor Labs Docs
downloaded: 2026-02-03 00:49:56
---

Set up SSO with Endor Labs | Endor Labs Docs



* Type to search...

[Print entire section](/administration/access-endorlabs/authentication-providers/custom-identity-providers/_print.html)



# Set up SSO with Endor Labs

Set up SAML or OIDC single sign on for Endor Labs with in your organization.

Single Sign-On (SSO) provides a seamless sign-in by enabling users to access external applications and services without re-entering the credentials. Endor Labs supports SAML or OIDC-based identity providers.

SAML is an XML-based protocol used for exchanging authentication and authorization data between applications.

OpenID Connect (OIDC) is an identity layer on top of the OAuth 2.0 framework that allows applications to verify the identity and claims of users.

Using Endor Labs, you can integrate using an Identity Provider (IdP) that supports SAML or OIDC, such as Okta, Microsoft Active Directory Federation Services (AD FS), Azure Active Directory (AD), Google, or OneLogin.

The default duration of a user session is four hours, if you have not set the session duration in your IdP. Endor Labs honors the session duration set in the IdP, after which the user needs to reauthenticate. You can set the session duration in the `SessionNotOnOrAfter` attribute for SAML. The token expiration claims (`exp`) control the session duration in OIDC.

Session duration cannot be more than four hours. If you set a session duration for more than four hours at the IdP, the session duration defaults to four hours.

Complete the following tasks to integrate an SSO-based identity provider with Endor Labs.

## Keep Service Provider (Endor Labs) details handy

To configure Endor Labs as a SAML 2.0 app, you must have the following service provider details:

* **Single sign-on URL**: This is the API endpoint of the application, where your identity provider redirects the user after successful authentication. You have to enter `https://api.endorlabs.com/v1/auth/saml-callback?tenant=yourtenant`. Replace `yourtenant` with your actual tenant name.
* **Audience URI**: This is a globally unique name for the service provider. You have to enter `https://api.endorlabs.com/v1/auth/sso`.

To configure Endor Labs as an OIDC app, you must have the following service provider details:

* **Sign-in redirect URIs**: This is the API endpoint of the application, where your identity provider redirects the user after successful authentication. You have to enter: `https://api.endorlabs.com/v1/auth/oidc/callback`.
* **Sign-out redirect URIs**: This is the API endpoint of the application, where your identity provider redirects the user after successful logout. You have to enter: `https://api.endorlabs.com/v1/auth/oidc/logout`.

## Retrieve Setup information from your IdP

The following information is needed for SAML and OIDC configuration setup in Endor Labs.

### Setup information for SAML Authentication

To set up SAML SSO with Endor Labs you will need the following information from your IdP:

* **Sign-On URL**: The SAML SSO remote sign-in URL of IdP.
* **Issuer**: The unique ID of IdP for Endor Labs.
* **Signing Certificate**: The public key certificate of your IdP.

### Setup Information for OIDC Authentication

To set up OIDC SSO with Endor Labs you will need the following information from your IdP:

* **Identity Provider Discovery URL**: The OIDC discovery URL of your identity provider.
* **Client Key**: The unique key of IdP for Endor Labs.
* **Client Secret**: The secret key of your IdP for Endor Labs.
* **Required Claims and Scopes**: The required claims and scopes if non-standard for your OIDC connection.

## Configure SAML in Endor Labs

Provide the Identity Provider SSO details in Endor Labs and allow users to seamlessly and securely sign in to Endor Labs.

1. Sign in to Endor Labs.
2. From the sidebar, navigate to Settings and click **CUSTOM IDENTITY PROVIDER**.
3. Select the **TYPE OF IDENTITY PROVIDER** as **SAML**.
4. Enter a name for your **IDENTITY PROVIDER NAME**.
5. From **METADATA DEFINITION**, select **Metadata URL** and enter the **SAML Identity provider metadata URL** or **Discovery URL** from your IdP.
6. If you want to enter the identity provider details manually, choose **METADATA DEFINITION** as **Manual** and enter the following details that you saved from IdP.

   * DISCOVERY URL: Enter **Sign-On URL** from IdP.
   * ISSUER: Enter **Issuer** from IdP.
   * ATTRIBUTES: Enter your attributes such as email and groups. Type the values and press enter.
   * CERTIFICATE: Enter the **Signing Certificate** from IdP.
7. Click **Save Configuration**.

## Configure OIDC in Endor Labs

Provide the following Identity Provider SSO details to configure OIDC SSO in Endor Labs and allow users to seamlessly and securely sign in to Endor Labs.

1. Sign in to Endor Labs.
2. From the sidebar, navigate to Settings and click **CUSTOM IDENTITY PROVIDER**.
3. Select the **TYPE OF IDENTITY PROVIDER** as **OIDC**.
4. Enter the **IDENTITY PROVIDER NAME** for your selected identity provider.
5. Under **DISCOVERY URL** enter your discovery URL. This is usually your Okta domain followed by /.well-known/
   openid-configuration. For example, `https://endorlabs.okta.com/.well-known/openid-configuration`.
6. Enter your Client ID and Client Secret from your IdP.
7. Under **Advanced Configuration** enter the following scopes in the **scopes** section: **email**, **groups**, **profile**. Make sure to hit enter after each to add each attribute.
8. If you are configuring group-based authentication ensure to add **groups** in the **Claim Names** section.
9. Click **Save Configuration**.

**Note**

Based on your IdP configuration you may need additional claim names or scopes. Consult your IdP administrator for additional guidance.

## Configure your Authorization Policy

Once you’ve configured your custom identity provider in Endor Labs you must set up an authorization policy for your users and groups.

To configure an authorization policy:

1. Sign in to Endor Labs.
2. From the sidebar, navigate to Settings and click **Auth Policy**.
3. Click the **Add Auth Policy** button.
4. Enter the name you selected for your custom identity provider as your identity provider.
5. Select the permissions you’d like to assign your user or group.
6. Under claims update your **Key**. Use **email** to assign individual users through email or **groups** to assign a user by group.
7. Assign the value to the key as the email of the user or group you would like to authorize. This value is case-sensitive.
8. Repeat as needed for any additional users or groups.

## Verify Sign-in

Use the user account to sign in to Endor Labs from your IdP and validate the SSO integration.

1. Sign in to IdP as a user.
2. Navigate to <https://app.endorlabs.com>
3. Click Login with Enterprise SSO
4. Enter the namespace you’d like to sign in to within Endor Labs.

For Okta-specific instructions, see [SSO using Okta](../custom-identity-providers/okta-oidc/)

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
