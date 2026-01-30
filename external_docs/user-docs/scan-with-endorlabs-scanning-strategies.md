---
url: https://docs.endorlabs.com/scan-with-endorlabs/scanning-strategies/
title: Scanning strategies | Endor Labs Docs
downloaded: 2026-01-29 22:21:36
---

Scanning strategies | Endor Labs Docs



* Type to search...

[Print entire section](/scan-with-endorlabs/scanning-strategies/_print.html)



# Scanning strategies

Learn strategies to best scan your projects with Endor Labs.

As you deploy Endor Labs in your environment, it’s important for your team to understand key scanning strategies.

## Set a default branch

The findings, metrics, and data shown on the dashboard and the project listing page are based on scanning the default branch, which is also known as the main context.

**Important recommendation**

If you are scanning multiple branches, it is essential to select and set one as the default branch. When performing the endorctl scan, use the flag `--as-default-branch` to designate a project branch as the default branch and view its findings.

```
endorctl scan --as-default-branch
```

If you do not set the flag `as-default-branch`, the first branch you scan is automatically considered as the default branch.
After a scan, if you switch the default branch to another using `--as-default-branch`, scans from the previous branches are erased, and their findings will no longer be available.

You do not need to set a default branch if you are using the Endor Labs GitHub App or not scanning multiple branches.

## Testing and monitoring different versions of your code

Across the software engineering lifecycle it is important that continuous testing is separated from what is monitored and reported on regularly. Often, engineering organizations want to test each and every change that enters a code base, but if security teams reported on each test they would quickly find themselves overwhelmed with noise. Endor Labs enables teams to separate what should be reported on relative to what should be tested but not reported on. Endor Labs allows teams to select reporting strategies for their software applications when integrated into CI/CD pipelines.

Here are the primary scanning and reporting strategies:

* **Reporting on the default branch** - All pull request commits are tested and all pushes or merges to the default branch are reported on and monitored by security and management teams.
* **Reporting on the latest release** - All reporting and monitoring is performed against tagged release versions. This requires each team have a mature release tagging strategy.

### How to deploy a strategy for reporting

The `endorctl scan` command by default will continuously monitor a version of your code for new findings such as unmaintained, outdated or vulnerable dependencies in the bill of materials for a package. To test a version of your code without monitoring and reporting on it, use the flag `--pr` or environment variable `ENDOR_SCAN_PR` as part of your scan.

When adopting a strategy such as reporting on the default branch, you will want to run any push or merge event to the default branch without the `--pr` flag and run any pull\_request or merged\_request event with the `--pr` flag. This allows you to test changes before they have been approved and report what has been merged to the default branch as your closest proxy to what is in production.

Let’s use the following GitHub Actions workflow as an example! In this workflow any push event will be scanned without the `--pr` flag but any pull\_request event is scanned as a point in time test of that specific version of your code.

```
name: Endor Labs Scan
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
jobs:
  scan:
    permissions:
      security-events: write # Used to upload sarif artifact to GitHub
      contents: read # Used to check out a private repository but actions/checkout.
      actions: read # Required for private repositories to upload sarif files. GitHub Advanced Security licenses are required.
      id-token: write # Used for keyless authentication to Endor Labs
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Repository
        uses: actions/checkout@v3
      - name: Setup Java
        uses: actions/setup-java@v3
        with:
          distribution: 'microsoft'
          java-version: '17'
      - name: Build Package
        run: mvn clean install
      - name: Endor Labs Scan Pull Request
        if: github.event_name == 'pull_request'
        uses: endorlabs/github-action@v1.1.1
        with:
          namespace: 'example'
          pr: true
          sarif_file: 'findings.sarif'
          pr_baseline: $GITHUB_BASE_REF
      - name: Endor Labs Reporting Scan
        if: github.event_name == 'push'
        uses: endorlabs/github-action@v1.1.1
        with:
          namespace: 'example'
          pr: false
          sarif_file: 'findings.sarif'
      - name: Endor Labs Testing Scan
        if: github.event_name == 'pull_request'
        uses: endorlabs/github-action@v1.1.1
        with:
          namespace: 'example'
          pr: true
          sarif_file: 'findings.sarif'
      - name: Upload findings to github
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: 'findings.sarif'
```

#### Scanning detached refs

In some CI/CD based environments, each time code is pushed to the default branch the exact commit SHA is checked out as a detached Git Reference. This is notably the case with Jenkins, CircleCI and GitLab Pipelines.

In these scenarios, on push or merge events Endor Labs must be told that the reference should be monitored as the default branch. You can do this with the `--detached-ref-name` flag or `ENDOR_SCAN_DETACHED_REF_NAME` environment variable. You should also couple this flag with the `--as-default-branch` flag or `ENDOR_SCAN_AS_DEFAULT_BRANCH` environment variable. This allows you to set this version of code as a version that should be monitored as well as define the name associated with the branch.

This strategy may be used for both a strategy reporting on the default branch on push events and a strategy reporting on tag creation event for that version of code.

You can see in the below GitLab Pipelines example defining the logic to manage a detached reference on GitLab.

```
    - if [ "$CI_COMMIT_REF_NAME" == "$CI_DEFAULT_BRANCH" ]; then
        export ENDOR_SCAN_AS_DEFAULT_BRANCH=true;
        export ENDOR_SCAN_DETACHED_REF_NAME="$CI_COMMIT_REF_NAME";
      else
        export ENDOR_SCAN_PR=true;
      fi
```

You can find the full GitLab pipelines reference below:

```
Endor Labs Dependency Scan:
  stage: Scan
  image: node # Modify this image to align with the build tools necessary to build your software packages
  dependencies: []
  variables:
    ENDOR_ENABLED: "true"
    ENDOR_ALLOW_FAILURE: "true"
    ENDOR_NAMESPACE: "demo"
    ENDOR_SCAN_PATH: "."
    ENDOR_ARGS: |
      --show-progress=false
      --detached-ref-name=$CI_COMMIT_REF_NAME
      --output-type=summary
      --exit-on-policy-warning
      --dependencies --secrets --git-logs
  before_script:
    - npm install yarn
  script:
    - curl https://api.endorlabs.com/download/latest/endorctl_linux_amd64 -o endorctl;
    - echo "$(curl -s https://api.endorlabs.com/sha/latest/endorctl_linux_amd64)  endorctl" | sha256sum -c;
      if [ $? -ne 0 ]; then
       echo "Integrity check failed";
       exit 1;
      fi
    - chmod +x ./endorctl
    - if [ "$DEBUG" == "true" ]; then
        export ENDOR_LOG_VERBOSE=true;
        export ENDOR_LOG_LEVEL=debug;
      fi
    - if [ "$CI_COMMIT_REF_NAME" == "$CI_DEFAULT_BRANCH" ]; then
        export ENDOR_SCAN_AS_DEFAULT_BRANCH=true;
        export ENDOR_SCAN_DETACHED_REF_NAME="$CI_COMMIT_REF_NAME";
      else
        export ENDOR_SCAN_PR=true;
      fi
    - ./endorctl scan ${ENDOR_ARGS}
  rules:
  - if: $ENDOR_ENABLED != "true"
    when: never
  - if: $CI_COMMIT_TAG
    when: never
  - if: $CI_COMMIT_REF_NAME != $CI_DEFAULT_BRANCH && $ENDOR_FEATURE_BRANCH_ENABLED != "true"
    when: never
  - if: $ENDOR_ALLOW_FAILURE == "true"
    allow_failure: true
  - if: $ENDOR_ALLOW_FAILURE != "true"
    allow_failure: false
```

### Implementing baseline scans

One of the common concerns software development teams have when adopting preventative controls is ownership of issues. Often, software has accrued significant technical debt, or new vulnerabilities arise that don’t directly impact their changes. Security teams want to have all known issues addressed while the development teams are focused on fixing issues or delivering core business value. They can’t be hindered each time a new issue impacts their entire code base.

To prevent new issues from entering the environment, security teams sometimes set policies that may break the build or return a non-zero exit code that can fail automated tests. This creates friction as there is no context around what changes a developer is responsible for versus what technical debt exists in a codebase on that day.

Establishing a baseline of what issues already exist in a software project and what issues may occur because of new updates is crucial to enabling preventative control adoption.

## Accelerating preventative control adoption with CI baselines

The high-level steps to establish and measure policies against a baseline scan are as follows:

1. Establish a baseline scan of your default branch or any other branch that undergoes regular testing
2. Integrate baseline scans into your automated workflows
3. Evaluate policy violations within the context of the branches to which you routinely merge

### Implementing baseline scan into your program

Development teams often have different delivery strategies. Some merge changes to a default branch. Others merge to a release branch that is then released to their environment. While these strategies differ across organizations, a baseline scan must exist to measure against attribute ownership.

To establish a baseline scan, your team must perform regular scans on the branch to which you merge. This often means that you scan each push of your default branch to monitor your environment and you test each pull request using the `--pr` and `--pr-baseline` flags.

The `--pr` flag is a user’s declaration that they are testing their code as they would in a CI pipeline. The `--pr-baseline` flag tells Endor Labs which Git reference to measure any changes.

For this example, we will use the default branch as a merging strategy. In this strategy, you’ll want to scan the default branch on each push event to re-establish your baseline. You’ll also want to establish your CI baseline as the default branch.

The following GitHub workflow illustrates this strategy.

```
name: Endor Labs Scan
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
jobs:
  scan:
    permissions:
      security-events: write # Used to upload sarif artifact to GitHub
      contents: read # Used to check out a private repository but actions/checkout.
      actions: read # Required for private repositories to upload sarif files. GitHub Advanced Security licenses are required.
      id-token: write # Used for keyless authentication to Endor Labs
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Repository
        uses: actions/checkout@v3
      - name: Setup Java
        uses: actions/setup-java@v3
        with:
          distribution: 'microsoft'
          java-version: '17'
      - name: Build Package
        run: mvn clean install
      - name: Endor Labs Scan Pull Request
        if: github.event_name == 'pull_request'
        uses: endorlabs/github-action@v1.1.1
        with:
          namespace: 'example'
          pr: true
          sarif_file: 'findings.sarif'
          pr_baseline: $GITHUB_BASE_REF
      - name: Endor Labs Reporting Scan
        if: github.event_name == 'push'
        uses: endorlabs/github-action@v1.1.1
        with:
          namespace: 'example'
          pr: false
          sarif_file: 'findings.sarif'
      - name: Endor Labs Testing Scan
        if: github.event_name == 'pull_request'
        uses: endorlabs/github-action@v1.1.1
        with:
          namespace: 'example'
          pr: true
          sarif_file: 'findings.sarif'
      - name: Upload findings to github
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: 'findings.sarif'
```

Each CI environment includes default environment variables that you can use to reference CI baselines in a template. See your CI providers’ documentation on default environment variables to determine the most suitable option for your requirements.

* [See the GitHub Actions documentation for GitHub default variables.](https://docs.github.com/en/actions/learn-github-actions/variables)
* [See the GitLab CI/CD documentation for the GitLab default variables.](https://docs.gitlab.com/ee/ci/variables/)

## Understand SARIF files

SARIF (Static Analysis Results Interchange Format) is an OASIS standard format for reporting static analysis results.

This standardized format allows you to:

* Integrate with multiple platforms: Upload results to GitHub Security, Azure DevOps, or other tools that support SARIF.
* Consolidate findings: Combine results from different security tools in a unified format.
* Automate workflows: Process and act on security findings programmatically.
* Track remediation: Monitor the status of security issues over time.

Endor Labs generates SARIF files that contain detailed information about security findings, dependency issues, and other analysis results from your scans.

### SARIF file structure

A SARIF file contains several key components:

* **Runs**: Each scan execution creates a run with metadata about the scan.
* **Results**: Individual findings with details about dependency vulnerabilities, SAST findings, and secrets.
* **Rules**: Descriptions of the checks that were performed.
* **Artifacts**: Information about the files and dependencies that were analyzed.

### Generate SARIF output using endorctl

SARIF files standardize security findings, enabling CI/CD integration, unified dashboards, and compliance reporting. They provide PR-level feedback, support long-term monitoring, and preserve historical data for auditing and tool migration.

To generate SARIF output with Endor Labs, use the `--sarif-file` or `-s` flag with the endorctl scan command:

```
endorctl scan --namespace=<your-namespace> --sarif-file findings.sarif
```

You can specify additional scan options when generating SARIF output, for example to include dependency scanning and git history secrets detection:

```
endorctl scan --sarif-file findings.sarif --dependencies --secrets --git-logs
```

### Upload SARIF files to GitHub

GitHub Security supports SARIF file uploads, allowing you to view Endor Labs findings directly in your repository’s Security tab. You can upload SARIF files automatically using the GitHub App (Pro), through GitHub Actions, or manually.

#### Automatic upload using GitHub App (Pro)

When you configure Endor Labs GitHub App (Pro) with a GHAS SARIF exporter, findings are automatically exported and uploaded to GitHub after each scan. See [Export findings to GitHub Advanced Security](../../scan-with-endorlabs/data-exporters/export-to-ghas/) for detailed setup instructions.

#### Automated upload using GitHub Actions

Use the following GitHub Actions workflow step to automatically upload SARIF files.

```
- name: Upload SARIF file to GitHub
  uses: github/codeql-action/upload-sarif@v3
  with:
    sarif_file: 'findings.sarif'
```

#### Manual upload via GitHub

To manually upload a SARIF file to GitHub:

1. Navigate to your GitHub repository.
2. Go to **Security** > **Code scanning** > **Upload SARIF**.
3. Select your SARIF file and upload it.

### Endor-specific SARIF extensions

Endor Labs extends the standard SARIF format with custom fields that provide additional context for vulnerability analysis and remediation. These properties are included in the `properties` field of each SARIF result.

The following fields are available in SARIF results generated by Endor Labs:

* `action-policies-triggered`: List of action policies triggered by this finding.
* `categories`: List of categories the finding belongs to.
* `cvss-score`: Common Vulnerability Scoring System (CVSS) score, ranging from 0.0 to 10.0.
* `cvss-vector`: CVSS vector string describing the characteristics of the vulnerability.
* `cvss-version`: The version of the CVSS score used.
* `epss-percentile-score`: EPSS percentile score, showing how severe the vulnerability is compared to others.
* `epss-probability-score`: Exploit Prediction Scoring System (EPSS) probability score, indicating likelihood of exploitation.
* `explanation`: Detailed explanation of the finding and its implications.
* `finding-url`: URL to view the finding in Endor Labs.
* `finding-uuid`: Unique identifier for the finding.
* `impact-score`: Custom impact score assigned to the finding.
* `project-uuid`: Unique identifier for the project where the finding was discovered.
* `remediation`: Recommended steps to fix or mitigate the finding.
* `tags`: List of tags associated with the finding, used for categorization and filtering.

Here are examples of SARIF output for SCA, secrets, and SAST findings, including Endor-specific extensions.

* SCA findings
* Secrets detection
* SAST findings

```
{
  "results": [
    {
      "ruleId": "SCA-Vulnerability",
      "kind": "fail",
      "level": "error",
      "message": {
        "text": "CVE-2021-44228 in org.apache.logging.log4j:log4j-core@2.14.1 (maven) — upgrade to 2.17.1 or later."
      },
      "locations": [
        {
          "physicalLocation": {
            "artifactLocation": {
              "uri": "pom.xml"
            },
            "region": {
              "startLine": 42
            }
          }
        }
      ],
      "properties": {
        "action-policies-triggered": ["block-critical-vulns"],
        "categories": ["dependency", "security"],
        "cvss-score": 10.0,
        "cvss-vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H",
        "cvss-version": "V3_1",
        "epss-percentile-score": 0.97,
        "epss-probability-score": 0.97576,
        "explanation": "This version of log4j-core contains CVE-2021-44228, also known as Log4Shell. This is a critical remote code execution vulnerability that allows attackers to execute arbitrary code by controlling log message content.",
        "finding-url": "https://app.endorlabs.com/findings/abc123",
        "finding-uuid": "abc123-def456",
        "impact-score": 10.0,
        "project-uuid": "proj-789",
        "remediation": "Upgrade log4j-core to version 2.17.1 or later. If immediate upgrade is not possible, set the JVM parameter -Dlog4j2.formatMsgNoLookups=true as a temporary mitigation.",
        "tags": ["CVE-2021-44228", "log4shell", "critical", "rce"]
      }
    }
  ]
}
```

```
{
  "results": [
    {
      "ruleId": "AWS Access Token",
      "message": {
        "text": "Invalid AWS Access Token: ID #3da668"
      },
      "fullDescription": {
        "text": "Invalid secrets should be audited for suspicious activity and ignored."
      },
      "help": {
        "text": "Inspect any service logs to determine if the exposed secret has been used for suspicious activity.\n\nIf you'd like to ignore this issue add the comment \"endorctl:allow\" to the secret location in your code.\n"
      },
      "shortDescription": {
        "text": "Invalid AWS Access Token: ID #3da668"
      },
      "properties": {
        "finding-url": "https://app.endorlabs.com/findings/secret-456",
        "finding-uuid": "secret-456-def",
        "project-uuid": "proj-789",
        "security-severity": "1.0",
        "tags": [
          "INVALID_SECRET",
          "NORMAL",
          "POLICY"
        ]
      }
    }
  ]
}
```

```
{
  "results": [
    {
      "level": "note",
      "locations": [
        {
          "physicalLocation": {
            "artifactLocation": {
              "uri": "BackendServer/middlewares/validateToken.js"
            },
            "region": {
              "startLine": 77
            }
          }
        }
      ],
      "message": {
        "text": "Problem:\nHardcoded JWT secret or private key was found. Hardcoding secrets like JWT signing keys poses a significant security risk. If the source code ends up in a public repository or is compromised, the secret is exposed. Attackers could then use the secret to generate forged tokens and access the system. Store it properly in an environment variable.\n\nSolution:\nHere are some recommended safe ways to access JWT secrets:\n- Use environment variables to store the secret and access it in code instead of hardcoding. This keeps it out of source control.\n- Use a secrets management service to securely store and tightly control access to the secret. Applications can request the secret at runtime.\n- For local development, use a .env file that is gitignored and access the secret from process.env.\n\nsample code snippet of accessing JWT secret from env variables\n```\nconst token = jwt.sign(payload, process.env.SECRET, { algorithm: 'HS256' });\n```\n"
      },
      "properties": {
        "explanation": "The rule detects the use of hardcoded JWT secrets or private keys in JavaScript code. Hardcoding secrets like JWT signing keys poses a significant security risk because if the source code is exposed, the secret is compromised. This allows attackers to generate forged tokens, potentially gaining unauthorized access to systems and sensitive data. The impact is high because it directly affects the confidentiality and integrity of the application.",
        "finding-url": "https://app.endorlabs.com/findings/sast-789",
        "finding-uuid": "sast-789-ghi",
        "impact-score": 8.7,
        "project-uuid": "proj-789",
        "remediation": "To remediate the use of hardcoded JWT secrets, avoid embedding secrets directly in the source code. Instead, use environment variables to store secrets securely and access them in your code. For example, in JavaScript, you can use `process.env.SECRET` to access the secret stored in an environment variable:\n\n```javascript const token = jwt.sign(payload, process.env.SECRET, { algorithm: 'HS256' }); ```\n\nAdditionally, consider using a secrets management service to securely store and manage access to secrets. For local development, use a `.env` file that is gitignored to prevent it from being included in version control.",
        "tags": [
          "A07:2021",
          "Identification-and-Authentication-Failures",
          "OWASP-Top-10",
          "SANS-Top-25"
        ]
      },
      "ruleId": "Use of hard-coded credentials in JWT"
    }
  ]
}
```

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
