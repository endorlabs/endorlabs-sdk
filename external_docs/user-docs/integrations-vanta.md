---
url: https://docs.endorlabs.com/integrations/vanta/
title: Set up Vanta integration with Endor Labs | Endor Labs Docs
downloaded: 2026-01-16 09:50:24
---

Set up Vanta integration with Endor Labs | Endor Labs Docs



* Type to search...

[Print entire section](/integrations/vanta/_print.html)



# Set up Vanta integration with Endor Labs

Learn how to integrate Vanta with Endor Labs and automate compliance requirements

Vanta enables organizations to manage risk by automating compliance and streamlining security reviews. Integrate Vanta with Endor Labs to view security findings in real-time and accelerate your security audit processes.

To integrate Endor Labs with Vanta:

* [Create an application in Vanta](#create-an-application-in-vanta)
  + [Create resources in Vanta](#create-resources-in-vanta)
* [Configure Vanta integration](#configure-vanta-integration)
  + [Associate an action policy with a Vanta notification](#associate-an-action-policy-with-a-vanta-notification)
  + [Manage Vanta notification targets in Endor Labs](#manage-vanta-notification-targets-in-endor-labs)
* [Run a scan](#run-a-scan)
  + [Findings exported to Vanta](#findings-exported-to-vanta)
* [View findings in Vanta](#view-findings-in-vanta)

## Create an application in Vanta

Create an application in Vanta so that Endor Labs can authenticate and export vulnerability findings to Vanta. The app requires `connectors.self:write-resource` and `connectors.self:read-resource scopes` to export vulnerabilities.

1. Sign in to Vanta as an Administrator.
2. Click **Settings** on the top navigation bar.
3. Select **Developer Console**.
   ![Vanta Developer Console](../../images/VantaDeveloperConsole.png)
4. Click **Create**.
5. Select **Build Integrations**.
6. Enter a name and description for your application.
7. Select the **App Visibility** as **Private** and click **Create**.
   ![Create Vanta Integration](../../images/createvantaapp.png)
8. Select the **Application Category** as **Vulnerability Scanner**.
9. Click **Generate Client Secret** to generate the OAuth client secret.
   OAuth Client ID appears. Copy the OAuth Client ID and the client secret and have them handy. You must enter this data in Endor Labs to configure the Vanta integration.
   ![Build Vanta Integration](../../images/createendorvanta.png)
10. Click **Save**.

### Create resources in Vanta

To successfully ingest security data and create notifications, map the Endor Labs attributes to resource types in Vanta.

1. Sign in to Vanta.
2. Navigate to **Settings** and click **Developer Console**.
3. Select your application and click **Resources**.
4. Click **Create Resource** and create the following resources to successfully map Endor Labs data into Vanta.

   * Enter the **Resource Type** as `Vulnerable Component` (mandatory) and select the **Base Resource Type** as **VulnerableComponent**.
     ![Create Resource](../../images/createresourcevanta.png)
   * Enter the **Resource Type** as `Package Vulnerability` (optional) and select the **Base Resource Type** as **PackageVulnerabilityConnectors**.
   * Enter the **Resource Type** as `Static Code Analysis` (optional) and select the **Base Resource Type** as **StaticAnalysisCodeVulnerabilityConnectors**.

   Provide the **Static Code Analysis** resource type if you want to export exposed secrets in your first party code to Vanta.

   You can view the schema generated for all the resource types.

Copy the **Resource ID** of the generated resources and have them handy. You must enter this data in Endor Labs to configure the Vanta integration.
![Vanta Resource IDs](../../images/endorvantaresources.png)

## Configure Vanta integration

Set up Endor Labs integration with Vanta.

Prerequisites:
Make sure you have the client ID, client secret, and the resource IDs from Vanta handy.

1. Sign in to Endor Labs and click **Integrations** from the sidebar.
2. Under **Notifications**, click **Add** for **Vanta**.
3. Click **Add Notification Integration**.
   ![Add Notification Integration](../../images/endortovanta.png)
4. Enter a name and description for this integration.
5. Enter the **CLIENT ID** and **CLIENT SECRET** that you generated on Vanta.
6. Under **Vanta Resources**, enter the Resource IDs for VULNERABILITY COMPONENT, PACKAGE VULNERABILITY, and STATIC CODE ANALYSIS VULNERABILITY from Vanta.

**Note**

**Vulnerable Component** is mandatory. You must enter either one of the **Package Vulnerability** or **Static Code Analysis Vulnerability** resource types.

7. Click **Add Notification Integration**.

### Associate an action policy with a Vanta notification

Users can create action policies to execute a recommended action when a policy is violated. For example, if there is a critical or high vulnerability, those vulnerabilities are exported to Vanta to ensure compliance adherence.

While creating an action policy, configure the following settings:

* Select **Choose an Action** as **Send Notification**.
* From **SELECT NOTIFICATION TARGETS**, choose the Vanta integration notification that you created.
* Choose an [**Aggregation type**](../../managing-policies/action-policies/#aggregation-types-for-notifications) for notifications. For integrating with Vanta, we recommend you choose **Project**.
* From **Assign Scope**, include the project tags in **INCLUSIONS** to apply this policy to a project.

See [Create an action policy](../../managing-policies/action-policies/) for more details.

### Manage Vanta notification targets in Endor Labs

You can view and manage the Endor Labs Vanta notification targets created for a project.

1. From the sidebar, navigate to **Manage** > **Integrations**.
2. Under **Notifications**, click **Manage** for **Vanta**. You can view all your created notification targets for Vanta.
3. To edit a notification target, click the vertical ellipsis and choose **Edit Notification Integration**.
4. To delete a notification target, click the vertical ellipsis dots and choose **Delete Notification Integration**.

## Run a scan

Run the endorctl scan on your configured projects. See [endorctl scan commands](../../endorctl/commands/scan/) for more information.

### Findings exported to Vanta

Endor Labs sends the following findings to Vanta:

* third-party open-source vulnerabilities
* secrets exposed in the first-party code

These findings are exported as **Package Vulnerabilities** and **Static Code Analysis Vulnerabilities** in Vanta. They are associated with a **Vulnerable Component** (that is the Repository Version) in Vanta.

Exporting findings generated on the Git repository security posture of an organization are not supported.

## View findings in Vanta

View Endor Labs’ findings in Vanta and take remedial actions.

1. Sign in to Vanta.
2. Select **Tests** to view notifications.
3. Select the integration that you created in the **Integration** filter to view notifications from Endor Labs.
   ![View Endor Labs Results in Vanta](../../images/viewendorresultsvanta.png)
4. Select a notification to view all findings associated with the Endor Labs policy.
   ![View notification in Vanta](../../images/view_results_in_vanta.png)
5. Click on a finding to view more details in Endor Labs.

For example, if you create an action policy to notify critical vulnerabilities and configure it to a Vanta notification target, you can see the exports as **Critical vulnerabilities identified in code repositories are addressed** under **Tests** in Vanta. The test classifications are based on the severity of the exported findings.

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
