---
url: https://docs.endorlabs.com/administration/access-endorlabs/authentication-providers/custom-identity-providers/okta-saml/
title: Set up Okta for SSO using SAML | Endor Labs Docs
downloaded: 2025-10-23 23:25:16
---

Set up Okta for SSO using SAML | Endor Labs Docs



* Type to search...
* ---

[Print entire section](/administration/access-endorlabs/authentication-providers/custom-identity-providers/okta-saml/_print.html)



# Set up Okta for SSO using SAML

Learn how to setup Okta as a custom external identity provider for SSO with Endor Labs

Endor Labs integrates with Okta to use SSO through either Security Assertion Markup Language (SAML) protocol.

With the Endor Labs-Okta SAML integration, Endor Labs acts as the Service Provider (SP), and Okta acts as the Identity Provider (IdP).
When users sign in to Endor Labs using the SAML authentication method, the IdP (Okta) sends a SAML assertion to the browser that is passed to the SP (Endor Labs). This enables Okta to establish a secure connection with the browser and then authenticate the users to sign in to Endor Labs.

#### Tip

Endor Labs honors the session duration set in SAML, after which the user needs to reauthenticate. You can set the session duration in the `SessionNotOnOrAfter` attribute for SAML. If you do not set the attribute, the default session duration is four hours. Session duration cannot be more than four hours. If you set the `SessionNotOnOrAfter` attribute for more than four hours, the session duration defaults to four hours.

The following high level steps allow you to successfully configure Okta for SSO through SAML:

## Create and configure a SAML application in Okta

In Okta, configure the Endor Labs application as a SAML 2.0 application and generate a single sign-on URL and certificate.

#### Tip

You must be an Okta administrator to configure the application end-to-end in Okta.

1. Sign in to the Okta admin account.
2. Go to **Applications** > **Applications**.
3. To create an app integration, click **Create App Integration**.
4. Select **SAML 2.0** and click **Next**.
5. Enter the following details in **General Settings** and click **Next**.

   * **App Name**: Enter Endor Labs.
   * **App Logo (optional)**: Upload the Endor Labs logo in PNG, JPG, or GIF format. The logo size must be less than 1 MB.
   * **App Visibility (optional)**: Select this option to hide the Endor Labs icon from users in the Okta dashboard.
6. Enter the following in SAML Settings.

   * **Single sign-on URL**: Enter `https://api.endorlabs.com/v1/auth/saml-callback?tenant=yourtenant`. Replace `yourtenant` at the end with your actual tenant name.
   * **Audience URI**: Enter `https://api.endorlabs.com/v1/auth/sso`
   * **Relay State**: Leave this field empty
   * **Name ID format**: Select **Unspecified**.
   * **Application username**: Select **Email**.
   * **Update application username on**: Ensure **Create/Update** is selected.
7. Click **Show Advanced Settings** and ensure the following default details are set:

   * **Response**: Select **Signed**.
   * **Assertion Signature**: Select **Signed**.
   * **Signature Algorithm**: Select **RSA-SHA256**.
   * **Digest Algorithm**: Select **SHA256**.
   * **Assertion Encryption**: Select **Unencrypted**.
8. Configure your attribute statements: Attribute statements are specific properties associated with individual users and are used for including user provisioning, access control, or user profile management. To configure each individual user in Endor Labs you can use **Attribute Statements**. To configure users using Okta groups, such as groups integrated with Active Directory accounts use **Group Attribute Statements**.

   1. Enter the following details in **Attribute Statements** for individual authorization:
      * **Name**: Enter **email**.
      * **Name format**: Select **Basic**.
      * **Values**: Select **user.email**.
   2. Enter the following details in **Group Attribute Statements** for group authorization:
      * **Name**: Enter **groups**.
      * **Name format**: Select **Basic**.
      * **Filter**: As best practice, filter the groups being sent by choosing one of the following options.
        + Select **Matches regex** and enter a regular expression to specify groups.
        + Select **Starts With** to filter groups based on a prefix, sending only groups that begin with the specified string.
9. Click **Next**.
10. Select **I’m a Okta customer adding an internal app**, and click **Finish**.

### Assign the appropriate users and groups to the application

Once you’ve created your Application you need to assign the appropriate users and groups as assignments.

1. Select **Assignments** in your newly created application.
2. Click **Assign** and select **Assign to people** or **Assign to groups** if you are configuring group authorization.
3. Search for and select the group you’d like to assign and click **Done**.

### Get Identity Provider details from Okta

Once you’ve created your Okta app and assigned groups, then collect the identity provider SSO details to configure Okta in Endor Labs.

1. Select **Sign On**.
2. From **Metadata Details**, copy the **Metadata URL**.
3. Save the following details and have them handy if you’d like to manually configure SAML:
   * **Sign-On URL**: The SAML SSO URL of Okta.
   * **Issuer**: The unique ID of Okta for Endor Labs.
   * **Signing Certificate**: The public key certificate of Okta.

## Configure Okta SSO in Endor Labs

Provide the Identity Provider SSO details to configure Okta SSO in Endor Labs and allow users to seamlessly and securely sign in to Endor Labs.

#### Tip

You must be an Endor Labs administrator to configure custom identity providers and authorization policies.

1. Sign in to Endor Labs.
2. From the sidebar, navigate to Settings and click **CUSTOM IDENTITY PROVIDER**.
3. Select the **TYPE OF IDENTITY PROVIDER** as **SAML**.
4. Enter the **IDENTITY PROVIDER NAME** as **Okta SAML**.
5. From **METADATA DEFINITION**, select **Metadata URL** and enter the **Metadata URL** that you downloaded from Okta.
6. If you want to manually enter the identity provider details, choose **METADATA DEFINITION** as **Manual** and enter the following details, you saved from Okta. See [Get Identity Provider details from Okta](#get-identity-provider-details-from-okta)
   * **DISCOVERY URL**: Enter **Sign-On URL** from Okta.
   * **ISSUER**: Enter **Issuer** from Okta.
   * **ATTRIBUTES**: Enter your attributes such as email, groups, or more. Type the values and press enter.
   * **CERTIFICATE**: Enter the **Signing Certificate** from Okta.
7. Under **Attributes** enter **email** and **groups**, Press **enter** after each entry to add each attribute.
8. Click **Save Configuration**.

You must be an Endor Labs administrator to configure custom identity providers and authorization policies.

### Configure your Authorization Policy

Once you’ve configured your custom identity provider in Endor Labs you must configure an authorization policy for your users and groups.

To set up an authorization policy:

1. Sign in to Endor Labs.
2. Select **Access Control** > **Auth Policy** from the left sidebar.
3. Select **Add Auth Policy**.
4. Enter **Okta SAML** as your identity provider.
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
