---
url: https://docs.endorlabs.com/endorctl/commands/recommend/
title: recommend | Endor Labs Docs
downloaded: 2026-01-16 09:51:08
---

recommend | Endor Labs Docs



* Type to search...

[Print entire section](/endorctl/commands/recommend/_print.html)



# recommend

Use the recommend command to suggest dependency updates that address issues across your environment.

The command `endorctl recommend` fetches prioritized and recommended updates to address findings across your tenant, projects, or packages. All recommendations are based on the number of issues and complexity of a given upgrade.

## Usage

To recommend dependency updates across **all projects** in your namespace.

```
endorctl recommend dependency-upgrades
```

To recommend dependency updates across a **specific project** in your namespace:

1. Retrieve the UUID of your project. In the following example, we are retrieving the UUID of the project “<https://github.com/endorlabs/app-java-demo>” and saving it as an environment variable.

   ```
   UUID=$(endorctl api list -r Project --filter="meta.name matches https://github.com/endorlabs/app-java-demo" --field-mask=uuid | jq -r '.list.objects[].uuid')
   ```
2. Execute the recommend dependency-upgrades command.

   ```
   endorctl recommend dependency-upgrades --project-uuid=$UUID
   ```

To recommend dependency updates across a **specific package** in your namespace:

1. Retrieve the UUID of your package version. The following example looks for a project with the name “<https://github.com/endorlabs/app-java-demo>” and saves it as an environment variable.

   ```
   UUID=$(endorctl api list -r PackageVersion --filter="meta.name==mvn://com.endor.webapp:endor-java-webapp-demo@4.0-SNAPSHOT AND context.type==CONTEXT_TYPE_MAIN" --field-mask=uuid | jq -r '.list.objects[].uuid')
   ```
2. Execute the recommend dependency-upgrades command

   ```
   endorctl recommend dependency-upgrades --package-version-uuid=$UUID
   ```

## Options

The following flags and environment variables are available for the init command.

| Flag | Environment Variable | Type | Description |
| --- | --- | --- | --- |
| `package-version-uuid` | `ENDOR_RECOMMEND_PACKAGE_VERSION_UUID` | string | Set the UUID of the package version for which you want to recommend dependency upgrades. |
| `project-uuid` | `ENDOR_RECOMMEND_PROJECT_UUID` | string | Set to the UUID of the project to recommend dependency upgrades for. |
| `persist` | N/A | boolean (default:false) | Enable to persist upgrade recommendations to Endor Labs. |

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
