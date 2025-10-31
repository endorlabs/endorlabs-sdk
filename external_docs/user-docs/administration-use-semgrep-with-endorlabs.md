---
url: https://docs.endorlabs.com/administration/use-semgrep-with-endorlabs/
title: Use Semgrep with Endor Labs | Endor Labs Docs
downloaded: 2025-10-27 12:59:21
---

Use Semgrep with Endor Labs | Endor Labs Docs



* Type to search...
* ---

[Print entire section](/administration/use-semgrep-with-endorlabs/_print.html)



# Use Semgrep with Endor Labs

Learn how to use Semgrep instead of Opengrep with Endor Labs.

Endor Labs uses [Opengrep](https://www.opengrep.dev/) to scan your code for SAST and AI model findings. Endor Labs downloads Opengrep for you when you run a scan and works seamlessly.

You can also use [Semgrep Community Edition](https://github.com/semgrep/semgrep) instead of Opengrep with Endor Labs.

## Download Semgrep

You need to download and install Semgrep Community Edition on your machine before you use it with Endor Labs.

We recommend that you install Semgrep version 1.99.0.

Though Semgrep supports installation with Brew on macOS, it does not support installation of a specific version.

To install Semgrep you need to have a Python environment set up on your machine with pip.

`pip install semgrep==1.99.0`

## Use Semgrep with Endor Labs

Set the environment variable `ENDOR_SCAN_SEMGREP_PROGRAM` to the value `semgrep` to use Semgrep with Endor Labs. See [Global flags and environment variables](../../endorctl/environment-variables/) for more information.

Make sure that Semgrep is properly installed on your machine and is present in the PATH.

```
semgrep --version
```

Run the following command to set the environment variable.

```
export ENDOR_SCAN_SEMGREP_PROGRAM=semgrep
```

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
