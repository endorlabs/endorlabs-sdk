---
name: endor-toolchain-catalog
description: 'Use when checking which toolchain versions and download URLs the platform

  stores, then picking pins for a local ScanProfile or registering a custom

  build tool. Not for scan-log selected_toolchains RCA.'
---

# Platform toolchain catalog (CSV)

Export the versions Endor Labs stores, then use the CSV to see what is available
and which provider URLs ship those archives. Register or attach them in a
ScanProfile per product docs:

- [Configure scan profile (UI)](https://docs.endorlabs.com/scan/scan-profiles/configure-scanprofile-ui/)
  — including [custom tool versions](https://docs.endorlabs.com/scan/scan-profiles/configure-scanprofile-ui/#configure-a-custom-version-for-a-tool)
- [Build tools / support matrix](https://docs.endorlabs.com/scan/scan-profiles/build-tools/)
- [scanprofile.yaml](https://docs.endorlabs.com/scan/scan-profiles/configure-scanprofile-yaml/)
- [ScanProfile API](https://docs.endorlabs.com/scan/scan-profiles/configure-scanprofile-api/)

```bash
uv run --env-file .env-admin python \
  sdk/skills/endor-toolchain-catalog/scripts/export_toolchain_catalog.py \
  -o .endorlabs/tasks/inventory/toolchain-catalog.csv
```

Default catalog namespace: `system` (privileged read). One CSV row per download URL.

## CSV columns — what to check

| Column | Use when checking the platform catalog |
|--------|----------------------------------------|
| `os` | Platform slice (`linux`, `darwin`). Cloud scans typically need `linux`. |
| `arch` | `amd64` or `arm64` for that OS. |
| `ecosystem` | Tool kind stored by the platform (`java`, `maven`, `golang`, …). Filter here to list available versions for one tool. |
| `name` | Exact version string Endor will install (what you pick in UI / put in the profile). |
| `relative_tool_chain_path` | Unpack path inside the archive (UI “advanced” / YAML field). |
| `sha256_sum` | Required checksum when registering a custom version. Blank ⇒ incomplete pin. |
| `url` | Download mirror Endor (or you) can fetch. Same `name` may appear on multiple rows (multiple mirrors). |

**Available versions for a tool:** unique `name` values where
`os` + `arch` + `ecosystem` match the target plane (e.g. `linux`/`amd64`/`maven`).

**Full URL set for a version:** all rows sharing the same
`os,arch,ecosystem,name` (and usually the same `sha256_sum` / path) — copy every
`url` into the ScanProfile `urls` list (or the UI URL field + mirrors).

## Provider hosts (where the full set lives)

Hosts seen on platform-stored URLs. Prefer an official provider host for that
ecosystem when registering a custom version; `storage.googleapis.com/falcon-toolchains/…`
is Endor’s mirror of the same artifact.

| Ecosystem (`ecosystem`) | Typical provider hosts (full/versioned archives) |
|-------------------------|--------------------------------------------------|
| `golang` | `go.dev` |
| `javascript` | `nodejs.org` |
| `maven` | `repo1.maven.org`, `archive.apache.org` (+ Endor GCS mirror) |
| `gradle` | `services.gradle.org` |
| `java` | `builds.openlogic.com`, `cdn.azul.com`, `download.oracle.com`, `corretto.aws`, `github.com` (+ Endor GCS) |
| `dotnet` | `builds.dotnet.microsoft.com`, `download.visualstudio.microsoft.com` |
| `dotnet-installer` | `raw.githubusercontent.com` (endorlabs install scripts) |
| `python` / `pnpm` / `yarn` / `scala` / `mirai` | `github.com` release assets |
| `rust` / `rustup` | `static.rust-lang.org` |
| `ruby` | `github.com`, `rubies.travis-ci.org`, `rvm.io` |
| `android-cmd-line-tools` | `dl.google.com` |
| `swift` | Endor GCS (`storage.googleapis.com`) |
| `php` / `composer` | Often version-only rows (empty `url`) — fill from the language/provider docs when customizing |

## Map a CSV pin → ScanProfile

UI custom version needs: **version** (`name`), **URL** (`url`), **SHA-256**
(`sha256_sum`), optional relative path — see
[configure a custom version](https://docs.endorlabs.com/scan/scan-profiles/configure-scanprofile-ui/#configure-a-custom-version-for-a-tool).

YAML / API: put the pin under `spec.toolchain_profile.os.<os>.arch.<arch>.…`
using the field for that `ecosystem`:

| `ecosystem` | Field under `os.<os>.arch.<arch>` |
|-------------|-----------------------------------|
| `java` | `java_tool_chain.version` |
| `maven` | `java_tool_chain.maven_version` |
| `gradle` | `java_tool_chain.gradle_version` |
| `golang` | `golang_tool_chain.version` |
| `python` | `python_tool_chain.version` |
| `javascript` | `javascript_tool_chain.nodejs_version` |
| `yarn` | `javascript_tool_chain.yarn_version` |
| `pnpm` | `javascript_tool_chain.pnpm_version` |
| `dotnet` | `dotnet_tool_chain.version` |
| `dotnet-installer` | `dotnet_tool_chain.dotnet_installer_version` |
| `php` | `php_tool_chain.version` |
| `composer` | `php_tool_chain.composer_version` |
| `ruby` | `ruby_tool_chain.version` |
| `rust` | `rust_tool_chain.version` |
| `rustup` | `rust_tool_chain.rustup_version` |
| `mirai` | `rust_tool_chain.mirai_version` |
| `scala` | `scala_tool_chain.version` |
| `swift` | `swift_tool_chain.version` |
| `android-cmd-line-tools` | `android_tool_chain.command_line_tools_version` |

Pin object fields: `name`, `relative_tool_chain_path`, `sha256_sum`, `urls` (all
CSV `url` values for that version).
