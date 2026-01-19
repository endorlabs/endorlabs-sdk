---
url: https://docs.endorlabs.com/rest-api/about/versions/
title: API Versions | Endor Labs Docs
downloaded: 2026-01-16 09:47:11
---

API Versions | Endor Labs Docs



* Type to search...

[Print entire section](/rest-api/about/versions/_print.html)



# API Versions

Learn how to specify which REST API version to use whenever you make a request to the Endor Labs REST API.

## About API versioning

The Endor Labs REST API is versioned. Any breaking changes will be released in a new API version.

New endpoints, fields, and enum values are backwards compatible within the same version.

For every new version of the API that is released, the major version is specified in the URL. For example, `https://api.endorlabs.com/v1/namespaces/my_namespace/projects` uses version 1 of the endpoint, per the **v1** path segment.

Each resources have their versions specified in the field **meta.version**. For example the following resource has version 1 per the **v1** value for the field **meta.version**.

```
{
  "meta": {
    "create_time": "2023-12-05T00:04:21.853Z",
    "kind": "Project",
    "name": "https://github.com/my_organization/my_repository.git",
    "update_time": "2024-05-01T16:50:03.830911988Z",
    "version": "v1"
  },
  "uuid": "656e69058032bf0abaaeb681"
}
```

When using the `endorctl` command-line tool to access the API, new endpoints, fields, or enum values are not available if your version of endorctl is older than the API version. Make sure to keep `endorctl` up-to-date to access the latest features and endpoints. For more information, see [Install and configure endorctl](https://docs.endorlabs.com/endorctl/install-and-configure/).

## Check latest API version using curl

To check the latest API version using curl, run the following command:

```
curl -s https://api.endorlabs.com/meta/version | jq .ClientVersion
```

### Example request using curl

```
curl -s https://api.endorlabs.com/meta/version | jq .ClientVersion
"v1.6.322"
```

## Check latest endorctl version

To get both the current and the latest version of `endorctl`, run the following command:

```
endorctl --version
```

In addition to your current version of `endorctl` you will also see a notification such as the following if a newer version of `endorctl` is available.

### Example request using endorctl

```
endorctl --version
endorctl version v1.6.293
A newer version of endorctl is available v1.6.317 - currently v1.6.293
```

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
