---
url: https://docs.endorlabs.com/deployment/ci-scans/scan-with-jenkins/
title: Scanning with Jenkins | Endor Labs Docs
downloaded: 2025-10-23 23:26:34
---

Scanning with Jenkins | Endor Labs Docs



* Type to search...
* ---

[Print entire section](/deployment/ci-scans/scan-with-jenkins/_print.html)



# Scanning with Jenkins

Learn how to implement Endor Labs in a Jenkins pipeline.

Jenkins is an open-source automation server widely used for building, testing, and deploying software. Specifically in the context of CI/CD pipelines, Jenkins serves as a powerful tool to automate various stages of the software development lifecycle.

To integrate Endor Labs into your Jenkins CI/CD processes:

1. [Authenticate to Endor Labs](#authenticate-to-endor-labs)
2. Install NodeJS plugin in Jenkins.
3. Install your build toolchain
4. Build your code
5. Scan with Endor Labs

## Authenticate to Endor Labs

To configure keyless authentication see [the keyless authentication documentation](../keyless-authentication/)

If you choose not to use keyless authentication you can configure an API key and secret in Jenkins for authentication using the following steps. See [managing API keys](../../../administration/api-keys/) for more information on generating an API key for Endor Labs.

1. In your Jenkins environment, navigate to **Manage Jenkins**.
2. Enter a credential name for reference such as `endorlabs` or reuse an existing context.
3. Click into your new or existing context. Add any project restrictions and select **Add Environment Variable**.
4. In **Environment Variable Name**, enter **ENDOR\_API\_CREDENTIALS\_KEY** and in **Value**, enter the Endor Labs API Key.
5. Select **Add Environment Variable**.

## Install Node.js plugin in Jenkins

See [Jenkins documentation](https://plugins.jenkins.io/nodejs/) to install Node.js plugin in Jenkins. You must have the Node.js plugin to use npm and download endorctl.

## Configure your Jenkins pipeline

To create a Jenkins pipeline:

1. Create a configuration pipeline file in your repository if you do not already have one using the pipeline project.
2. In your configuration pipeline file customize the job configuration based on your project’s requirements using one of the examples, [simple Jenkins configuration](#simple-jenkins-configuration-using-npm) or [Jenkins pipeline using curl](#jenkins-pipe-line-for-curl-to-download-endorctl-binary).
3. Ensure that the context you created is part of the workflow if you are not using keyless authentication.
4. Adjust the image field to conform to the required build tools for constructing your software packages, and synchronize your build steps with those of your project.
5. Update your Endor Labs tenant namespace to the appropriate namespace for your project.
6. Update your default branch from main if you do not use main as the default branch name.
7. Modify any dependency or artifact caches to align with the languages and caches used by your project.

## Examples

Use the following examples to get started. Make sure to customize this job with your specific build environment and build steps.

### Simple Jenkins configuration using npm

```
pipeline {
    agent any
    tools {nodejs "NodeJS"}
    environment {
        ENDOR_API = credentials('ENDOR_API')
        ENDOR_NAMESPACE = credentials('ENDOR_NAMESPACE')
        ENDOR_API_CREDENTIALS_KEY = credentials('ENDOR_API_CREDENTIALS_KEY_1')
        ENDOR_API_CREDENTIALS_SECRET = credentials('ENDOR_API_CREDENTIALS_SECRET_1')
    }
    stages {
        stage('Checkout') {
            steps {
                // Checkout the Git repository
                checkout scmGit(branches: [[name: '*/main']], userRemoteConfigs: [[url: 'https://github.com/endorlabstest/app-java-demo.git']])
            }
        }

        stage('Build') {
            steps {
                // Perform any build steps if required
                sh 'mvn clean install'
            }
        }

        stage('endorctl Scan') {
            steps {
                script {
                    // Define the Node.js installation name configured in Jenkins
                    NODEJS_HOME = tool name: 'NodeJS', type: 'jenkins.plugins.nodejs.tools.NodeJSInstallation'
                    PATH = "$NODEJS_HOME/bin:${env.PATH}"
                }

                // Download and install endorctl.
                sh 'npm install -g endorctl'
                // Check endorctl version and installation.
                sh 'endorctl --version'
                // Run the scan.
                sh('endorctl scan -a $ENDOR_API -n $ENDOR_NAMESPACE --api-key $ENDOR_API_CREDENTIALS_KEY --api-secret $ENDOR_API_CREDENTIALS_SECRET')

            }
        }

        stage('Results') {
            steps {
                // Publish or process the vulnerability scan results
                // Publish reports, fail the build on vulnerabilities, etc.
                echo 'Publish results'
            }
        }
    }

}
```

### Jenkins pipe line for curl to download endorctl binary

The following example includes curl to download the endorctl binary.

```
pipeline {
    agent any

    // Endorctl scan uses following environment variables to the trigger endorctl scan
    environment {
        ENDOR_API = credentials('ENDOR_API')
        ENDOR_NAMESPACE = credentials('ENDOR_NAMESPACE')
        ENDOR_API_CREDENTIALS_KEY = credentials('ENDOR_API_CREDENTIALS_KEY')
        ENDOR_API_CREDENTIALS_SECRET = credentials('ENDOR_API_CREDENTIALS_SECRET')
    }
    stages {
        // Not required if repository is allready cloned to trigger a endorctl scan
        stage('Checkout') {
            steps {
                // Checkout the Git repository
                checkout scmGit(branches: [[name: '*/main']], userRemoteConfigs: [[url: 'https://github.com/endorlabstest/app-java-demo.git']])
            }
        }

        stage('Build') {
            // Not required if project is already built
            steps {
                // Perform any build steps if required
                sh 'mvn clean install'
            }
        }

        stage('endorctl Scan') {
            steps {
                // Download and install endorctl.
                sh '''#!/bin/bash
                    echo "Downloading latest version of endorctl"
                    VERSION=$(curl $ENDOR_API/meta/version | jq -r '.ClientVersion')
                    ENDORCTL_SHA=$(curl $ENDOR_API/meta/version | jq -r '.ClientChecksums.ARCH_TYPE_LINUX_AMD64')
                    curl $ENDOR_API/download/endorlabs/"$VERSION"/binaries/endorctl_"$VERSION"_linux_amd64 -o endorctl
                    echo "$ENDORCTL_SHA  endorctl" | sha256sum -c
                    if [ $? -ne 0 ]; then
                        echo "Integrity check failed"
                        exit 1
                    fi
                    chmod +x ./endorctl
                    // Check endorctl version and installation.
                    ./endorctl --version
                    // Run the scan.
                    ./endorctl scan -a $ENDOR_API -n $ENDOR_NAMESPACE --api-key $ENDOR_API_CREDENTIALS_KEY --api-secret $ENDOR_API_CREDENTIALS_SECRET
                '''
            }
        }
    }
}
```

Once you’ve set up Endor Labs you can test your CI implementation is successful and begin scanning.

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
