---
url: https://docs.endorlabs.com/best-practices/github-security-campaign/
title: Best Practices: GitHub Security Campaign | Endor Labs Docs
downloaded: 2025-12-11 11:34:10
---

Best Practices: GitHub Security Campaign | Endor Labs Docs



* Type to search...
* ---

[Print entire section](/best-practices/github-security-campaign/_print.html)



# Best Practices: GitHub Security Campaign

Learn how to plan, execute, and monitor GitHub security campaigns using Endor Labs and GitHub Advanced Security.

A GitHub Security Campaign is an organized, time-bound initiative designed to identify, remediate, and prevent vulnerabilities across multiple repositories. By leveraging Endor Labs dependency intelligence and GitHub Advanced Security (GHAS), these campaigns transform vulnerability findings into coordinated remediation efforts that keep developers working inside GitHub. This approach is particularly effective when multiple projects share vulnerable dependencies or when organizations must meet compliance-driven remediation deadlines.

Endor Labs generates vulnerability findings in SARIF format, which are uploaded directly into GitHub Advanced Security. Once uploaded, these findings become actionable alerts enabling developers to triage, fix, and track vulnerabilities without leaving their familiar environment.

The security campaign allows organizations to:

* Target a specific class of vulnerabilities, for example `Log4j`, or `CVE-2024-xyz`.
* Drive dependency upgrades and security fixes across all affected repositories.
* Address secrets detection and SAST findings alongside for comprehensive security remediation.
* Enforce consistent remediation timelines and accountability across teams.
* Monitor reduction in overall security debt using both GitHub’s campaign dashboard and Endor Labs analytics.

Ensure you have deployed [Endor Labs](../../deployment) and enabled [GitHub Advanced Security](https://docs.github.com/en/get-started/learning-about-github/about-github-advanced-security) before creating a security campaign.

## Create and manage a security campaign

Use GitHub Security Campaigns to coordinate and manage large-scale vulnerability remediation efforts by importing findings from Endor Labs.

1. Run a scan with Endor Labs to generate vulnerability findings in SARIF format and upload them to GitHub Advanced Security. See [SARIF output format](../../scan-with-endorlabs/scanning-strategies/#understand-sarif-files) for detailed information on generating, customizing, and uploading SARIF files.

**Automatic SARIF upload**

Configure Endor Labs GitHub App (Pro) with a GHAS SARIF exporter to automatically upload findings to GitHub after each scan. See [Export findings to GitHub Advanced Security](../../deployment/monitoring-scans/github-app/github-app-pro/export-findings-to-ghas/) for setup instructions.

2. In GitHub, navigate to **Security > Campaigns > New Campaign** to define your campaign parameters. Refer to [security campaign guide](https://docs.github.com/en/enterprise-cloud@latest/code-security/securing-your-organization/fixing-security-alerts-at-scale/creating-managing-security-campaigns) for more information on GitHub’s campaign features and configuration options.
3. Define the scope of your campaign.

   * **Organization-wide**: Apply the campaign across all repositories in your organization.
   * **Selected repositories**: Target specific repositories affected by the vulnerability class.
   * **Teams or projects**: Scope by team ownership or project grouping.
4. Specify a clear focus area of the campaign that aligns with your security requirements. For example, remediating Log4j vulnerabilities across Java projects, or upgrading vulnerable npm packages to secure versions.
5. Define campaign objectives with clear remediation timelines. For example, close 80% of critical dependency vulnerabilities within 30 days, or fully remediate exposed secrets within 10 days.
6. Monitor campaign metrics in GitHub, including percentage of vulnerabilities remediated, active versus resolved alerts, and repository-level completion.

## Best practices

Security campaigns are a strategic way to remediate security alerts at scale while improving developer knowledge of secure coding practices. Below are the best practices to ensure successful campaign execution.

### Plan and prioritize alerts strategically

Select a related group of security alerts for remediation rather than attempting to fix all alerts at once. For organizations building secure coding knowledge, prioritize alerts that can serve as learning opportunities.

Use Endor Labs’ reachability analysis and severity scoring to identify high-impact vulnerabilities.

* Focus on **reachable** vulnerabilities where the vulnerable code is actually used in execution paths.
* Filter by **exploitability score**, **CVE severity**, or **policy violation type**.
* Use **Endor Labs Dependency Graph** to visualize transitive relationships and focus on the most impactful fixes.

**Tip**

You can tag repositories with metadata such as `critical`, `frontend`, or `backend` in Endor Labs and scope your campaign accordingly. Exclude inactive or archived repositories to focus efforts where they matter most.

### Provide educational resources

Include links to relevant educational materials in the campaign description to help developers understand and remediate vulnerabilities effectively, such as OWASP references, secure secrets management guides, or internal upgrade instructions.

### Enable AI assistance for faster remediation

Leverage AI-powered tools to accelerate remediation while maintaining code quality:

* Use **GitHub Copilot Autofix** to suggest fixes for code scanning alerts automatically, reducing manual effort.
* Make **GitHub Copilot Chat** available for developers to ask questions about vulnerabilities, testing, and secure coding best practices.
* Enable **Endor Labs automated remediation PRs** to create pull requests with updated dependency versions, vulnerability references (CVE IDs, severity, reachability), and compatibility checks.

### Assign and support campaign managers

Campaign managers play a critical role in maintaining momentum and ensuring developers have the support they need to succeed. Campaign managers should:

* Review PRs, provide guidance, and maintain consistent communication.
* Provide a contact link for questions and collaboration.
* Monitor progress and provide support where needed to ensure sustained engagement.
* Help resolve complex or unclear fixes through open communication with developers.

### Define realistic deadlines

Set timelines according to issue complexity and remediation scope. Simple dependency upgrades require minimal validation, whereas compatibility or architectural fixes need extended testing and integration checks. Align campaigns with sprint cycles or release milestones. Iterative, narrowly scoped campaigns improve predictability, code stability, and remediation quality.

### Track progress and engagement

Continuously monitor campaign performance using GitHub dashboards for remediation percentage, active versus resolved alerts, repository-level progress, and time-to-fix metrics, and use GitHub Issues for task tracking and communication within developer workflows.

**Tip**

Use GitHub labels such as `security-campaign-q4` or `log4j-remediation` on issues and pull requests to enable easy filtering and audit tracking across repositories.

### Log4j vulnerability remediation example

**Scenario:** A critical Log4j vulnerability affects multiple Java microservices across the organization.

**Campaign execution:**

1. Export a SARIF file containing all dependency vulnerabilities from Endor Labs.
2. Upload the SARIF file to GitHub to populate alerts across affected repositories.
3. Create a security campaign titled “Fix outdated Log4j dependencies across all repos”.
4. Assign the campaign to the Java development team with a 30-day remediation deadline.
5. Developers fix vulnerabilities directly in GitHub by updating affected dependencies.
6. The security team monitors campaign progress in GitHub until 85% of alerts are resolved, then closes the campaign.

**Outcome:** The organization remediates 85% of Log4j-related vulnerabilities within 30 days, improving dependency security posture and reducing exposure to known CVEs.

## FAQs

Can security campaigns include private repositories?

Yes. Security campaigns work with both public and private repositories. Ensure GitHub Advanced Security is enabled for private repositories and that the Endor Labs GitHub App has appropriate permissions.




How are alerts selected for a campaign?

Alerts are selected using GitHub’s campaign filters and Endor Labs’ vulnerability data. Use Endor Labs’ reachability analysis to prioritize alerts where vulnerable code is actively used in execution paths.




What is the maximum number of active campaigns allowed?

GitHub permits a maximum of 10 active campaigns, each with up to 1,000 alerts. You can prioritise active repositories, target specific vulnerability types, close completed campaigns swiftly, and run campaigns sequentially or split them into focused initiatives




Can multiple campaign types run simultaneously?

Yes. You can run multiple campaign types simultaneously, such as dependency remediation, secrets rotation, and license compliance. Each campaign can target different repositories, teams, or vulnerability classes.




What integrations are available for campaign management?

GitHub Security Campaigns integrate with GitHub Issues, GitHub Actions, Slack, Jira, and Endor Labs. You can export Campaign data to business intelligence tools and internal reporting dashboards

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
