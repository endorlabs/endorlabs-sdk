---
url: https://docs.endorlabs.com/ai/ai-llm/
title: AI model findings | Endor Labs Docs
downloaded: 2026-01-26 10:06:29
---

AI model findings | Endor Labs Docs



* Type to search...

[Print entire section](/ai/ai-llm/_print.html)



# AI model findings

Find and manage priority issues related to AI models.

Endor Labs can detect AI models and list them as dependencies when you run a scan with the `--ai-models` flag. You can view the detected AI models in the **AI Inventory** section of the [Endor Labs user interface](#view-ai-models-in-your-namespace).

You can define custom policies to flag the usage of specific AI providers, specific AI models, or models with low-quality scores so that their usage raises findings as part of your scan. Endor Labs provides [AI model policy templates](../ai-model-policies/) that you can use to create finding policies that are tailored to your organization’s needs. You can [view these findings](#view-ai-model-findings-in-your-namespace) in **Code Dependencies** > **AI Models** on the **Findings** page.

Run the following command to detect AI models in your repository.

```
endorctl scan --ai-models
```

When you run a scan with the `--ai-models` option, Endor Labs downloads Opengrep and runs Opengrep to detect AI models.

Endor Labs detects AI models using pattern matching and can use LLM processing to improve detection accuracy. LLM processing is disabled by default.

See [Supported AI model providers](#ai-model-detection) for the list of external AI models detected by Endor Labs. Only Hugging Face models are scored, as they are open source and provide extensive public metadata. Models from all other providers are detected but not scored due to limited metadata.

## Enable LLM processing for AI model detection

To enable LLM processing in Endor Labs:

1. Select **Manage** > **Settings** from the left sidebar.
2. Select **System settings** > **Data privacy**.
3. Turn on **Code Segment Embeddings and LLM Processing**.

See [Configure system settings](../../administration/configure-system-settings/) for more information.

**Privacy**

When you enable LLM processing, Endor Labs uses a private and isolated Azure OpenAI Service deployment, which is not accessible from the public Internet and cannot be used for LLM training.

To generate AI model findings:

1. Configure [finding policy](../ai-model-policies/) to detect AI models with low scores and enforce organizational restrictions on specific AI models or model providers.
2. [View AI Model findings](#ai-model-detection).
3. To disable AI model discovery, set `ENDOR_SCAN_AI_MODELS=false` in your [scan profile.](../../scan-with-endorlabs/manage-scan-profiles/configure-scanprofile-ui/#configure-general-scan-profile-settings)

## AI model detection

The following table lists the AI model providers currently supported by Endor Labs for model detection. For each provider, the table includes supported programming languages, if model scoring is available, and a reference link to the provider’s API documentation.

| AI model | Supported languages | Endor score | Reference |
| --- | --- | --- | --- |
| HuggingFace | Python | ✓ | <https://huggingface.co/docs> |
| OpenAI | Python, JavaScript, Java (beta), Go (beta), C# | ✗ | <https://platform.openai.com/docs/libraries> |
| Anthropic | Python, TypeScript, JavaScript, Java (alpha), Go (alpha) | ✗ | <https://docs.anthropic.com/en/api/client-sdks> |
| Google | Python, JavaScript, TypeScript, Go | ✗ | <https://ai.google.dev/gemini-api/docs/sdks> |
| AWS | Python, JavaScript, Java, Go, C#, PHP, Ruby | ✗ | <https://docs.aws.amazon.com/bedrock/latest/APIReference/welcome.html#sdk> |
| Perplexity | Python | ✗ | <https://docs.perplexity.ai/api-reference/chat-completions-post> |
| DeepSeek | Python, JavaScript, Go, PHP, Ruby | ✗ | <https://api-docs.deepseek.com/api/deepseek-api> |
| Azure OpenAI | C#, Go, Java, Python | ✗ | <https://learn.microsoft.com/en-us/azure/ai-foundry/> |

## AI model discovery through monitoring scans

By default, AI models are discovered during SCA scans run through GitHub App, Bitbucket App, Azure DevOps App, and GitLab App. You can view the reported AI models under **AI Inventory** in the left sidebar.

To disable AI model discovery, set `ENDOR_SCAN_AI_MODELS=false` as an additional environment variable in the [scan profile](../../scan-with-endorlabs/manage-scan-profiles/configure-scanprofile-ui/#configure-general-scan-profile-settings) and assign the scan profile to the project.

## Detect AI models

Configure finding policies and perform an endorctl scan to detect AI models in your repositories and review the findings.

1. Configure [finding policy](../ai-model-policies/) to detect AI models with low scores and enforce organizational restrictions on specific AI models or model providers.
2. Run an endorctl scan with the following command.

   ```
   endorctl scan --ai-models --dependencies
   ```

## View AI models in your namespace

To view all AI models that are used in your namespace:

1. Select **AI Inventory** on the left sidebar.
   ![AI Models](../../images/ai-inventory.png)
2. Use the search bar to look for any specific models.
3. Select a model, and click to see its details.
4. You can also navigate to **Findings** and choose **AI Models** to view findings.
   ![AI model findings](../../images/aimodel-global-finding.png)

## View AI models in a project

To view AI models that are used in a specific project:

1. Select **Projects** from the left sidebar and select a project.
2. Select **Inventory** and click **AI Models** under **Dependencies** to view findings.
   ![AI model dependencies](../../images/aimodel-dependencies.png)

## View AI model findings in your namespace

To view all AI model findings in your namespace:

1. Select **Findings** from the left sidebar.
2. Select **AI Models** from the **Findings** page.
   ![AI model findings](../../images/aimodel-global-finding.png)

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
