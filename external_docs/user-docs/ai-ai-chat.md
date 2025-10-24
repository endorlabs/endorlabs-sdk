---
url: https://docs.endorlabs.com/ai/ai-chat/
title: Endor AI Chat | Endor Labs Docs
downloaded: 2025-10-23 23:24:50
---

Endor AI Chat | Endor Labs Docs



* Type to search...
* ---

[Print entire section](/ai/ai-chat/_print.html)



# Endor AI Chat

Use the Endor AI Chat to understand vulnerabilities and view recommended actions. It leverages AI to provide contextual explanations, guidance, and next steps for issues detected in your project. With AI-powered context, you can reduce time spent digging through raw data and accelerate triage and remediation.

You can use Endor Ask AI chat from multiple places across the Endor Labs application.

## Prerequisites

To start using Endor Ask AI chat, you must enable **Code Segment Embeddings and LLM Processing** in **Data Privacy** settings.

1. Select **Manage** > **Settings** from the left sidebar.
2. Select **SYSTEM SETTINGS** > **Data Privacy**.

   ![Enable Code Segment Embeddings and LLM Processing](/images/enable_embeddings.png)
3. Select **Code Segment Embeddings and LLM Processing**.
4. Click **Save Data Privacy Settings**.

## Investigate vulnerabilities

Use the AI chat to simplify technical details and generate summaries.

1. From the left sidebar, select **Projects**, then search for and choose a project.
2. Select a finding and click **Ask AI** to get more details.
3. Ask questions like,
   * Summarize this finding.
   * Is this vulnerability exploitable?
   * How do I remediate this?
   * Is this a true positive finding, for example, Is this a true positive SAST finding?

![vulnerabilities](../../images/ai-chat/ai-chat-vulnerability.png)

## Summarize scan results

From the scan history, you can analyze scans performed by endorctl over time.

1. From the left sidebar, select **Projects**, then search for and choose a project.
2. Select **SCAN HISTORY** to review the past scans.
3. Select an entry and click **Actions** > **Add to AI Chat**.
4. Ask questions like,
   * Summarize this scan.
   * Which issues were introduced or resolved?

![scan history](../../images/ai-chat/ai-chat-scanhistory.png)

## Understand vulnerabilities

ASK AI simplifies searching the Vulnerability Database by allowing users to ask natural-language questions. It provides guidance and explanations, helping users quickly interpret risk and remediation options.

1. From the left sidebar, select **Vulnerabilities**.
2. Search for a vulnerability and select a search result.
3. Click **Ask AI** to get data about the vulnerability.
4. Ask questions like,
   * How does this affect Tomcat servers?
   * Why is this considered high severity?

![vulnerability database](../../images/ai-chat/ai-chat-vulnerability-db.png)

## Understand packages

To assist with troubleshooting during scans, Endor Ask AI Chat provides quick explanations for package resolution and reachability errors within a project. It helps users understand what happens to a package during scanning by analyzing the provided error message and returning relevant context.

1. From the left sidebar, select **Projects**.
2. From **Inventory**, and select a specific package.
3. Click into the drawer and click **Ask AI**.
4. Ask questions like
   * Summarize this package
   * Explain errors and how to solve them.

![packages](../../images/ai-chat/ai-chat-packages.png)

## Data scope for AI responses

Endor Ask AI chat agents generate answers based solely on specific data available within the Endor Labs platform. They have access only to the following data objects:

* Findings
* Scan results
* Vulnerabilities
* Package versions

Agents are designed to provide insights, explanations, and recommendations from the content of these objects. If the requested information falls outside this scope, such as external environment data, undocumented configurations, or unrelated context, the AI may not be able to generate a response.

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
