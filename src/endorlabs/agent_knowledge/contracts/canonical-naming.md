---
id: canonical-naming
tags:
- naming
- facades
---

# Canonical naming

- Use `tenant.namespace.child` only; never UUIDs in namespace paths.
- Example: `tenant_meta_namespace="tenant.acme.backend"`.
- **`Client` facade attributes:** **PascalCase** matching `endorctl api … --resource <Kind>`
  (e.g. `client.Project`, `client.Finding`).
- Resource Python modules stay `snake_case` (`endorlabs.resources.project`).
- **Custom facades:** SDK-only helpers registered in `registry.py` (e.g. `ScanLogs` for log lines;
  `ScanLogRequest` is the endorctl-aligned resource kind).
