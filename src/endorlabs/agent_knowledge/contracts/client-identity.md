---
id: client-identity
tags:
- auth
- transport
- headers
- hosting
---

# Client identity headers

Normative companion to [docs/contracts.md](https://github.com/endorlabs/endorlabs-sdk/blob/main/docs/contracts.md) § Client identity.
Hosts **SHALL** pass identity via `ClientIdentity` (or constructor kwargs) rather than inventing parallel header schemes on the SDK Client.

## Header grammar

```text
User-Agent: <product>/<version> […]
x-endor-caller: <product-plane>
x-endor-caller-version: <product-version>
x-endor-op-comment: <optional workflow or host comment>
```

Default SDK Client:

```text
User-Agent: endorlabs-sdk/<sdk_ver>
x-endor-caller: endorlabs-sdk
x-endor-caller-version: <sdk_ver>
```

## Rules

- Default `Client()` / `APIClient()` **SHALL** set branded `User-Agent` `endorlabs-sdk/<version>`.
- Default **SHALL** set `x-endor-caller: endorlabs-sdk` and `x-endor-caller-version: <sdk_ver>`.
- `op_comment` **SHALL** map to `x-endor-op-comment` when provided; **MUST NOT** contain `service/endorctl`.
- Callers **MUST NOT** forge `endorctl` as `x-endor-caller`.
- Injected `http_client` headers: SDK **SHALL** fill missing identity keys only; **MUST NOT** overwrite host-provided `User-Agent` / `x-endor-caller*`.
- Other product planes **SHALL** use `ClientIdentity.custom(...)` (or construct `ClientIdentity` directly) — the SDK does not prescribe host-specific factories.

## Factories

| Factory | Effect |
| ------- | ------ |
| `ClientIdentity.sdk()` | Default SDK plane |
| `ClientIdentity.workflow("endor-reports")` | SDK plane + `x-endor-op-comment: endor-reports/<ver>` |
| `ClientIdentity.custom(caller=…, caller_version=…)` | Host-supplied plane |

```python
from endorlabs import Client, ClientIdentity

client = Client(
    tenant="example-tenant",
    identity=ClientIdentity.workflow("endor-reports"),
)
```
