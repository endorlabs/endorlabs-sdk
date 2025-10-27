---
url: https://docs.endorlabs.com/managing-sboms/exporting-sboms/
title: Export SBOMs and VEX | Endor Labs Docs
downloaded: 2025-10-27 12:59:32
---

Export SBOMs and VEX | Endor Labs Docs



* Type to search...
* ---

[Print entire section](/managing-sboms/exporting-sboms/_print.html)



# Export SBOMs and VEX

Learn more about software transparency and the role of SBOMs in your organization.

To export an SBOM you must first perform a successful `endorctl` scan. If you haven’t successfully scanned a project see [quick start](../../getting-started/quickstart/) for more information.

Endor Labs supports export in the [CycloneDX format](https://cyclonedx.org/docs/1.6/json/#bomFormat), [VEX](https://cyclonedx.org/capabilities/vex/) format, and [SPDX format](https://spdx.github.io/spdx-spec/v2.3/file-information/).

## Export an SBOM through the Endor Labs user interface

When you export an SBOM at the project level, it includes all the packages in the project and all the package versions. This allows you to combine the SBOMs of multiple packages and versions into a single SBOM. A consolidated SBOM for the project enables quick identification and assessment of vulnerabilities across all software components.

### Export an SBOM as CycloneDX

You can export SBOM of the project in the CycloneDX format.

1. Select **Projects** from the left sidebar.
2. Select the project for which to create an SBOM.
3. Click **Export SBOM** in the top right-hand corner.

   ![sbom in CycloneDX](../../images/cyclonedx-sbom.png)
4. Select **CycloneDX**.
5. Choose whether to export as an application or a library.

   If you choose to export as an application, enter an application name.
6. Select the output format and type of SBOM you would like to generate in **FILE FORMAT**.
7. Click **Add More** to select the packages and package versions you want to include in the SBOM.

   If you do not select specific packages, the SBOM will include information for all packages and package versions.

   ![Add more](../../images/cyclonedx-addmore.png)

   You can filter by ecosystem to select the type of packages to include in the SBOM.

   ![Add more ecosystem](../../images/cyclonedx-addmore-ecosystem.png)

   You can also search and select multiple package versions of the same package.

   ![Add more version](../../images/cyclonedx-addmore-version.png)
8. Click **Export SBOM**.

   A file containing the SBOM will download from your browser.

### Export an SBOM as SPDX

You can export SBOM of the project in the SPDX format.

1. Select **Projects** from the left sidebar.
2. Select the project for which to create an SBOM.
3. Click **Export SBOM** in the top right-hand corner.

   ![sbom as SPDX](../../images/spdx-sbom.png)
4. Select **SPDX**.
5. Enter the name of your application in **Application Name**.
6. Select the output format and type of SBOM you would like to generate in **File Format**.
7. Click **Add More** to select the packages and package versions you want to include in the SBOM.

   If you do not select specific packages, the SBOM will include information for all packages and package versions.

   ![Select packages](../../images/spdx-addmore.png)

   You can filter by ecosystem to select the type of packages to include in the SBOM.

   ![Select packages](../../images/spdx-addmore-ecosystem.png)

   You can also search and select multiple package versions of the same package.

   ![Select packages](../../images/spdx-addmore-version.png)
8. Click **Export SBOM**.

   A file containing the SBOM will download from your browser.

## Export SBOM through endorctl

You can use the following options with the SBOM export command.

| Flag | Environment Variable | Type | Description |
| --- | --- | --- | --- |
| `component-type` | `ENDOR_SBOM_COMPONENT_TYPE` | string | Set the SBOM component type to `application`, or `library` (default `application`). |
| `output-format` | `ENDOR_SBOM_OUTPUT_FORMAT` | string | Set the SBOM format to `json` or `xml` for CycloneDX, and `json` or `tag-value` for SPDX (`json` is the default for both). |
| `package-version-name` | `ENDOR_SBOM_PACKAGE_VERSION_NAME` | string | Name of the package version for which you want to generate an SBOM. |
| `package-version-uuid` | `ENDOR_SBOM_PACKAGE_VERSION_UUID` | string | The UUID of the package version for which you want to generate an SBOM. |
| `timeout` | `ENDOR_SBOM_TIMEOUT` | string | Set the timeout for the SBOM generation (default `30s`). Use the Go duration format, for example, 30s, 1m. |
| `with-vex` | `ENDOR_SBOM_WITH_VEX` | boolean | Generate the corresponding VEX document along with the SBOM. |
| `project-uuid` | `ENDOR_SBOM_PROJECT_UUID` | string | The UUID of the project for which you want to generate an SBOM. |
| `project-name` | `ENDOR_SBOM_PROJECT_NAME` | string | Name of the project for which you want to generate an SBOM. |
| `app-name` | `ENDOR_SBOM_APP_NAME` | string | Name of the application or the library. Required for multi-package SBOM export. |
| `package-version-uuids` | `ENDOR_SBOM_PACKAGE_VERSION_UUIDS` | string | The list of package version UUIDs to export an SBOM. |

You can export an SBOM in CycloneDX or SPDX format using endorctl, for a single package version or across multiple package versions.

* **Export SBOM with a single package version**
* **Export SBOM in CycloneDX format with multiple package versions**
* **Export SBOM in SPDX format with multiple package versions**

To export an SBOM you will need the package version name for which you’d like to create an SBOM or its UUID. You can also export an SBOM with multiple package versions. To export an SBOM with multiple package versions, you need the package version UUIDs or the project name.

Pass the package name or UUID to the command `endorctl sbom export` using the `--package-version-name` or `--uuid` flags.

To export an SBOM, you must first retrieve the package version name through the API.

You can easily export a reference package name and the scanned version you’d like to export as environment variables.

```
export PACKAGE_NAME=<insert_package_name>
export VERSION=<insert_package_version>
```

Then query the API for the package version name and set this as an environment variable:

```
export PACKAGE_VERSION_NAME=$(endorctl api list -r PackageVersion --filter "meta.name matches $PACKAGE_NAME AND meta.name matches $VERSION" --field-mask=meta.name | jq -r ".list.objects[].meta.name")
```

Export an SBOM in the CycloneDX format through endorctl using the package version name.

```
endorctl sbom export --package-version-name=$PACKAGE_VERSION_NAME >> cyclonedx.json
```

Export an SBOM in the SPDX format through endorctl using the package version name.

```
endorctl sbom export --format spdx --package-version-name=$PACKAGE_VERSION_NAME >> spdx.json
```

To export multiple package versions in an SBOM, you need the UUIDs of package versions, or the name or UUID of the project to which the package versions belong.

To create an SBOM based on project details, either provide the project UUID with the `--project-uuid` flag or the project name with the `--project-name` flag. You also need to provide a name for the package with the `--app-name` flag.

Run the command to create an SBOM with multiple package versions using the project UUID.

```
endorctl sbom export -n <Namespace> --project-uuid=<Project UUID> --app-name=<Application Name> >> <SBOM Name>.json
```

For example:

```
endorctl sbom export -n test --project-uuid=66e345c340669666c22979d6 --app-name=actions-hu/app-java-demo >> cyclonedx-sbom.json
```

Run the following commands to create an SBOM with multiple package versions with the project name.

1. Fetch the project name using the project’s UUID.

   ```
   endorctl api get -r Project --uuid <Project's UUID> -n <namesapce> |jq .meta.name
   ```
2. Run the following command and replace `<Project Name>` with the project name you retrieved in the previous step.

   ```
   endorctl sbom export -n <Namespace> --project-name=<Project Name> --app-name=<Application Name> >> <SBOM Name>.json
   ```

   For example:

   ```
   endorctl sbom export -n test --project-name=actions-hu/app-java-demo --app-name=actions-hu/app-java-demo >> cyclonedx-sbom.json
   ```

Generate an SBOM based on package version UUIDs, provide the package version UUIDs with the `--package-version-uuids` flag. You also need to provide a name for the package with the `--app-name` flag.

```
endorctl sbom export -n <Namespace> --package-version-uuids=<Package Version UUID 1>,<Package Version UUID 2>,... <Package Version UUID N> --app-name=<Application Name> >> <SBOM Name>.json
```

For example:

```
endorctl sbom export -n test --package-version-uuids=66e345c340669666c22979d6,89f456c340669666c229854a,43a56b1340669666c289d4a2 --app-name=actions-hu/app-java-demo >> spdx-sbom.json
```

To export multiple package versions in an SBOM, you need the UUIDs of package versions, or the name or UUID of the project to which the package versions belong.

To create an SBOM based on project details, either provide the project UUID with the `--project-uuid` flag or the project name with the `--project-name` flag. You also need to provide a name for the package with the `--app-name` flag.

Run the command to create an SBOM with multiple package versions using the project UUID.

```
endorctl sbom export --format spdx -n <Namespace> --project-uuid=<Project UUID> --app-name=<Application Name> >> <SBOM Name>.json
```

For example:

```
endorctl sbom export --format spdx -n test --project-uuid=66e345c340669666c22979d6 --app-name=actions-hu/app-java-demo >> spdx-sbom.json
```

Run the following commands to create an SBOM with multiple package versions with the project name.

1. Fetch the project name using the project’s UUID.

   ```
   endorctl api get -r Project --uuid <Project's UUID> -n <namesapce> |jq .meta.name
   ```
2. Run the following command and replace `<Project Name>` with the project name you retrieved in the previous step.

   ```
   endorctl sbom export --format spdx --output-format=<Format Type> -n <Namespace> --project-name=<Project Name> --app-name=<Application Name> >> <SBOM Name>.json
   ```

   For example:

   ```
   endorctl sbom export --format spdx --output-format=json -n test --project-name=actions-hu/app-java-demo --app-name=actions-hu/app-java-demo >> spdx-sbom.json
   ```

Generate an SBOM based on package version UUIDs, provide the package version UUIDs with the `--package-version-uuids` flag. You also need to provide a name for the package with the `--app-name` flag.

```
endorctl sbom export --format spdx --output-format=json  -n <Namespace> --package-version-uuids=<Package Version UUID 1>,<Package Version UUID 2>,... <Package Version UUID N> --app-name=<Application Name> >> <SBOM Name>.json
```

For example:

```
endorctl sbom export --format spdx --output-format=json -n test --package-version-uuids=66e345c340669666c22979d6,89f456c340669666c229854a,43a56b1340669666c289d4a2 --app-name=actions-hu/app-java-demo >> spdx-sbom.json
```

To export the CycloneDX SBOM as a library rather than an application use `--component-type=library`.

```
endorctl sbom export --component-type=library --package-version-name=$PACKAGE_VERSION_NAME >> cyclonedx.json
```

To export the CycloneDX SBOM in XML format rather than json use `--output-format` with the XML parameter.

```
endorctl sbom export --output-format=xml --package-version-name=$PACKAGE_VERSION_NAME >> cyclonedx.xml
```

To export a VEX document use the flag `--with-vex`

```
endorctl sbom export --with-vex
```

To export the SPDX SBOM using the tag-value format instead of json, use `--output-format=tag-value`.

```
endorctl sbom export --format spdx --output-format=tag-value --package-version-name=$PACKAGE_VERSION_NAME >> sbom-spdx.spdx
```

#### Note

endorctl generates SBOMs in the CycloneDX format by default.

## Endor Labs Export Formats

Endor Labs provides the following fields to map to the [NTIA minimum elements of an SBOM standard](https://www.ntia.gov/report/2021/minimum-elements-software-bill-materials-sbom).

### CycloneDX Format

Endor Labs supports export in the CycloneDX format.

The following table lists the mandatory and some optional fields in the SBOM file that Endor Labs exports.

| Field | Mandatory | Description |
| --- | --- | --- |
| `bomFormat` | true | Specifies the format of the SBOM. |
| `specVersion` | true | The version of the specification used (for example, “1.4”). |
| `serialNumber` | false | A unique identifier for the SBOM document. |
| `version` | true | The revision number of the SBOM. |
| `metadata` | false | Contains metadata about the SBOM and primary component. |
| `metadata.timestamp` | false | The date and time when the SBOM was generated. |
| `metadata.component` | false | Information about the main component described by the SBOM. |
| `metadata.component.bom-ref` | false | A reference identifier for the component within the BOM. |
| `metadata.component.type` | false | The type of the main component (for example, “application” or “library”). |
| `metadata.component.name` | false | The name of the main component. |
| `metadata.component.version` | false | The version of the main component. |
| `metadata.component.hashes` | false | Cryptographic hashes of the main component. |
| `metadata.component.purl` | false | The Package URL (purl) for the main component. |
| `metadata.supplier` | false | Information about the supplier of the software. |
| `metadata.supplier.name` | false | The name of the supplier. |
| `metadata.supplier.url` | false | URLs associated with the supplier. |
| `metadata.supplier.contact` | false | Contact information for the supplier. |
| `metadata.licenses` | false | License information for the main component. |
| `components` | true | List of software components included in the SBOM. |
| `components[].bom-ref` | false | A reference identifier for each component within the BOM. |
| `components[].type` | true | The type of each component (for example, “library”). |
| `components[].name` | true | The name of each component. |
| `components[].version` | false | The version of each component. |
| `components[].licenses` | false | License information for each component. |
| `components[].licenses[].license.name` | false | The name of the license. |
| `components[].purl` | false | The Package URL (purl) for each component. |
| `components[].externalReferences` | false | External references for components. |
| `components[].externalReferences[].url` | false | The URL of the external reference. |
| `components[].externalReferences[].type` | false | The type of the external reference (for example, “`vcs`”). |
| `dependencies` | false | Describes the relationships between components. |
| `dependencies[].ref` | false | Reference to a component in the dependency relationship. |
| `dependencies[].dependsOn` | false | List of components that this component depends on. |

### VEX Format

The following table lists the mandatory and some optional fields in the VEX file that Endor Labs exports.

| Field | Mandatory | Description |
| --- | --- | --- |
| `bomFormat` | true | Specifies the format of the VEX document. |
| `specVersion` | true | The version of the specification used. |
| `serialNumber` | true | A unique identifier for the VEX document. |
| `version` | true | The revision number of the VEX document. |
| `metadata` | true | Contains metadata about the VEX document and primary component. |
| `metadata.timestamp` | true | The date and time when the VEX document was generated. |
| `metadata.tools` | true | Information about tools used to generate the VEX document. |
| `metadata.tools.services` | true | List of services used in generating the VEX document. |
| `metadata.tools.services[].provider` | true | Information about the provider of the service. |
| `metadata.tools.services[].provider.name` | true | The name of the service provider. |
| `metadata.tools.services[].provider.url` | true | URLs associated with the service provider. |
| `metadata.tools.services[].name` | true | The name of the service. |
| `metadata.tools.services[].version` | true | The version of the service. |
| `metadata.tools.services[].description` | true | A description of the service. |
| `metadata.component` | true | Information about the main component described by the VEX document. |
| `metadata.component.bom-ref` | true | A reference identifier for the component within the VEX. |
| `metadata.component.type` | true | The type of the main component. |
| `metadata.component.name` | true | The name of the main component. |
| `metadata.component.version` | true | The version of the main component. |
| `metadata.component.hashes` | true | Cryptographic hashes of the main component. |
| `metadata.component.purl` | true | The Package URL (purl) for the main component. |
| `vulnerabilities` | true | List of vulnerabilities associated with the component. |
| `vulnerabilities[].id` | false | The identifier of the vulnerability. |
| `vulnerabilities[].references` | false | References related to the vulnerability. |
| `vulnerabilities[].references[].source.url` | false | URL of the reference source. |
| `vulnerabilities[].ratings` | false | Severity ratings for the vulnerability. |
| `vulnerabilities[].ratings[].score` | false | Numerical score of the severity. |
| `vulnerabilities[].ratings[].severity` | false | Textual representation of the severity. |
| `vulnerabilities[].ratings[].method` | false | The method used for rating (for example, “CVSSv3”). |
| `vulnerabilities[].ratings[].vector` | false | The vector string for the rating. |
| `vulnerabilities[].cwes` | false | Common Weakness Enumeration (CWE) identifiers. |
| `vulnerabilities[].description` | false | A description of the vulnerability. |
| `vulnerabilities[].detail` | false | Detailed information about the vulnerability. |
| `vulnerabilities[].recommendation` | false | Recommended actions to address the vulnerability. |
| `vulnerabilities[].advisories` | false | List of advisories related to the vulnerability. |
| `vulnerabilities[].advisories[].url` | false | URL of the advisory. |
| `vulnerabilities[].published` | false | The date when the vulnerability was published. |
| `vulnerabilities[].updated` | false | The date when the vulnerability information was last updated. |
| `vulnerabilities[].credits` | false | Credits for individuals or organizations related to the vulnerability. |
| `vulnerabilities[].credits.individuals` | false | List of individuals credited. |
| `vulnerabilities[].analysis` | false | Analysis of the vulnerability’s impact on the component. |
| `vulnerabilities[].analysis.state` | false | The state of the analysis (for example, `not_affected`). |
| `vulnerabilities[].analysis.justification` | false | Justification for the analysis state. |
| `vulnerabilities[].affects` | false | Information about which components are affected by the vulnerability. |
| `vulnerabilities[].affects[].ref` | false | Reference to the affected component. |

### SPDX Format

The following table lists the mandatory and some optional fields in the SPDX file that Endor Labs exports.

| Field | Mandatory | Description |
| --- | --- | --- |
| `spdxVersion` | true | Specifies the SPDX specification version used. |
| `dataLicense` | true | Specifies the data license for the SPDX document. |
| `SPDXID` | true | Unique identifier for the SPDX document. |
| `name` | true | Name of the SPDX document. |
| `documentNamespace` | false | Defines the namespace URI for the document. |
| `creationInfo` | true | Contains metadata about when and how the document was created. |
| `creationInfo.licenseListVersion` | false | Specifies the version of the SPDX license list used. |
| `creationInfo.creators[]` | true | List of entities that created the document (tool, organization, or person). |
| `creationInfo.created` | true | The date and time when the document was created. |
| `packages[]` | true | List of packages included in the SPDX document. |
| `packages[].name` | true | Name of the package. |
| `packages[].SPDXID` | true | Unique identifier for the package. |
| `packages[].versionInfo` | false | Version of the package, if known. |
| `packages[].supplier` | false | Information about the package supplier. |
| `packages[].downloadLocation` | true | Location from where the package can be downloaded. |
| `packages[].filesAnalyzed` | false | Indicates whether the files in the package were analyzed. |
| `packages[].licenseConcluded` | false | License the package is concluded to be under. |
| `packages[].licenseDeclared` | false | License declared by the package supplier. |
| `packages[].copyrightText` | false | Copyright statement for the package. |
| `packages[].externalRefs[]` | false | List of external references related to the package. |
| `packages[].externalRefs[].referenceCategory` | true | Category of the external reference. |
| `packages[].externalRefs[].referenceType` | false | Type of external reference (for example, `purl`). |
| `packages[].externalRefs[].referenceLocator` | true | Value used to locate the reference (for example, a Package URL). |

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
