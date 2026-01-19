---
url: https://docs.endorlabs.com/upgrades-and-remediation/using-endor-patches/configure-nexus-repository/
title: Configure Sonatype Nexus Repository to use Endor patches | Endor Labs Docs
downloaded: 2026-01-16 09:50:10
---

Configure Sonatype Nexus Repository to use Endor patches | Endor Labs Docs



* Type to search...

[Print entire section](/upgrades-and-remediation/using-endor-patches/configure-nexus-repository/_print.html)



# Configure Sonatype Nexus Repository to use Endor patches

Learn how to configure your Sonatype Nexus Repository setup to use Endor patches.

Configure Sonatype Nexus Repository Manager to ensure that the patched dependencies from Endor Labs are fetched and used correctly. The following procedures use Maven as the repository type, you can select the repository type based on your requirements.

## Create a remote repository for Endor Patching

Create a remote repository to fetch artifacts from the Endor Patch repository.

1. Log in to the Nexus Repository Manager.
2. Go to **Repositories** and click **Create repository**.
3. Select **maven2 (proxy)** as the recipe.
4. Enter the repository name, such as `endor-patch`.
5. In **Remote Storage**, enter the Endor Patch repository URL, typically given by Endor Labs, like `https://factory.endorlabs.com/v1/namespaces/<namespace>/maven2`.
   Replace `<namespace>` with your Endor Labs tenant name.
   ![Remote Storage](../../../images/RemoteStorageNexus.png)
6. Select **Authentication**, and enter your Endor Labs API Key ID as the **User Name** and your Endor Labs API Key secret as the **password**.
7. Click **Create repository** to save.

## Prioritize Endor patch repository in Maven group

If you have a Maven group repository that combines multiple repositories, you need to prioritize the Endor patch repository.

1. Log in to the Nexus Repository Manager.
2. Select **Browse** and navigate to your Maven group repository that combines multiple repositories.
3. Edit the group repository and move the `endor-patch` repository to the top of the order in the members list.
   This ensures that Endor Patch is checked first before any other repository for patch dependencies.
   ![Member Repositories Edit](../../../images/MemberRepoNexus.png)
4. Click **Save** to save the changes.

## Set up routing rules in other repositories

You can set up routing rules in repositories, other than the Endor patch repositories, to exclude Endor patch repositories. This will prevent other repositories from overriding the Endor patch dependencies.

1. Log in to the Nexus Repository Manager.
2. Select **Repository** in the **Administration** menu.
3. Select **Create Routing Rule**.
4. Enter a name such as `exclude-endor-patch`.
5. Select **Block** as the mode.
6. Enter the regular expression to block Endor patches in **Matchers**. For example, `com/endor/patch/.*`.
   ![Routing Rules for Nexus](../../../images/RoutingRulesNexus.png)
7. Click **Create Routing Rule** to save the rule.
8. Select **Browse** and navigate to the proxy repository that you want to edit.
9. Click Edit and select the routing rule that you created as the **Routing Rule**.
10. Click **Save**.

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
