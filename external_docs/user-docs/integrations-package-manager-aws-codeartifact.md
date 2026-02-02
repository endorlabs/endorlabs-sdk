---
url: https://docs.endorlabs.com/integrations/package-manager/aws-codeartifact/
title: Configure integration with AWS | Endor Labs Docs
downloaded: 2026-01-29 22:21:51
---

Configure integration with AWS | Endor Labs Docs



* Type to search...

[Print entire section](/integrations/package-manager/aws-codeartifact/_print.html)



# Configure integration with AWS

Learn how to configure package manager integrations with AWS CodeArtifact.

Configure Endor Labs to integrate with AWS CodeArtifact to use private libraries to build and scan your software.

You must Create an OpenID Connect provider in AWS IAM to allow Endor Labs to authenticate and assume roles securely. Then, configure an IAM role with a trust policy to grant Endor Labs read-only access to AWS CodeArtifact repositories.

You can configure the resources using the [AWS Management Console](#create-aws-resources-from-the-aws-user-interface), [AWS CloudFormation Template](#create-the-aws-resources-using-cft-template), or the [AWS CLI](#create-resources-from-the-aws-cli).

## Create AWS resources from the AWS management console

Create the AWS resources required for this integration from the AWS user management console.

### Create an OpenID Connect provider

In AWS, create an OpenID Connect provider and authenticate Endor Labs to assume roles.

1. Sign into Identity and Access Management (IAM).
2. From **Access Management**, select **Identity Providers**.
3. Click **Add Provider** and choose **OpenID Connect**.
4. In **Provider URL** enter the Endor Labs application URL `https://api.endorlabs.com`.
5. Enter an **Audience** such as **endor-aws-code-artifact** and click **Add Provider**.

You must keep the **Provider URL** and **Audience** values handy.

### Create an IAM role with trust policies

In AWS IAM, create roles that Endor Labs can assume once its users or services are authenticated. Associate each role with a trust policy that grants Endor Labs read-only access to repositories in AWS CodeArtifact.

1. From **IAM**, select **Roles**.
2. Click **Create Role**.
3. From **Trusted entity type**, select **Web Identity** and click **Next**.
4. Select the **Identity provider** you created in the previous task and for **Audience** select the exact value used in the previous task then click **Add condition**.
5. Under **Add condition** set the **Key** to `api.endorlabs.com:sub`, set the **Condition** to `StringLike` and for the **value**, input `<insert-your-tenant>/*`. Make sure to replace `<insert-your-tenant>` with your tenant name. For example `demo/*`.
6. Add one more condition setting **Key** to `api.endorlabs.com:sub`, set the **Condition** to `StringLike` and for the **value**, input `<insert-your-tenant>.*/*`, for example `demo.*/*` and click **Next**.
7. From **Permission policies**, select **AWSCodeArtifactReadOnlyAccess** and click **Next**.
8. Enter a name for the role such as **endor-aws-code-artifact-role** and include an optional description.
9. Review the **Select trusted entities** section, then click **Edit** to make modifications if required. It should look like the following example.

```
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": "sts:AssumeRoleWithWebIdentity",
            "Principal": {
                "Federated": "arn:aws:iam::<AWS-Account-ID>:oidc-provider/api.endorlabs.com"
            },
            "Condition": {
                "StringLike": {
                    "api.endorlabs.com:sub": [
                        "<insert-your-namespace>/*",
                        "<insert-your-namespace>.*/*"
                    ]
                },
                "StringEquals": {
                    "api.endorlabs.com:aud": [
                        "endor-aws-code-artifact"
                    ]
                }
            }
        }
    ]
}
```

8. Click **Create Role**.

You must keep the role ARN handy to enter in the Endor Labs application.

You can now go and [configure the package manager integration in Endor Labs](#configure-package-manager-integration-in-endor-labs-with-aws-codeartifact)

## Create AWS resources using a CFT template

Use AWS CloudFormation Template (CFT) to automate the creation and configuration of AWS resources required for this integration.

1. Create a `.cft` file from the following script entering the OIDC URL, audience, namespace, and role name.

```
AWSTemplateFormatVersion: '2010-09-09'
Description: CloudFormation template to create an IAM OpenID Connect (OIDC) identity provider and an IAM role with AWSCodeArtifactReadOnlyAccess.

Parameters:
  OIDCUrl:
    Description: The URL of the OIDC provider (e.g., https://api.endorlabs.com).
    Type: String
    Default: "https://api.endorlabs.com"

  ClientId:
    Description: The audience claim to use in the OIDC trust policy (e.g., endor-aws-code-artifact).
    Type: String
    Default: "endor-aws-code-artifact"

  Namespace:
    Description: The namespace in the OIDC sub claim to allow (e.g., demo).
    Type: String
    Default: "Enter your Endor Labs namespace"

  RoleName:
    Description: IAM role name (e.g., endor-aws-code-artifact-role).
    Type: String
    Default: "endor-aws-code-artifact-role"

Resources:
  OpenIDConnectProvider:
    Type: "AWS::IAM::OIDCProvider"
    Properties:
      Url: !Ref OIDCUrl
      ClientIdList:
        - !Ref ClientId
    DeletionPolicy: Retain

  CodeArtifactRole:
    Type: "AWS::IAM::Role"
    Properties:
      RoleName: !Ref RoleName
      AssumeRolePolicyDocument:
        Version: "2012-10-17"
        Statement:
          - Effect: "Allow"
            Principal:
              Federated: !Ref OpenIDConnectProvider  # Directly reference OIDC Provider created in the same template
            Action: "sts:AssumeRoleWithWebIdentity"
            Condition:
              StringEquals:
                "api.endorlabs.com:aud": !Ref ClientId
              StringLike:
                "api.endorlabs.com:sub":
                  - !Sub "${Namespace}/*"
                  - !Sub "${Namespace}.*/*"
      ManagedPolicyArns:
        - "arn:aws:iam::aws:policy/AWSCodeArtifactReadOnlyAccess"
    DeletionPolicy: Retain

Outputs:
  TargetRoleArn:
    Description: The ARN of the newly created IAM role
    Value: !GetAtt CodeArtifactRole.Arn

  AllowedAudience:
    Description: The allowed audience
    Value: !Ref ClientId
```

2. Save this file with an appropriate name such as `awscodeartifact-endor-labs.cft`, and have it handy.
3. Sign into AWS CloudFormation and search for **Stacks**.
4. Click **Create Stack** and select **Choose an existing template**.
5. From **Template source**, select **Upload a template file**.
6. Click **Choose file**, select the file you saved `awscodeartifact-endor-labs.cft` and click **Next**.
7. In **Specify stack details**, choose a name for the stack, verify the **Parameters** you entered in the script and click **Next**.
8. Select the acknowledgement from **Configure stack options** and click **Next**.
9. From **Review and Create**, review the details and click **Submit**. Check the progress of the creation of your resources from **Stacks**. Once the stack is created, you can see the status as **CREATE\_COMPLETE**.
10. Click **Outputs** to see the target role ARN and the **AllowedAudience** values. Have the values handy to enter in the Endor Labs application.
11. You can now go and [configure the package manager integration in Endor Labs](#configure-package-manager-integration-in-endor-labs-with-aws-codeartifact)

## Create resources from the AWS CLI

To create the necessary resources for CodeArtifact integration with the AWS CLI use the following procedure:

1. First, create a new OIDC provider in AWS:

```
aws iam create-open-id-connect-provider \
    --url https://api.endorlabs.com \
    --client-id-list endor-aws-code-artifact
```

2. Keep the **OpenIDConnectProviderArn** returned during the create command handy. If you lose it you can retrieve it using the following command:

```
aws iam list-open-id-connect-providers
```

3. Next, you’ll need to create a role to provide the OIDC provider access to AWS CodeArtifact. Ensure you replace `<insert-your-namespace>` with your Endor Labs namespace and `<insert-your-account-id>` with your AWS account ID.

```
aws iam create-role \
    --role-name endor-aws-code-artifact-role \
    --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Federated": "arn:aws:iam::<insert-your-account-id>:oidc-provider/api.endorlabs.com"
            },
            "Action": "sts:AssumeRoleWithWebIdentity",
            "Condition": {
                "StringEquals": {
                    "api.endorlabs.com:aud": "endor-aws-code-artifact"
                },
                "StringLike": {
                    "api.endorlabs.com:sub": [
                        "<insert-your-namespace>/*",
                        "<insert-your-namespace>.*/*"
                    ]
                }
            }
        }
    ]
}'
```

4. Finally, assign the role a permissions policy to access AWS CodeArtifact.

```
aws iam attach-role-policy \
    --role-name endor-aws-code-artifact-role \
    --policy-arn arn:aws:iam::aws:policy/AWSCodeArtifactReadOnlyAccess
```

5. You can now go and [configure the package manager integration in Endor Labs](#configure-package-manager-integration-in-endor-labs-with-aws-codeartifact)

## Configure package manager integration in Endor Labs with AWS CodeArtifact

After creating an IAM role in AWS with the necessary trust policies, configure AWS CodeArtifact package manager integration within the Endor Labs application.

1. Sign in to Endor Labs and under **Manage**, select **Integrations**.
2. Select the package manager configuration you’d like to customize and click **Manage**
3. In the upper right-hand corner, select **Add Package Manager**.
4. Select **AWS Code Artifactory**.
5. In **DOMAIN**, enter the name of your repository in AWS CodeArtifact.
6. In **DOMAIN OWNER**, enter the AWS account ID that owns the CodeArtifact repository.
7. In **REPOSITORY**, enter the repository name.
8. In **TARGET ROLE ARN**, enter the role ARN you created.
9. In **ALLOWED AUDIENCE**, enter the **Audience** value specified during role creation. In this example we used **endor-aws-code-artifact**.
10. In **REGION**, enter the AWS region of the AWS Code Artifact Repository.
11. Select if you want to **Propagate this package manager to all child namespaces** from **Advanced**.
12. Select **Add Package Manager**.

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
