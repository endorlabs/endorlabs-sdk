---
url: https://docs.endorlabs.com/rest-api/quickstart/
title: Quickstart | Endor Labs Docs
downloaded: 2026-01-26 10:06:11
---

Quickstart | Endor Labs Docs



* Type to search...

# Quickstart

Start using the Endor Labs REST API immediately.

This article describes how to quickly get started with the Endor Labs REST API using the Endor Labs command line tool `endorctl` or `curl`. For a more detailed guide, see [Getting started with the REST API](../using-the-rest-api/getting-started).

The following is an example request to get the number of findings in your namespace:

* endorctl
* curl

1. Run `endorctl init` and your browser window will open automatically. Select your authentication provider from the available options and complete the authentication process.

   You can also specify your supported authentication provider manually.

   ```
   endorctl init --auth-mode google
   ```
2. Use the `endorctl` command-line tool to make your request. Note that you do not have to provide the namespace or access token when using `endorctl` to access the Endor Labs REST API. For more information, see the [Endor Labs CLI documentation](../../endorctl/commands/api).

   ```
   endorctl api list -r Finding --count
   ```

1. Install `curl` if it isn’t already installed on your machine. To check if `curl` is installed, execute `curl --version` on the command line. If the output provides information about the version of `curl`, that means `curl` is installed. If you get a message similar to command not found: curl, you need to download and install curl. For more information, see the [curl project download page](https://curl.se/download.html).
2. Run `endorctl init` and your browser window will open automatically. Select your authentication provider from the available options and complete the authentication process.

   You can also specify your supported authentication provider manually.

   ```
   endorctl init --auth-mode google
   ```
3. Create an access token. The access token produced below has the same scopes/permissions as the API key created through `endorctl init`. **Treat your access token like a password**. For more information, see [Authentication](../authentication/).

   ```
   export ENDOR_TOKEN=$(endorctl auth --print-access-token)
   ```
4. Use the Curl command to make your request. Pass your token in an Authorization header. The following is an example request to get the number of findings in a given namespace. If needed, replace `$ENDOR_NAMESPACE` with the name of your namespace, or export it as a variable using `export ENDOR_NAMESPACE=<insert-namespace>`.

   ```
   curl --get \
     --header "Authorization: Bearer $ENDOR_TOKEN" \
     --header "Accept-Encoding: gzip" \
     --url "https://api.endorlabs.com/v1/namespaces/$ENDOR_NAMESPACE/findings?list_parameters.count=true"
   ```

For more information on HTTP headers and parameters, see [Getting Started](../using-the-rest-api/getting-started/).

For more examples of common use cases, see [Use cases](../using-the-rest-api/use-cases/).

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
