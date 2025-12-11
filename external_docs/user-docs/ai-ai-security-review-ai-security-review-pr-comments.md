---
url: https://docs.endorlabs.com/ai/ai-security-review/ai-security-review-pr-comments/
title: PR Comments for AI security code review | Endor Labs Docs
downloaded: 2025-12-11 11:34:30
---

PR Comments for AI security code review | Endor Labs Docs



* Type to search...
* ---

[Print entire section](/ai/ai-security-review/ai-security-review-pr-comments/_print.html)



# PR Comments for AI security code review

Learn how AI security code review PR comments work and how to interpret them as a developer

Beta

AI security code review PR comments provide automated feedback directly in your GitHub pull requests when potential security issues are detected in your code changes. This feature helps developers identify and fix security vulnerabilities before code is merged into the main branch.

When you create or update a pull request, Endor Labs automatically scans the diff of the pull request. The scan data is sent to a private and secure AI model for security analysis. A comment is automatically posted to your PR with the analysis. You can review the findings and make necessary changes.

If no security issues are detected, you can see a comment indicating a clean security review.

## Benefits of AI security code review PR comments

You can get the following benefits with AI security code review PR comments:

* Get security feedback without leaving your development workflow
* Identify issues before code review or merge
* Reduce the time between writing code and discovering security problems
* Receive specific recommendations for fixing security issues
* Understand the security implications of your code changes
* Learn about security best practices through real examples

## Content of AI security code review PR comment

After the analysis is complete, Endor Labs posts a comment directly on your pull request with the following information:

* **Summary**: A summary of the code changes in the pull request along with the file name and location of the code changes.
* **Security Changes**: A list of security changes in the pull request along with the file names and location of the security changes.

The following example shows how an AI security code review PR comment appears in a GitHub pull request.

![Example of AI security review](../../../images/ai-security-review-example.png)

### Summary of code changes

The AI security review provides a comprehensive summary of all code changes in your pull request.

The summary includes the following information:

* **Detailed change analysis**: What was modified, added, or removed in each file.
* **File paths and line numbers**: Exact locations of all changes.
* **Technical implementation details**: Specific functions, configurations, and changes made in the code.
* **Impact assessment**: Analysis of how changes affect the overall system.

The following example shows a summary of code changes for a pull request.

![AI security code review PR comment summary](../../../images/ai-security-review-pr-comment-summary.png)

### Security Changes

The AI security review analyzes your code changes across different security aspects and provides detailed findings for any security-relevant changes.

The following sections describe the security changes in more detail.

* [Comment structure of security changes](#comment-structure-of-security-changes)
* [Severity levels](#severity-levels)
* [Category icons for security changes](#category-icons-for-security-changes)

The following example shows a security changes for a pull request.

![AI security code review PR comment security changes](../../../images/ai-security-review-pr-comment-security-changes.png)

#### Comment structure of security changes

The comment structure is as follows:

* **Security Changes Header**: Numbered count of security changes found.
* **Security Aspect Icons**: Visual indicators and category icons for quick identification.
* **Severity Level**: Critical, High, Medium, or Low classification.
* **Detailed Description**: Comprehensive explanation of the security concern.
* **Code References**: Specific file paths and line numbers with clickable links.
* **Justification Section**: Detailed explanation of why the change poses a security risk.

#### Severity levels

The following severity levels are used to classify the security changes:

* **🔴 Critical**: Immediate security threats (prompt injection vulnerabilities, authentication bypasses).
* **🟠 High**: Significant security risks (API endpoint issues, access control problems).
* **🟡 Medium**: Security concerns to address (PII data handling, dependency security, JWT implementation).
* **🟢 Low**: Minor security issues or best practice violations.

#### Category icons for security changes

The following category icons are used to classify the security changes:

* **📦 Dependency**: Dependency security, library vulnerabilities.
* **🤖 AI**: AI model security, prompt injection risks.
* **🔒 Access Control**: Authentication, authorization, session management.
* **🔌 API Endpoint**: API security controls, rate limiting.
* **🗄️ Database**: Query construction, data access controls.
* **🔐 Cryptographic**: Encryption, hashing, key management, JWT implementation.
* **💳 Payment Processing**: Financial data security, PCI compliance.
* **🧠 Memory Protection**: Buffer overflows, memory leaks.
* **👤 PII Data Handling**: PII handling, data classification, local storage security.
* **📝 Input Validation**: Data sanitization, injection prevention.
* **🏗️ Infrastructure**: Cloud resources, container security.
* **🚀 CI/CD**: Build pipeline security, artifact integrity.
* **⚙️ Configuration**: Secrets management, environment variables.
* **🌐 Network**: Firewall rules, network segmentation.

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
