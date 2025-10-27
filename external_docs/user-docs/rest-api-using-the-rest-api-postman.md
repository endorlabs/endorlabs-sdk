---
url: https://docs.endorlabs.com/rest-api/using-the-rest-api/postman/
title: Postman | Endor Labs Docs
downloaded: 2025-10-27 13:00:22
---

Postman | Endor Labs Docs



* Type to search...
* ---

[Print entire section](/rest-api/using-the-rest-api/postman/_print.html)



# Postman

Learn how to use Endor Labs REST API with Postman

## Download Postman

Download Postman from [here](https://www.postman.com/downloads/). You can also use [Postman on the web](https://go.postman.co/home).

## Download the Endor Labs OpenAPI json

Go to [Endor Labs API Reference](https://docs.endorlabs.com/api/) and click the download button to download the Endor Labs OpenAPI json file, `openapi.json`.

## Import Endor Labs API json file in Postman

1. Open the Postman application.
2. Click **Import** and select the downloaded `openapi.json` file.
3. Select **OpenAPI 3.0 with Postman Collection** and click **Import**.

Endor REST API collection is added to your workspace. It may take a couple of minutes to load the entire collection because of the size.

## Configure Endor REST API collection

To use the Endor Labs APIs effectively with Postman you need to set the appropriate variables and configure authentication.

Before you proceed further, get your API Key and API Secret from the Endor Labs UI or endorctl. See [REST API authentication](../../authentication/#api-key-and-secret) for more information.

Endor Labs APIs require a bearer token, which is obtained from the `CreateAPIReq` endpoint. You need to add a pre-request script to obtain this token in the collection. The pre-request script runs when you initiate an API request and fetches the bearer token to be used in your API request.

The pre-request script also adds the following headers to the request:

* `'Content-Type': 'application/jsoncompact'`
* `'Accept-Encoding': 'gzip, deflate, br, zstd'`

We recommend that you create a new environment in Postman to run the APIs. You can save your variables in the environment and not the collection so that secrets are not exposed if you want to export and share the collection. You can also save the variables in the collection and modify the pre-request script to run the APIs without creating an environment.

### Create an environment in Postman

1. Click **Environments** in left navigation menu.
2. Click **Create New Environment**.
3. Enter a name for your environment.

### Configure variables in the environment

1. Click **Environments** in left navigation menu.
2. Select your Endor Labs API environment.
3. Create a variable with the name, `baseUrl` and enter `https://api.endorlabs.com` as the value.
4. Create the following variables with information that your API Key and API Secret.
   * `apiKey` : Your API key
   * `apiSecret` : Your API secret
5. Create a variable with the name, `bearerToken` and leave it as empty.
   ![Postman Variables](../../../images/PostmanEnvVars.png)
6. Save the changes.

### Configure authentication in the Endor REST API collection

1. Select Endor REST API collection and select the **Authorization** tab.
2. Select Bearer Token as the **Auth Type**.
3. Enter `{{bearerToken}}` in the **Bearer Token** field.
   ![Postman Authentication](../../../images/PostmanAuth.png)
4. Save the changes.

## Add the pre-request script to the Endor REST API collection

1. Select Endor REST API collection and select the **Scripts** tab.
2. Select **Pre-request**.
3. Enter the following JavaScript code as the pre-request script.

   ```
    const getTokenEndpoint = pm.environment.get("baseUrl") + '/v1/auth/api-key';
    const apiKey = pm.environment.get("apiKey");
    const apiSecret = pm.environment.get("apiSecret");
    const requestOptions = {
        method: 'POST',
        url: getTokenEndpoint,
        header: {
            'Content-Type': 'application/jsoncompact',
            'Accept-Encoding': 'gzip, deflate, br, zstd'
        },
        body: {
            mode: 'raw',
            raw: JSON.stringify({
                "key": apiKey,
                "secret": apiSecret
            })
        }
    };

    pm.sendRequest(requestOptions, function(err, response) {
        if (err) {
            console.log(err);
        } else {
            const jsonResponse = response.json();
            pm.environment.set("bearerToken", jsonResponse.token);

            // Set headers for the main request
            pm.request.headers.add({
                key: 'Content-Type',
                value: 'application/jsoncompact'
            });
            pm.request.headers.add({
                key: 'Accept-Encoding',
                value: 'gzip, deflate, br, zstd'
            });
        }
    });
   ```

   ![Postman Pre-request Script](../../../images/PostmanPreRequestScript.png)
4. Save the changes.

## Run Endor Labs API from Postman

1. Click **Collections** in the left navigation menu.
2. Expand Endor REST API collection and select the API that you want to run.
3. Configure the parameters in the **Params** tab.
4. Select the Endor Labs API environment from the Environments drop-down list.
5. Enter the name of your namespace in the `:tenant_meta.namespace` or `:target_namespace` if your API request applies to a namespace.
6. Click **Send** to send the API request.

## Customize and share Postman collection

You can configure parameters for multiple APIs according to your requirements, save the collection, and share the collection to quickly distribute API requests tailored for your organization.

For example, you might want to create multiple collections that apply to different namespaces and use different parameters for the namespaces. You can customize the parameters for each use case and export the collection for distribution in your development team.

## Endor Labs API with Postman: An Example

Consider a scenario where you need to fetch findings that have a CVSS score of more than 9.7.

You need to run the `ListFindings` API, which is available under `Endor REST API > V1 > Namespaces > {tenant_meta.namespace} > findings` in the collection.

In the **Params** tab, select only `list_parameters.filter` as the key and enter `spec.finding_metadata.vulnerability.spec.cvss_v3_severity.score > 9.7` as the value.

Replace `:tenant_meta.namespace` with the name of your namespace and click Send.

![Postman Example Request](../../../images/PostmanExampleRequest.png)

The response contains the list of findings that are vulnerabilities with CVSS score greater than 9.7.
![Postman Example Response](../../../images/PostmanExampleRsponse.png)

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
