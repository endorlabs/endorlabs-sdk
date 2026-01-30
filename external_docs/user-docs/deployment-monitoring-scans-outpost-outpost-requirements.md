---
url: https://docs.endorlabs.com/deployment/monitoring-scans/outpost/outpost-requirements/
title: Outpost requirements | Endor Labs Docs
downloaded: 2026-01-26 10:05:20
---

Outpost requirements | Endor Labs Docs



* Type to search...

[Print entire section](/deployment/monitoring-scans/outpost/outpost-requirements/_print.html)



# Outpost requirements

Learn about the requirements for Outpost.

You need a Kubernetes cluster with nodes that have at least 8 cores and 32 GB of RAM. Nodes should be running Linux.

You must create a namespace in your Kubernetes cluster to deploy Outpost. Use this namespace when you [configure Outpost integration](../outpost-configuration/) in Endor Labs.

Outpost currently supports the following Kubernetes distributions:

* Azure Kubernetes Service (AKS)
* Google Kubernetes Engine (GKE)
* Amazon Elastic Kubernetes Service (EKS)
* Self-hosted Kubernetes clusters

## Kubernetes cluster requirements for Outpost

The total number of nodes in the cluster depends on the number of projects that you want to scan and the number of scans that you want to run in a day.

The total scans per node per day (24 hours) is calculated based on the following formula.

```
Total scans per node per day = (Node memory ÷ Pod memory request - 1) × (24 ÷ Average scan duration)
```

Pod memory request is the memory required for running endorctl. The Outpost scheduler sets the pod memory requests. Typically, the pod memory request is 8 GB. For demanding ecosystems with call graph enabled, the Outpost scheduler sets the pod memory request to 16 GB.

You can use the following formula to calculate the number of nodes required.

```
Number of nodes = Total projects ÷ Total scans per node per day
```

The following table shows the number of nodes required for different combinations of projects and scans.

| Number of projects | Pod Memory Request | Average Scan Duration (in hours) | Scans per node per day | Node specification | Number of nodes |
| --- | --- | --- | --- | --- | --- |
| 140 | 8 GB | 1 | 72 | 8 cores, 32 GB RAM | 2 |
| 1000 | 8 GB | 1 | 72 | 8 cores, 32 GB RAM | 14 |
| 1000 | 8 GB | 1 | 360 | 32 cores, 128 GB RAM | 3 |

## Storage requirements for Outpost

Storage requirements for Outpost depend on the number of projects that you want to scan and the size of the repositories. Storage requirements increase in direct proportion to the number of concurrent scans.

You can use the following formula to calculate the storage requirements if you are running `N` number of concurrent scans.

```
Storage requirements = Sum of the largest N project sizes + extra space for other files
```

For example:

* **Project sizes:** 10 GB, 8 GB, 6 GB, 4 GB, 2 GB
* **Concurrent scans:** 3
* **Storage calculation:** 10 GB + 8 GB + 6 GB + extra space
* **Total storage required:** 24 GB + extra space for other files

We recommend that you allocate 500 GB of storage if you have several large projects and want to run several concurrent scans.

## Network requirements for Outpost

Ensure the following network requirements are met for Outpost:

* **Egress Access:** Required. Allow outbound traffic to Endor Labs platform, toolchains, and package managers.
* **DNS Resolution:** Required. Allow list of necessary domains.
* **Network Policies:** Required. Allow outbound traffic to Endor Labs platform, toolchains, and package managers.

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
