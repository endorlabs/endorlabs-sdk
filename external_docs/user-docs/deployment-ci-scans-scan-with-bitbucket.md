---
url: https://docs.endorlabs.com/deployment/ci-scans/scan-with-bitbucket/
title: Scanning in Bitbucket Pipelines | Endor Labs Docs
downloaded: 2026-02-03 00:50:14
---

Scanning in Bitbucket Pipelines | Endor Labs Docs



* Type to search...

[Print entire section](/deployment/ci-scans/scan-with-bitbucket/_print.html)



# Scanning in Bitbucket Pipelines

Learn how to implement Endor Labs in a Bitbucket pipeline.

Bitbucket Pipelines is a continuous integration and continuous delivery (CI/CD) service built into Bitbucket. It allows developers to automatically build, test, and deploy their code based on a configuration file `bitbucket-pipelines.yml` defined in the root of their repository.

To integrate Endor Labs into a Bitbucket pipeline:

1. [Authenticate to Endor Labs](#authenticate-to-endor-labs)
2. Install your build toolchain
3. Build your code
4. Scan with Endor Labs

## Authenticate to Endor Labs

Configure an API key and secret in the `bitbucket-pipelines.yml` file for authentication. See [managing API keys](../../../administration/api-keys/) for more information on generating an API key for Endor Labs.

## Configure your Bitbucket pipeline

**Important**

Bitbucket Pipelines may check out commits in a detached HEAD state, which can lead to fragmented branch tracking in Endor Labs. See [Set up branch tracking in Bitbucket Pipelines](#set-up-branch-tracking-in-bitbucket-pipelines) to configure proper branch context.

To create a Bitbucket pipeline reference the following steps:

1. Create a `bitbucket-pipelines.yml` file in your repository if you do not already have one.
2. In your `bitbucket-pipelines.yml` file customize the job configuration based on your project’s requirements using [the following example](#example).
3. Adjust the image field to use the necessary build tools for constructing your software packages, and align your build steps with those of your project.
4. Update your Endor Labs tenant namespace to the appropriate namespace for your project.
5. Update your default branch from main if you do not use main as the default branch name.
6. Modify any dependency or artifact caches to align with the languages and caches used by your project.

## Example

Use the following example to get started. Make sure to customize this job with your specific build environment and build steps.

### Bitbucket configuration

```
simage: maven:3.6.3-jdk-11

pipelines:
  branches:
    main:
      - step:
          name: "Build and Test"
          script:
            - mvn install -DskipTests
            - echo "Running Endor Labs Scan"
            - curl https://api.endorlabs.com/download/latest/endorctl_linux_amd64 -o endorctl
            - echo "$(curl -s https://api.endorlabs.com/sha/latest/endorctl_linux_amd64)  endorctl" | sha256sum -c
            - chmod +x ./endorctl
            - ./endorctl scan -n $ENDOR_NAMESPACE --api-key $ENDOR_API_CREDENTIALS_KEY --api-secret $ENDOR_API_CREDENTIALS_SECRET
  pull-requests:
    '**':
      - step:
          name: "Build and Test on PR to Main"
          script:
            - mvn install -DskipTests
            - echo "Running Endor Labs PR Scan"
            - curl https://api.endorlabs.com/download/latest/endorctl_linux_amd64 -o endorctl
            - echo "$(curl -s https://api.endorlabs.com/sha/latest/endorctl_linux_amd64)  endorctl" | sha256sum -c
            - chmod +x ./endorctl
            - ./endorctl scan --pr --pr-baseline=main --languages=java --output-type=json -n $ENDOR_NAMESPACE --api-key $ENDOR_API_CREDENTIALS_KEY --api-secret $ENDOR_API_CREDENTIALS_SECRET | tee output.json
            #Optional - Comment on the PR
            # - apt-get update
            # - apt-get install -y python3 python3-pip
            # - pip3 install -r requirements.txt
            # - python3 add-bitbucket-pr-comments.py output.json
```

Once you’ve set up Endor Labs, you can test your CI implementation to ensure it is successful and then proceed with your scans.

### View PR comments for policy violations

You can also use the Insights feature in Bitbucket Pipelines to indicate if the changes in your pull requests violated any policies set in Endor Labs.

```
import json
import os
import sys
import requests
import argparse

# Check for required environment variables
BITBUCKET_REPO_OWNER = os.getenv('BITBUCKET_REPO_OWNER')
BITBUCKET_REPO_SLUG = os.getenv('BITBUCKET_REPO_SLUG')
BITBUCKET_COMMIT = os.getenv('BITBUCKET_COMMIT')

if not all([BITBUCKET_REPO_OWNER, BITBUCKET_REPO_SLUG, BITBUCKET_COMMIT]):
     sys.exit("Error: One or more required environment variables (BITBUCKET_REPO_OWNER, BITBUCKET_REPO_SLUG, BITBUCKET_COMMIT) are not set.")

#This is an internal proxy running in the BitBucket environment to accept Code Insights
proxies = {"http": "http://localhost:29418"}

def load_json_with_unescaped_characters(file_path):
    """Load and return JSON data from a file, replacing unescaped characters if necessary."""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            json_str = file.read().strip()
        return json.loads(json_str)
    except json.decoder.JSONDecodeError as e:
        print(f"Failed to parse JSON: {e}")
        return None
    except FileNotFoundError:
        print(f"File not found: {file_path}")
        sys.exit()

def construct_report_payload(endor_findings):
    """Construct and return the payload for creating a Bitbucket report."""
    warning_findings_count = len(endor_findings.get('warning_findings', []))
    blocking_findings_count = len(endor_findings.get('blocking_findings', []))
    total_violations = warning_findings_count + blocking_findings_count
    result = "PASSED" if total_violations == 0 else "FAILED"
    report_payload = {
        "title": "Endor Labs Policy Violations",
        "details": f"Endor Labs detected {total_violations} policy violations associated with this pull request.\n\n{endor_findings['warnings'][0]}",
        "report_type": "SECURITY",
        "reporter": "Endor Labs",
        "link": f"https://app.endorlabs.com/t/{namespace}/projects/{project_uuid}/pr-runs/{report_id}",
        "logo_url": "https://avatars.githubusercontent.com/u/92199924",
        "result": result,
        "data": [
            {"title": "Warning Findings", "type": "NUMBER", "value": warning_findings_count},
            {"title": "Blocking Findings", "type": "NUMBER", "value": blocking_findings_count}
        ]
    }
    return report_payload

def construct_annotation_payload(finding):
    """Construct and return the payload for creating an annotation in Bitbucket."""
    title = "Endor Labs Policy Violation"
    summary = finding['meta']['description']
    details =  f"{finding['spec']['summary']}\n\n{finding['spec']['remediation']}"
    severity = "CRITICAL" if finding['spec']['level'] == "FINDING_LEVEL_CRITICAL" else \
               "HIGH" if finding['spec']['level'] == "FINDING_LEVEL_HIGH" else \
               "MEDIUM" if finding['spec']['level'] == "FINDING_LEVEL_MEDIUM" else "LOW"
    affected_paths = finding['spec'].get('dependency_file_paths', [])
    path = affected_paths[0] if affected_paths else "Unknown file"
    annotation_payload = {
        "external_id": finding['uuid'],
        "title": title,
        "annotation_type": "VULNERABILITY",
        "summary": summary,
        "details": details,
        "severity": severity,
        "path": path
    }
    return annotation_payload

def send_report(report_payload):
    """Send the constructed report payload to the Bitbucket API."""
    report_url = f"http://api.bitbucket.org/2.0/repositories/{BITBUCKET_REPO_OWNER}/{BITBUCKET_REPO_SLUG}/commit/{BITBUCKET_COMMIT}/reports/{report_id}"
    response = requests.put(report_url, json=report_payload, proxies=proxies)
    if response.status_code in [200, 201]:
        print("Report created or updated successfully")
    else:
        print(f"Failed to create or update report: {response.text}")

def send_annotation(annotation_payload):
    """Send the constructed annotation payload to the Bitbucket API."""
    annotation_url = f"{base_url}/{report_id}/annotations/{annotation_payload['external_id']}"
    response = requests.put(annotation_url, json=annotation_payload, proxies=proxies)
    if response.status_code in [200, 201]:
        print("Annotation added successfully")
    else:
        print(f"Failed to add annotation: {response.text}")

def process_findings(filename):
    """Load findings from JSON, create a report, and add annotations for each finding."""
    endor_findings = load_json_with_unescaped_characters(filename)
    if endor_findings is None:
        print("Failed to load findings. Exiting.")
        return

    global report_id, project_uuid, namespace

    # Define the order of keys to check
    finding_types = ['all_findings', 'warning_findings', 'blocking_findings']

    # Iterate over finding types and extract the first one found
    for finding_type in finding_types:
        if endor_findings.get(finding_type):
            first_finding = endor_findings[finding_type][0]
            report_id = first_finding['context']['id']
            project_uuid = first_finding['spec']['project_uuid']
            namespace = first_finding['tenant_meta']['namespace']
            break  # Stop after finding the first non-empty list

    if not report_id:
        print("No findings found.")
        sys.exit()

    # Prepare the base URL for Bitbucket API requests
    global base_url
    base_url = f"http://api.bitbucket.org/2.0/repositories/{BITBUCKET_REPO_OWNER}/{BITBUCKET_REPO_SLUG}/commit/{BITBUCKET_COMMIT}/reports"

    # Create the report
    report_payload = construct_report_payload(endor_findings)
    send_report(report_payload)

    # Iterate over findings and create annotations
    for finding in endor_findings.get('blocking_findings', []) + endor_findings.get('warning_findings', []):
        annotation_payload = construct_annotation_payload(finding)
        send_annotation(annotation_payload)

def main():
    """Main function to parse arguments and process findings."""
    parser = argparse.ArgumentParser(description="Script to process findings and update Bitbucket via API.")
    parser.add_argument("filename", help="Filename containing the JSON findings.")
    args = parser.parse_args()

    process_findings(args.filename)

if __name__ == "__main__":
    main()
```

## Set up branch tracking in Bitbucket Pipelines

In Git, a detached HEAD state occurs when the repository checks out a specific commit instead of a branch reference. In this state, Git points the HEAD directly to a commit hash, without associating it with a named branch. As a result, actions performed, such as creating new commits or running automated scans, do not carry branch identity unless explicitly specified.

Proper branch context enables Endor Labs to:

* Associate scans with the correct branch
* Identify scans on the monitored default branch
* Track findings and display metrics accurately across branches

Without proper branch configuration, Endor Labs may create multiple branch entries for the same logical branch, leading to fragmented reporting and inaccurate metrics.

![Project with multiple branch entries](../../../images/branch-fragmentation.png)

Bitbucket Pipelines often check out commits by their SHA instead of the branch name, which creates a detached HEAD state.

Use `--detached-ref-name` only to specify the branch name for a commit in detached HEAD state. This associates the commit with the correct branch without setting it as the default branch.

```
script:
  - ./endorctl scan -n $ENDOR_NAMESPACE \
    --detached-ref-name="$BITBUCKET_BRANCH" \
    --api-key $ENDOR_API_CREDENTIALS_KEY \
    --api-secret $ENDOR_API_CREDENTIALS_SECRET
```

Use both `--detached-ref-name` and `--as-default-branch` together when you want to associate the commit with a branch and set it as the default branch scan.

```
script:
  - ./endorctl scan -n $ENDOR_NAMESPACE \
    --as-default-branch \
    --detached-ref-name="$BITBUCKET_BRANCH" \
    --api-key $ENDOR_API_CREDENTIALS_KEY \
    --api-secret $ENDOR_API_CREDENTIALS_SECRET
```

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
