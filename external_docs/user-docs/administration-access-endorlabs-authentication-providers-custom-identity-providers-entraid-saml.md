---
url: https://docs.endorlabs.com/administration/access-endorlabs/authentication-providers/custom-identity-providers/entraid-saml/
title: Set up Entra ID for SSO using SAML | Endor Labs Docs
downloaded: 2025-10-27 12:58:53
---

Set up Entra ID for SSO using SAML | Endor Labs Docs



* Type to search...
* ---

[Print entire section](/administration/access-endorlabs/authentication-providers/custom-identity-providers/entraid-saml/_print.html)



# Set up Entra ID for SSO using SAML

Set up Microsoft Entra ID as a custom identity provider for SSO with Endor Labs.

You can integrate Endor Labs with Microsoft Entra ID (formerly Azure Active Directory) to use the Security Assertion Markup Language (SAML) 2.0 protocol for single sign-on (SSO) with Endor Labs.

With the Endor Labs–Entra ID SAML integration, Endor Labs acts as the Service Provider (SP), and Microsoft Entra ID acts as the Identity Provider (IdP). When users sign in to Endor Labs using SAML, the SAML protocol triggers an authentication request to Entra ID, which returns a SAML assertion to Endor Labs. Users are then authenticated to access the application.

#### Note

The default session duration for SAML authentication is four hours. You can modify the `SessionNotOnOrAfter` attribute to lower the session duration. See [Session duration](../../../authentication-providers/#session-duration) for more information.

Complete the following tasks to set up SAML-based single sign-on (SSO) using Entra ID as the identity provider for Endor Labs.

## Create and configure SAML application in Entra ID

To set up SAML, your organization’s Entra ID administrator must create an application for Endor Labs and generate the SSO URL and certificate.

To configure your Endor Labs application in Entra ID:

1. Sign in to Entra ID. Select **Enterprise Applications** and click **Create your own application**.
2. Enter `Endor Labs` as the name of your application and select **Integrate any other application you didn’t find in the gallery (Non-gallery)**.
3. Click **Create** to initiate creating your enterprise application.
4. Under **Overview**, click **Single sign-on** and select **SAML**. This redirects you to the **SAML-based Sign-on** page.
5. Edit the following details in **Basic SAML Configuration** and click **Save**.

   * **Identifier (Entra ID)**: `https://api.endorlabs.com/v1/auth/sso`
   * **Reply URL (Assertion Consumer Service URL)**: `https://api.endorlabs.com/v1/auth/saml-callback?tenant=yourtenant`

     #### Note

     Replace `yourtenant` with your tenant name.

     ![](../../../../../images/entraid-saml-setup.png)
6. In **Attributes & Claims**, select **Edit** to add required claims, additional claims and group claims.

   a. Select **Add new claim** and fill the following details:

   * **Name**: Enter `email`.
   * **Source**: Select **Attribute**.
   * **Source Attribute**: Select `user.email` from the list.

   b. Select **Add a group claim** and configure the following in the right sidebar.

   * **Which groups associated with the user should be returned in the claim?**: Select **Security groups**.
   * **Source attribute**: Select **Group ID** from the list.
   * **Advance options**: Select **Customize the name of the group claim**, and enter `groups` in **Name (required)**.![](../../../../../images/entraid-attributes-claims.png)

   c. Click **Save** and return to **SAML-based Sign-on**.
7. Copy the **App Federation Metadata URL** available in **SAML Certificates**.

   ![](../../../../../images/entraid-saml-metadataURL.png)

## Create Entra ID SSO in Endor Labs

After creating the application in Entra ID, configure Endor Labs to use Entra ID as the identity provider (IdP).

To set up Entra ID as your SAML IdP:

1. Sign in to Endor Labs and select **Access Control** from the left sidebar.
2. Select **Custom Identity Provider**.
3. Provide the following details.
   * **Type of Identity Provider**: SAML.
   * **Identity Provider Name**: Entra ID.
   * **SAML Identity Provider Metadata URL**: Enter the Metadata URL copied from SAML certificates section in Entra ID.
   * **Attributes**: Enter **email**, **groups**. Separate the attributes using the `enter` or `return` key.

     ![](../../../../../images/entraid-endorlabs-custom-idp-setup.png)
4. Click **Save Configuration**.

### Configure your authorization policy

After setting up Entra ID as your SAML IdP, you must configure an authorization policy for your users and groups.

To configure an authorization policy:

1. Sign in to Endor Labs and select **Access Control** from the left sidebar.
2. Select **Auth Policy** and click **Add Auth Policy**.
3. Select **Entra ID SAML** from the **Identity Provider** list.
4. Choose the necessary permissions. See [authorization roles](../../../authorization-roles/) for more information.
5. Configure **Claims** as a key-value pair.
   * For individual users, provide `user` as **Key** and the user’s email as **Value**.
   * For groups, provide `groups` as **Key** and the group ID configured in Entra ID as **Value**.
6. Under **Advanced**, select a set of namespaces for which the authorization policy applies.

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
