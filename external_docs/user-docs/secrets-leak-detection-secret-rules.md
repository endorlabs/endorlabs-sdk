---
url: https://docs.endorlabs.com/secrets-leak-detection/secret-rules/
title: Manage secret rules | Endor Labs Docs
downloaded: 2026-02-03 00:49:56
---

Manage secret rules | Endor Labs Docs



* Type to search...

[Print entire section](/secrets-leak-detection/secret-rules/_print.html)



# Manage secret rules

Use secret rules to scan and detect secrets

You can use the following rules to scan your codebase and detect secrets:

* **System rules**: Endor Labs provides out-of-the-box rules for secret patterns for many public services like GitHub, GitLab, AWS, Bitbucket, Dropbox, and more.
* **Custom rules**: If you are using a service that is not included in the out-of-the-box list of secret patterns provided by Endor Labs, you can build your own custom rule to scan and detect the secrets for any service.

The following table lists the most important fields of the rule definition.

| Field name | Description |
| --- | --- |
| `meta.name` | The name of the rule. |
| `spec.rule_id` | The rule identifier must be unique across all rules, both the system and the ones created in your namespace. |
| `spec.regex` | The secret detection rule contains the pattern that the scanner will try to match. |
| `spec.keywords` | The keywords are used for an initial check of a pattern before the full regex expression gets evaluated. |
| `spec.validation` | The details about how to validate a secret. |
| `spec.entropy` | The minimum Shannon entropy a regex group must have to be considered. |
| `spec.disabled` | Set to `false` for system rules. |

## Create a secret rule

1. Select **Manage** > **Policies & Rules** from the left sidebar.
2. Select **Secret Rules**.
3. Click **Create Secret Rules**.

   ![Create secret rules](../../images/add-secret-rule.png)
4. Enter the unique **Rule Identifier** and **Rule Name**.
5. Enter the **Description** of the secret rule.
6. Enter the regex for the secret rule in **Detection Rule**.
7. Enter keywords for pre-regex check filtering as comma separated values in **Keywords**.
8. Optionally, enter the minimum Shannon entropy a regex group must have to be considered in **Entropy**.
9. Optionally, add validation details to validate the secret:

   * **Validation URL**: Enter the URL for validation.
   * **Validation Method**: Choose between GET and POST methods.
   * **Success Response Codes**: Enter valid response codes (For example, `200` for HTTP Status OK)
   * **Failure Response Codes**: Enter invalid response codes (For example, `401` for HTTP Status Unauthorized)
   * **Authorization Details**: You can choose between Authorization Header, Bearer Token, and Basic Authentication.
10. Select **Propagate this rule to all child namespaces** to apply the secret rule to all child namespaces.
11. Click **Add Rule**.

### Create secret rules from the command line

For example, consider a token “demo\_value123” can be described using a regular expression. Here is an example of the rule specification:

```
"meta": {
    "name": "Demo Token"
},
"spec": {
    "disabled": false,
    "keywords": [
        "demo_"
    ],
    "regex": "demo_[0-9a-zA-Z]{20}",
    "rule_id": "demo-rule"
}
```

Use the following command from the CLI to create this custom rule.

```
$ endorctl api create -r SecretRule -n demo  \
> --data '{
> "meta": {
>     "name": "Demo Token"
> },
> "spec": {
>     "disabled": false,
>     "keywords": [
>         "demo_"
>     ],
>     "regex": "demo_[0-9a-zA-Z]{20}",
>     "rule_id": "demo-rule"
> }
> }'
INFO: Initiating host-check ...
INFO: Host-check complete
{
  "meta": {
    "create_time": "2023-09-27T17:08:18.436936Z",
    "kind": "SecretRule",
    "name": "Demo Token",
    "update_time": "2023-09-27T17:08:18.436936Z",
    "upsert_time": "2023-09-27T17:08:18.436936Z",
    "version": "v1"
  },
  "spec": {
    "disabled": false,
    "keywords": [
      "demo_"
    ],
    "regex": "demo_[0-9a-zA-Z]{20}",
    "rule_id": "demo-rule"
  },
  "tenant_meta": {
    "namespace": "demo"
  },
  "uuid": "65146182aaeeffbaf5b6b553"
}
```

After the rule is created, the system uses this rule to detect this category of secrets.

If you can validate the secret using an HTTP request, then you can also add [validation](#validator) to this rule. See the following example for creating a validation rule for a demo\_test123 token.

```
curl -H "Authorization: Bearer "demo_test123" https://api.testserver.com/user
```

Then the validation specification can be:

```
"validation": {
    "name": "Demo secrets validator",
    "http_request": {
        "header": [
            {
                "key": "Bearer",
                "value": "{{.AuthzValue}}",
                "authz": true
            }
        ],
        "method": "GET",
        "uri": "https://api.testserver.com/user"
    },
    "http_response": {
        "failed_auth_codes": [
            401
        ],
        "successful_auth_codes": [
            200
        ]
    }
}
```

#### Validator

You can use a validator to check if a discovered secret is valid or not. The Endor Labs system rules for secrets include the necessary validator. When you validate a secret, the finding for that secret is categorized as critical, ensuring it receives higher priority compared to others.

When defining a custom rule, you can add your own validator from the command line or from the user interface. The system uses this information to send an HTTP request such as a GET or POST to the address specified by the public service for the detected secret.

For example, when a GitHub Personal Access Token named “ghp\_endor123” is detected, the system sends the following HTTP request to GitHub’s address:

```
curl -H "Authorization: Token "ghp_endor123" https://api.github.com/user
```

The authentication codes defined by the service are used to mark the secrets as valid or invalid.

The validation portion of the secret rule contains the following fields:

| Field | Description |
| --- | --- |
| name | The name of the validator |
| http\_request.uri | The address where the HTTP request should be sent |
| http\_request.method | The HTTP method to be used (GET or POST) |
| http\_request.header.(key, val) | A set of key/value pairs that are added to the HTTP header. See [HTTP Request Header](#http-request-header) |
| http\_response.successful\_auth\_codes | The set of HTTP response codes that should be used to tag a secret as valid. For example, `http.StatusOK (200)` |
| http\_response.failed\_auth\_codes | The set of HTTP response codes that should be used to tag a secret as invalid. For example, `http.StatusUnauthorized (401)` |

#### HTTP request header

HTTP request header is a set of key-value pairs that should be added to the header.

```
{
    "key": "Content-Type",
    "value": "application/json"
}
```

There are cases where one needs to use a value on runtime and substitute a pattern. For example, the secret itself that needs to be substituted is one such case. This is achieved by declaring a value using the `{{.Value}}` pattern.

For the HTTP header section that includes the secret, the block looks like the following snippet.

```
{
    "key": "Token",
    "value": "{{.AuthzValue}}",
    "authz": true,
}
```

In this case, the scanner replaces the candidate secret that was detected and adds it to the HTTP request header in place of `{{.AuthzValue}}`.

The following table describes a special case where the key-value pair is marked with the `authz` flag and is used to craft the “Authorization” part of the header, where three options are supported.

| Key | Header |
| --- | --- |
| Basic | ‘Authorization: `Basic "hash{{.AuthzValue}}"’`’ |
| Bearer | ‘Authorization: `Bearer {{.AuthzValue}}`’ |
| Token | ‘Authorization: `Token {{.AuthzValue}}`’ |

## Manage secret rules

1. Select **Manage** > **Policies & Rules** from the left sidebar.
2. Select **Secret Rules**.

   The list of all secret rules appears.
   ![Secret rules](../../images/secret-rules.png)
3. Select the rule for which you want to view the details.

   The rule details appear in the right sidebar.

   ![Secret rule details](../../images/secret-rule-details.png)

### Clone a secret rule

Click the three vertical dots on the right side of the rule and select **Clone Rule**.

The cloned rule appears in the list of secret rules and you can edit it.

### Edit a secret rule

Click the three vertical dots on the right side of the rule and select **Edit Rule**.

You can only edit the custom rules that you created or the system rules that you cloned.

### Fetch secret rules with endorctl

To fetch the Endor Labs secret scanning rules from the command line type the following commands:

```
endorctl api list -r SecretRule -n <your-namespace>
```

For example, to see the rule for the GitHub Personal Access Token, you could search by the name `GitHub Personal Access Token` or by the rule-id `github-pat`:

```
endorctl api get -r SecretRule -n <your-namespace> --name "GitHub Personal Access Token"
endorctl api list -r SecretRule -n <your-namespace> --filter=spec.rule_id==github-pat
```

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
