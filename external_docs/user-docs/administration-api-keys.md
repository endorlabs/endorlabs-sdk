---
url: https://docs.endorlabs.com/administration/api-keys/
title: Manage API keys | Endor Labs Docs
downloaded: 2025-10-23 23:25:43
---

Manage API keys | Endor Labs Docs



* Type to search...
* ---

[Print entire section](/administration/api-keys/_print.html)



# Manage API keys

Manage your Endor Labs API keys for automation.

Use API keys to engage with Endor Labs services programmatically and enable any automation or integration with other systems in your environment. You can manage API keys with endorctl or from the Endor Labs user interface.

#### Tip

Instead of using API keys, you can use keyless authentication to authenticate with Endor Labs services. See [Keyless authentication](../../deployment/ci-scans/keyless-authentication/) for more information. Using keyless authentication eliminates the need to manage API keys and reduces the risk of API key compromise.

See [Best Practices: API key management](../../best-practices/manage-api-keys/) for more information on how to manage API keys.

## Create an API key

Create an API key to access Endor Labs services programmatically. You can create an API key through the Endor Labs user interface or using the Endor Labs API. You can create API keys with an expiry of up to one year from the Endor Labs user interface. You can use the API to generate API keys with longer expiry.

### Create an API key through the Endor Labs user interface

1. Select **Access Control** from the left sidebar.
2. Select **API Keys**.
3. Click **Generate API Key**.
4. Enter a name to identify the API key.
5. Select the [roles](../../administration/access-endorlabs/authorization-roles/) to apply to the API Key.

   You can choose from the following options:

   * Admin
   * Read-only
   * Code Scanner
   * Policy Editor
   * On-Prem Scheduler
6. Select the expiry of the API key.

   You can set the value as 30, 60, 90 days, or one year.
7. When you create an API key, it applies to the current namespace and all its child namespaces.

   To prevent the policy from being applied to any child namespace, click **Advanced** and deselect **Propagate this policy to all child namespaces**.

Using these credentials, you can configure Endor Labs scans in your CI/CD pipeline, or set up the Endor Labs Visual Studio Code extension. Each session initiated by the API key is valid up to four hours. See [scanning with endorctl](../../scan-with-endorlabs/) and [use Endor Labs extension in Visual Studio Code](../../deployment/ide/) for details.

### Create an API key through Endor Labs API

Run the following command to generate and API with the [create API Key endpoint](https://docs.endorlabs.com/api/#tag/APIKeyService/operation/APIKeyService_CreateAPIKey).

```
endorctl api create -r APIKey --data '{
  "meta": {
    "name": "API Key name",
    "description": "API key description"
  },
  "spec": {
    "permissions": {
      "roles": ["SYSTEM_ROLE_ADMIN"]
    },
    "expiration_time": "2025-05-01T00:00:00Z"
  }
}
```

You can use the following values in `spec.permissions.roles`:

* `SYSTEM_ROLE_ADMIN`
* `SYSTEM_ROLE_READ_ONLY`
* `SYSTEM_ROLE_POLICY_EDITOR`
* `SYSTEM_ROLE_CODE_SCANNER`

See [authorization roles](../../administration/access-endorlabs/authorization-roles/) for more information.

You can provide a specific value for the expiration date of the token. You can also set an expiry of over one year if required. You cannot edit the expiry after you create the API key. If you want to change the expiry, create a new API key with the required expiry date.

For example, you want to create an API key for a CI/CD pipeline that expires on March 31st 2026.

Run the following command to create an API key with `SYSTEM_ROLE_CODE_SCANNER` role so that you can use it for endorctl access from a CI/CD pipeline.

```
endorctl api create -r APIKey --data '{
  "meta": {
    "name": "CI/CD Access API key",
    "description": "API key for use within the CI/CD pipeline"
  },
  "spec": {
    "permissions": {
      "roles": ["SYSTEM_ROLE_CODE_SCANNER"]
    },
    "expiration_time": "2026-03-31T00:00:00Z"
  }
}'
```

```
{
  "meta": {
    "create_time": "2025-03-11T16:29:06.127975636Z",
    "created_by": "xxxxxx@endor.ai@google@api-key",
    "description": "API key for use within the CI/CD pipeline",
    "kind": "APIKey",
    "name": "CI/CD Access API key",
    "update_time": "2025-03-11T16:29:06.127975636Z",
    "updated_by": "xxxxxx@endor.ai@google@api-key",
    "version": "v1"
  },
  "spec": {
    "expiration_time": "2026-03-31T00:00:00Z",
    "issuing_user": {
      "meta": {
        "name": "xxxxxx@endor.ai@google@api-key"
      },
      "spec": {
        "email": "",
        "first_name": "",
        "last_login_time": "2025-03-11T16:29:06.114662511Z",
        "last_name": "",
        "user_name": ""
      }
    },
    "key": "endr+foo",
    "permissions": {
      "roles": [
        "SYSTEM_ROLE_CODE_SCANNER"
      ]
    },
    "secret": "endr+bar"
  },
  "tenant_meta": {
    "namespace": "demo"
  },
  "uuid": "67dx6x6x6f69xxx777a41cda"
}
```

## Delete an API Key

Delete the API keys that are expired or no longer in use. You can delete API keys using the Endor Labs user interface or using the Endor Labs API.

### Delete an API key through the Endor Labs user interface

1. Select **Access Control** from the left sidebar.
2. Select **API Keys**.
3. Find the API key that you want to delete and click the trash can icon at the far right.

### Delete an API key through Endor Labs API

Run the following command to delete an API key with the [delete API Key endpoint](https://docs.endorlabs.com/api/#tag/APIKeyService/operation/APIKeyService_DeleteAPIKey).

```
endorctl api delete -r=APIKey --name=<API_Key_Name>
```

The command fails if there are multiple API keys with the same name. You can use the UUID to delete a specific API key.

```
endorctl api delete -r=APIKey --uuid=<API_Key_UUID>
```

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
