---
url: https://docs.endorlabs.com/upgrades-and-remediation/using-endor-patches/configure-jfrog-artifactory/
title: Configure JFrog Artifactory to use Endor patches | Endor Labs Docs
downloaded: 2025-12-11 11:33:46
---

Configure JFrog Artifactory to use Endor patches | Endor Labs Docs



* Type to search...
* ---

[Print entire section](/upgrades-and-remediation/using-endor-patches/configure-jfrog-artifactory/_print.html)



# Configure JFrog Artifactory to use Endor patches

Learn how to configure your JFrog Artifactory setup to use Endor patches.

Configure JFrog Artifactory to ensure that the patched dependencies from Endor Labs are fetched and used correctly. The following procedures use Maven as the repository type, you can select the repository type based on your requirements.

## Create a remote repository for Endor Patching

Create a remote repository to fetch artifacts from the Endor Patch repository.

1. Log in to the JFrog Platform as an administrator.
2. In the **Administration** module, select **Repositories**.
3. Select **Create a Repository** and click **Remote**.
4. Select **Maven** from the list of repository types.
5. In **Repository Key**, enter a name such as `endor-patch`.
6. Create an API Key in Endor Labs to authenticate to the Endor Patch repository with “Read-Only” permissions. See [creating an API key](../../../administration/api-keys/) for more detail. Keep these details handy.
7. In **URL**, enter the Endor Patch repository URL, `https://factory.endorlabs.com/v1/namespaces/$NAMESPACE/maven2`.
   Replace `$NAMESPACE` with your Endor Labs tenant name.
8. Enter your Endor Labs API Key ID as the **User Name** and your Endor Labs API Key secret as the **password** for your new remote repository.
9. Click **Test** to ensure you are able to successfully connect to the remote repository.
   ![Artifactory Remote Repository](../../../images/remoterepoartifactory.png)
10. Click **Advanced** and select **Priority Resolution** to ensure that the Endor patch repository is prioritized over other remote repositories.
    ![Artifactory Remote Repository Advanced](../../../images/remoterepoartifactoryadvanced.png)
11. Click **Create Remote Repository**.

## Create a virtual repository for Endor Patching

Create a virtual repository to simply access to Endor patch repositories and other remote repositories.

1. Log in to the JFrog Platform.
2. In the **Administration** module, select **Repositories**.
3. Select **Create a Repository** and click **Virtual**.
4. Select **Maven** from the list of repository types.
5. In **Repository Key**, enter a name such as `endor-patch`.
6. Add the `endor-patch` remote repository to this virtual repository along with other required remote repositories.
7. Ensure `endor-patch` repository is at the top of the list to prioritize it if you are using auto patching. See [the auto patching documentation for more details](../auto-patching/)
   ![Artifactory Virtual Repository](../../../images/virtualrepositoryartifactory.png)
8. Click **Create Virtual Repository**.

## Edit an existing virtual repository

Edit an existing virtual repository to access the Endor Patch repositories and other remote repositories.

1. Log in to the JFrog Platform.
2. In the **Administration** module, select **Repositories**.
3. Select the **Virtual** tab and click into the existing virtual repository you’d like to edit.
4. Under **Repositories** move the `endor-patch` remote repository to the selected repositories.
5. Ensure `endor-patch` repository is at the top of the list of selected repositories to prioritize it if you are using auto patching. See [the auto patching documentation](../auto-patching/) for more information.
6. Click **Save**.

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
