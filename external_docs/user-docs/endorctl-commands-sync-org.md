---
url: https://docs.endorlabs.com/endorctl/commands/sync-org/
title: sync-org | Endor Labs Docs
downloaded: 2025-10-23 23:25:17
---

sync-org | Endor Labs Docs



* Type to search...
* ---

[Print entire section](/endorctl/commands/sync-org/_print.html)



# sync-org

Use the sync-org command to sync all projects in a GitHub organization to Endor Labs.

Use the `endorctl sync-org` command to create projects for all the unscanned repositories in your GitHub organization. This does not automatically scan the projects. It creates projects in Endor Labs, measures scan coverage across a GitHub organization, and gives you visibility into your source control repository.

## Usage

To sync your GitHub organization to Endor Labs:

* Export a GitHub token that can read all projects in your GitHub organization. To run the sync-org command you need at least `repo` and `read:org permissions`.

  ```
  export GITHUB_TOKEN=<insert-github-token>
  ```
* Run the sync-org command. By default, archived repositories are skipped.

  ```
  endorctl sync-org --name=endorlabs
  ```

## Options

The `endorctl sync-org` command uses the following flags and environment variables:

| Flag | Environment Variable | Type | Description |
| --- | --- | --- | --- |
| `archived` | `ENDOR_SYNC_ORG_ARCHIVED` | boolean (default:false) | Include archived repositories. |
| `github-api-url` | `ENDOR_SYNC_ORG_GITHUB_API_URL` | string | Set the URL for API requests to GitHub Enterprise Cloud or GitHub Enterprise Server (default: `https://api.github.com/`). |
| `name` | `ENDOR_SYNC_ORG_NAME` | string | Set the full name of the organization. For example: `endorlabs`. |
| `platform-source` | `ENDOR_SYNC_ORG_PLATFORM_SOURCE` | string | Set the platform source (default: `github`). |
| `uuid` | `ENDOR_SYNC_ORG_UUID` | string | Set the UUID of the GitHub installation. |

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
