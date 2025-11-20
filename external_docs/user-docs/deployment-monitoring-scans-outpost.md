---
url: https://docs.endorlabs.com/deployment/monitoring-scans/outpost/
title: Outpost: The on-prem scheduler for monitoring scans | Endor Labs Docs
downloaded: 2025-11-20 11:51:02
---

Outpost: The on-prem scheduler for monitoring scans | Endor Labs Docs



* Type to search...
* ---

[Print entire section](/deployment/monitoring-scans/outpost/_print.html)



# Outpost: The on-prem scheduler for monitoring scans

Learn how to deploy Outpost, the on-prem scheduler for monitoring scans.

Beta

Endor Labs monitoring scan regularly scans your source code to discover vulnerabilities. The Endor Labs Apps clone and analyze all repositories every 24 hours, ensuring continuous monitoring for open source vulnerabilities and code weaknesses. See [Monitoring scans](/en/deployment/monitoring-scans/) for more information.

Endor Labs uses a Kubernetes cluster where your source code repositories and cloned, and the scans are conducted. Your policies may require that the source code repositories are not exposed to the public cloud. In such situations, you can use Outpost, which is a deployable on-prem instance of the Endor Labs scheduler that runs on your private Kubernetes cluster. After you deploy Outpost, Endor Labs uses your Kubernetes cluster to run the monitoring scans.

The scheduling of the scans and the scans themselves are run within your firewall. After the scans are completed, only the scan results are sent to Endor Labs.

Outpost provides full feature parity with regular cloud-based Endor Labs scans.

The following diagram shows how monitoring scans work when you configure Outpost.

```
graph TD
    A(["Endor Labs App"]) -->|<span style='font-size: 12px'>Continuous monitoring</span>| B["Source Code Repositories"]
    B <--> F["Private Artifact Registry"]
    A -->|<span style='font-size: 12px'>Initiates scans</span>| C["Private Kubernetes cluster
    <span style='font-size: 12px'>Runs Outpost and the scans inside your firewall</span>"]
    B -->|<span style='font-size: 12px'>Clones repositories</span>| C
    C -->|<span style='font-size: 12px'>Pass scan data</span>| D(["Endor Labs Platform
    <span style='font-size: 12px'>Generate findings from scan results</span>"])

    subgraph E["Firewall"]
    A
    B
    C
    F
    end

    class A,D endor
    class B,C,F customer
    class E firewall
    classDef customer fill:#3FE1F3
    classDef endor fill:#5BF385
    classDef firewall fill:transparent,stroke-dasharray: 5 5,stroke:#FF4500,color:#FF4500
```

Outpost helps you in the following instances:

* Security and compliance requirements prevent you from exposing source code repositories to external services
* Firewall restrictions that prevent direct integration with external scan services and requires complex VPN configurations
* Integrating endorctl into multiple CI/CD pipelines can be complex and costly, and relying on manual scanning processes increases the risk of errors
* Need to scan against private artifact registries and internal services

You need to configure Outpost as an integration at your Endor Labs tenant namespace. You can only configure Outpost as an integration at your root namespace. After you configure the integration and complete the Kubernetes cluster configuration, all the monitoring scans in your Endor Labs tenant are run on your Kubernetes cluster.

#### Warning

After configuring Outpost, you cannot use the cloud-based Endor Labs scheduler. You cannot choose to run scans of a particular project on the cloud-based Endor Labs scheduler and others with Outpost. All monitoring scans in your Endor Labs tenant will be carried out on your Kubernetes cluster.

The following sections describe how you can configure and deploy Outpost.

* [Outpost requirements](../outpost/outpost-requirements/)
* [Outpost authentication](../outpost/outpost-authentication/)
* [Outpost configuration](../outpost/outpost-configuration/)

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
