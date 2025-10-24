---
url: https://docs.endorlabs.com/managing-policies/
title: Policies | Endor Labs Docs
downloaded: 2025-10-23 23:27:23
---

Policies | Endor Labs Docs



* Type to search...
* ---

# Policies

Policies are rules that allow you to customize the behavior of the Endor Labs scan.

You can use policies to:

* Enable, disable, or edit out-of-the-box features
* Create custom findings
* Set guardrails for the development process
* Create custom ticketing or messaging workflows

Endor Labs comes with various out-of-the-box policies that enable you to quickly get started with the product. Policy templates are available to help you easily create custom findings and configure workflows around known vulnerabilities, outdated, unmaintained, or unused software dependencies, license risks, code review guidelines, repository configurations, and more.

See also [configure policy settings](../administration/configure-system-settings/#configure-policy-settings).

You can also write policies from scratch using [Rego policy language](https://www.openpolicyagent.org/docs/latest/policy-language/) and customize policies based on organizational rules and needs.

You can tag projects to apply policies to specific projects. See [Tagging projects](./tagging-projects/) for more information.

## Key benefits of policies

Policies are essential to define risk tolerance, set automated rules for open source components, check your repository or organization configuration, and more.

* **Identify and triage issues** - Policies give you a quick and automated way to identify and triage issues in your environment. This saves valuable development time and ensures developers consider security issues at the early stages of application development.
* **Improve decision-making** - Automating enforcement simplifies decision-making in an organization and reduces complexity. Policies make assessing the OSS components simpler and allow developers to focus on violations critical to the organization.
* **Establish governance** - Use policies to set up an organization’s governance methods such as enforcing Multi-Factor Authentication, setting up code review guidelines, guidelines on the use of the open source components, preventing misconfiguration of source code repositories, and more.

## Policy types

You can set up the following types of policies in Endor Labs.

* [**Finding policies**](./finding-policies/) - Enable or disable out-of-the-box features and create custom finding policies to identify and raise findings for issues in your development environment. For example, you can create a finding policy to raise findings for missing, unknown, problematic, or incompatible licenses.
* [**Exception policies**](./exception-policies/) - Identify findings that should be exempt from action policies. For example, you can create an exception policy to automatically dismiss all findings found in the `serverless-dns` package.
* [**Action policies**](./action-policies/) - Define the system behavior and set up workflows when a finding with a given set of properties is raised. For example, you can create an action policy to create a Jira task when packages with outdated dependencies are included in your projects.
* [**Remediation policies**](./remediation-policies/) - Define the conditions to remediate findings when an upgrade is available. For example, you can apply remediation when a low risk upgrade is available.
