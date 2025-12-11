---
url: https://docs.endorlabs.com/introduction/
title: Introduction to Endor Labs | Endor Labs Docs
downloaded: 2025-12-11 11:30:55
---

Introduction to Endor Labs | Endor Labs Docs



* Type to search...
* ---

[Print entire section](/introduction/_print.html)



# Introduction to Endor Labs

Secure your software supply chain with Endor Labs

Endor Labs helps security and DevOps teams build secure applications without the productivity tax associated with traditional security and compliance obligations.

Endor Labs addresses three primary software supply chain security use cases:

* Secure open-source code
* Secure repositories and pipelines
* Meet AppSec compliance requirements

## Secure Open Source Code

Secure and manage the open source software (OSS) packages that are used in your application code:

* **Vulnerability prioritization:** Reachability-based SCA uses program analysis to understand code behavior at build time, identifying reachable vulnerabilities at the function level to help you prioritize risk in the context of your code.
* **Full visibility of OSS risks:** Scan direct and transitive dependencies, including phantom dependencies, and cross-reference with a proprietary database that includes function-specific annotations on CVEs dating back to 2018.
* **Select healthy OSS dependencies:** Prevent risky OSS from entering your ecosystem with Endor Score and DroidGPT, allowing you to implement governance of OSS selection and improve developer productivity.

## Secure repositories and pipelines

Track potential process deviations and failures in your pipelines:

* **SCM config management:** Gain visibility into the configuration of source code management systems and understand the delivery process through secure configuration baselines and out-of-the-box policies.
* **Detect and prioritize secret leaks:** Identify potential secret leaks in your source code and implement policies that block secrets from being hard coded.

## Meet AppSec compliance requirements

Demonstrate compliance with stakeholder and industry requirements:

* **License compliance risk management:** Manage legal and compliance risks related to OSS licensing as part of an open source software governance program, including an Open Source Program Office (OSPO).
* **SBOM and VEX:** Automatically generate SBOMs for each software package and annotate with Vulnerability Exploitability eXchange (VEX) documents so that your stakeholders can get visibility into your software inventory and assess the status of vulnerabilities.

## Integrate Endor Labs into SDLC workflows

Endor Labs integrates into various stages of the software delivery lifecycle, including:

1. A developer’s Integrated Developer Environment (IDE) or their local workstation.
2. Continuous integration jobs before software installation or build processes.
3. Continuous integration jobs after software installation or build processes.
4. Day-to-day ticketing and messaging workflows.

The diagram below illustrates how a DevSecOps program can integrate Endor Labs into their software delivery workflows:

![Using Endor Labs](../images/endorlabs_workflow.png)

* Endor Labs IDE plugins help development teams select better dependencies and catch potential issues early in the software development process.
* Endor Labs secret scanning is performed as a test before building software, allowing teams to quickly identify potential secret leaks in their source code.
* Endor Labs software composition analysis and reachability analysis occur as post-build/install steps in the CI pipeline. This post-build/install scanning provides a more accurate bill of materials and helps prioritize issues.
* Endor Labs scans for the configuration of your source code management system as a regular scan on your repositories. This configuration generally changes infrequently and defines how your development team delivers and tests your software.
* Endor Labs helps establish ticketing and messaging workflows through policies to notify your team of urgent issues or policy violations for appropriate resolution.

---

##### [Call graphs](/introduction/call-graphs/)

Mitigate open source vulnerabilities with call graph visualizations, pinpointing and understanding the invocation of vulnerable methods for actionable developer insights.

##### [Reachability analysis](/introduction/reachability-analysis/)

Learn how Endor Labs helps you identify which vulnerabilities are exploitable, potentially exploitable, and false positives.

##### [Endor scores](/introduction/scores/)

Understand how packages and AI Models are scored in Endor Labs.

##### [Malware detection](/introduction/malware-detection/)

Understand how malware is detected, classified, and scored in Endor Labs.

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
