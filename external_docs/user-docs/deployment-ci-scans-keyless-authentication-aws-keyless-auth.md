---
url: https://docs.endorlabs.com/deployment/ci-scans/keyless-authentication/aws-keyless-auth/
title: Keyless authentication in AWS | Endor Labs Docs
downloaded: 2025-10-23 23:25:06
---

Keyless authentication in AWS | Endor Labs Docs



* Type to search...
* ---

[Print entire section](/deployment/ci-scans/keyless-authentication/aws-keyless-auth/_print.html)



# Keyless authentication in AWS

Learn how to implement keyless authentication for AWS.

To enable keyless authentication in AWS you’ll first need permissions to create or modify the following roles and an instance profile with the appropriate roles configured.

1. An instance access role - The instance access role is assigned to the compute resource, which needs to access Endor Labs. Your instance access role may already exist and you must ensure this role provides the permissions to allow the role to assume the role of a dedicated federation role.
2. A dedicated federation role - The dedicated federation role should have no permissions in AWS. Endor Labs will authorize requests that come from this role.

Perform the following steps to configure keyless authentication in AWS.

1. [Create or modify](#create-or-select-an-instance-profile) an existing [Instance profile](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_use_switch-role-ec2_instance-profiles.html) to assign a role to your EC2 instance.
2. [Create or modify a role an instance access role, which enables services to assume a dedicated federation role.](#create-or-modify-an-instance-access-role)
3. [Assign this role to the instance profile.](#assign-instance-access-role-to-the-instance-profile)
4. [Create a dedicated federation role to provide access to Endor Labs, which will be assumed by the instance access role.](#create-a-dedicated-federation-role)
5. [Create an authorization policy in Endor Labs.](#create-an-authorization-policy-in-endor-labs)
6. [Test keyless authentication.](#test-keyless-authentication-with-aws)

To configure keyless authentication with EKS, you will need an existing IAM ODIC provider for your cluster and to configure a Kubernetes service account annotated with your instance access role. You won’t need to create or assign roles to instance profiles or create any instance profiles. See the [AWS Documentation](https://docs.aws.amazon.com/eks/latest/userguide/associate-service-account-role.html) for additional information.

You will need to have the [AWS CLI installed](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) to follow the following procedure.

### Create or select an instance profile

An instance profile allows users to attach a single role to an EC2 instance. If you do not already have a pre-defined role or instance profile used by your EC2 instances you should create an instance profile for Endor Labs access.

To create an instance profile using the AWS CLI:

```
aws iam create-instance-profile --instance-profile-name EndorLabsAccessProfile
```

### Create or modify an instance access role

To successfully authenticate to Endor Labs you will need to assign an instance access role to the instance profile you created above.

The instance access role must at a minimum allow the compute resources that require access to perform the action `sts:AssumeRole`. If you already have a role you intend to assign to your instance profile, ensure that it has permissions to allow your compute resources to perform this action.

If you do not have an existing role you intend to use, create the role named endorlabs-instance-access-role using the instructions below.

Add the following json to a file called `endorlabs-instance-access-role.json`

```
cat > endorlabs-instance-access-role.json <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Service": [
                    "ec2.amazonaws.com"
                ]
            },
            "Action": "sts:AssumeRole"
        }
    ]
}
EOF
```

Use this file to create your instance access role using the following command:

```
aws iam create-role --role-name endorlabs-instance-access-role --assume-role-policy-document file://endorlabs-instance-access-role.json
```

### Assign instance access role to the instance profile

Next, ensure that the instance access role is assigned to the instance profile using the following command:

Your instance profile name and role name will need to be updated based on the names of these resources in your environment.

```
aws iam add-role-to-instance-profile --instance-profile-name EndorLabsAccessProfile --role-name endorlabs-instance-access-role
```

Finally, create your EC2 instance and [ensure that your instance profile is assigned to it](https://repost.aws/knowledge-center/attach-replace-ec2-instance-profile).

### Create a dedicated federation role

A dedicated federation role is leveraged to provide a least privileged role that enables access to Endor Labs. This role is designed to be assumed only by specific other roles and does not provide access to AWS resources.

To create your federation role you will need the name and AWS account number of the instance access role, which should look similar to the following policy json:

```
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "AWS": "arn:aws:iam::$ACCOUNT:role/$ROLE_NAME"
            },
            "Action": "sts:AssumeRole"
        }
    ]
  }
```

First, get the account number of the role:

```
export ACCOUNT=$(aws sts get-caller-identity | jq -r '.Account')
```

Then define the name of the instance access role. For the following example, we will assume it is endorlabs-instance-access-role.

```
export ROLE_NAME=endorlabs-instance-access-role
```

Next, create the IAM policy document.

```
cat > endorlabs-federation-aws-role.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
      {
          "Effect": "Allow",
          "Principal": {
              "AWS": "arn:aws:iam::${ACCOUNT}:role/${ROLE_NAME}"
          },
          "Action": "sts:AssumeRole"
      }
  ]
}
EOF
```

Next, apply the policy document as a role:

```
aws iam create-role --role-name endorlabs-federation --assume-role-policy-document file://endorlabs-federation-aws-role.json
```

Finally, fetch the ARN of the IAM role you’ve created using the following command and create an authorization policy for it in Endor Labs.

To fetch the ARN of the Endor Labs federation role use the following command:

```
aws iam list-roles | jq -r '.Roles[] | select(.Arn|contains("endorlabs-federation"))'.Arn
```

### Create an authorization policy in Endor Labs

Create an authorization policy in the Endor Labs user interface by following these steps:

1. Login to Endor Labs as an administrator.
2. Under Manage, navigate to **Access Control** > **Auth Policy**
3. Click **Add Auth Policy**
4. Under Identity Provider Select **AWS role**
5. Provide the appropriate permissions for your authorization policy.
6. Under claims use the Key **User** and the value of the ARN that you fetched in the previous command.
7. Click **Save Auth Policy** to finalize your keyless authentication setup.

### Test keyless authentication with AWS

On the EC2 instance you’ve configured for keyless authentication, download and install the latest version of `endorctl`. See [our documentation for instructions on downloading the latest version](../../../../endorctl/install-and-configure/)

To scan with keyless authentication you must use the flag `--aws-role-arn=<insert-your-arn>` for federated access to Endor Labs such as in the below example:

```
endorctl --aws-role-arn=<insert-your-arn> api list -r Project -n <insert-your-endorlabs-tenant> --page-size=1
```

You’ve set up and configured keyless authentication. Now you can run a test scan to ensure you can successfully scan projects using keyless authentication with AWS.

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
