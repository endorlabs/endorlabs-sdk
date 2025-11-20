---
url: https://docs.endorlabs.com/administration/access-endorlabs/authorization-policies/
title: Authorization policies | Endor Labs Docs
downloaded: 2025-11-20 11:49:46
---

Authorization policies | Endor Labs Docs



* Type to search...
* ---

[Print entire section](/administration/access-endorlabs/authorization-policies/_print.html)



# Authorization policies

Learn how to manage authorization policies in Endor Labs.

Authorization in Endor Labs is defined by a set of authorization policies. Authorization policies define the permissions provided to an identity authenticated by a supported identity provider when that identity meets specific rule criteria defined as attributes or claims about the identity.

Authorization policies must contain the following information:

* The [supported identity provider](../authentication-providers/) through which a given identity comes from.
* The [role](../../access-endorlabs/authorization-roles/) provided to an identity.
* An optional expiration time for the policy.
* The rule criteria or claims for which the identity must have to be authorized to access Endor Labs.

After setting up the authorization policy, you can [invite users to Endor Labs](../invitations/).

## Set up authorization policies

To set up an authorization policy to your Endor Labs tenant:

1. Sign in to Endor Labs and select **Access Control** from the left sidebar.
2. Select **Auth Policy** and click **Add Auth Policy**.
3. Select the identity provider for which you want to configure an authorization policy.
4. Select the role to be granted to a matching identity.
5. Select an expiration time for the authorization rule.
   * This may be either **No expiration**, **24 hours**, **72 hours**, **one week**, **two weeks**, or **30 days**.
6. Select the claims for which the authorization rule will provide access.
   * For **GitHub** and **GitLab** this may be the user’s platform handle.
   * For **Google**, this may be the user’s email address or the domain of the email address.
   * For a **custom identity provider**, this may be set to a key value pair associated with the claims provided by your external identity provider.
   * For **Email** this may be the email address an authentication link is sent to.
   * For **GitHub Action OIDC** this may be the organization or repository for which a workload runs under.
   * For **AWS Role** this may be the AWS ARN of the role the machine is set to impersonate.
   * For **Google Cloud** this may be the principal email of a service account the workload is set to impersonate.
   * For **Azure** these may be the user’s tenant ID, app ID, object ID and subscription ID.
7. Under **Advanced**, select a set of namespaces for which the authorization policy applies. If you choose to propagate this policy to all child namespaces, then the authorization policy will apply to any selected namespaces and their children.
8. Click **Add Auth Policy** to save your authorization policy.

After adding the authorization policy, a user with the corresponding authorization claims can sign in to Endor Labs with their configured permissions.

See [Invite users to Endor Labs](../invitations/).

## Search authorization policies

You can use the search functionality to find authorization policies based on specific criteria.

To search for authorization policies:

1. Navigate to **Manage** > **Access Control**.
2. Select **Auth Policy**.
3. Use the search bar to find policies by:
   * **Rule**: Search policies by any text or string patterns within the rule definitions.
   * **Created By**: Search policies by the email address of the creator.
   * **Namespaces**: Search policies associated with a specific namespace.

![Access Control interface](../../../images/auth-policy-search.png)

### Edit authorization policies

To edit an authorization policy:

1. Navigate to **Manage** > **Access Control**.
2. Select **Auth Policy**.
3. Click the vertical three dots on the right side of the policy you want to edit and click **Edit Auth Policy**.
4. You can update the identity provider, permission, expiration time, claims of key and value, and namespaces the policy applies to.
5. Click **Propagate this policy to all child namespaces** to apply this policy to all child namespaces within the hierarchy.
6. Click **Update Auth Policy**.

![Edit authorization policy](../../../images/edit-auth-policy.png)

### Delete authorization policies

To delete an authorization policy:

1. Navigate to **Manage** > **Access Control**.
2. Select **Auth Policy**.
3. Click the vertical three dots on the right side of the policy you want to delete and click **Delete Auth Policy**.
4. Click **Confirm** in **Delete Authorization Policy**.

### Grant support access

You can give the Endor Labs team read-only access to your namespaces for a limited time, allowing them to offer technical support and resolve issues.

You can revoke access and delete these policies at any time. See [delete authorization policy](#delete-authorization-policies) for more information.

To grant support access to your namespace:

1. Navigate to **Manage** > **Access Control**.
2. Select **Auth Policy** and click **Grant Support Access**.
3. Select an expiration time for the access from the drop down menu.
4. Click **Grant Access**.

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
