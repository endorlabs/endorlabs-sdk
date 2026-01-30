# Retrieving ScanResult and Findings

## Concepts

- **ScanResult**: Scan metadata, environment, runtime stats, policies triggered; `spec.findings` holds Finding UUIDs.
- **Finding**: Security findings; linked by `context.scan_uuid` and `spec.project_uuid`.
- **Relationship**: Project (meta.name = repo URL) → ScanResult (meta.parent_uuid = Project UUID) → Finding UUIDs in spec.findings.

Use **traverse** when namespace is unknown or you need to search across namespaces. Use **field-mask** (ListParameters.mask or --field-mask) for smaller responses.

## Workflow (one-line steps)

1. Get Project UUID by repository URL (filter on meta.name or spec.git; use traverse if namespace unknown).
2. List ScanResults by meta.parent_uuid == Project UUID; sort by meta.create_time desc; take first for "most recent."
3. Get Finding by UUID (or list findings filtered by spec.project_uuid / context.scan_uuid as needed).

Resources: `endor_cockpit.resources.finding`, `.scan_result`, `.project`; [conventions.md](../conventions.md) (traverse, mask); [reference/resources.md](../reference/resources.md).

Runnable patterns: `tests/`, `maneuvers/`; full platform workflows: [docs.endorlabs.com](https://docs.endorlabs.com/).
