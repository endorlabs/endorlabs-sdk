---
name: endor-troubleshoot-sdk
description: Debug Endor Labs SDK errors, API failures, and test issues. Use when
  validating SDK behavior against endorctl or contracts, 404 after traverse, list
  ServerError at wrong namespace, update_mask validation failures, namespace mismatches,
  or unexpected test skips.
---

# Troubleshoot SDK Issues

Systematic workflow for diagnosing whether the SDK, `endorctl`, and documented
contracts agree — before changing client code.

## Evidence vs inference

When explaining root cause to the user:

- **Evidence-backed** — cite live API rows, `endorctl` output, workflow JSON under `.endorlabs-context/workspace/`, or normative text in `contracts/` / this skill.
- **Inferred** — heuristic scan pairing, partial hydration, or backend-behavior guesses without a reproducing call. Label **Inferred:** and say what to fetch next.

Deep triangulation playbook: [validation-reference.md](validation-reference.md). Repo clone only: `docs/contributing/troubleshooting.md`.

## Workflow

1. **Document** — capture the task, context, approach, and full error (including stack trace and `response.text`). Persist triage notes, repro scripts, and JSON exports under `.endorlabs-context/workspace/runs/scratch/` (see [workspace-layout](../../rules/endor-workspace-layout.md)); For CLI → library → script escalation, see [workflow-composition](../../rules/endor-workflow-composition.md).
2. **Research** — search codebase, `contracts/`, and API spec. Local spec: `.endorlabs-context/platform/openapi/openapiv2.swagger.json`; local user docs: `.endorlabs-context/platform/user-docs/`. Online fallback: <https://api.endorlabs.com/download/openapiv2.swagger.json>.
3. **Investigate** — replay the same call with `endorctl` (same resource, namespace, filter, traverse); compare outcomes using [validation-reference.md](validation-reference.md).
4. **Resolve** — fix usage, scope, model-sync, or SDK bug; document what evidence changed.

## Common validation traps

### 404 Not Found after `list(traverse=True)`

**Validate:** Does `endorctl api get` with the **owning** namespace succeed?

**Fix:** Pass the **resource object** instead of UUID-only — the SDK uses `tenant_meta.namespace`:

```python
client.Project.delete(target)  # correct
client.Project.delete(target.uuid)  # may 404
```

### List `ServerError` at tenant root

**Validate:** Does `endorctl api list` at the same namespace show the same error?

**If yes:** Scope issue — list from a child namespace or project namespace. Mask alone does not fix backend list failures.

**If endorctl 200 but SDK parse fails:** **endor-model-sync-drift**.

### Path namespace vs body UUID mismatch

**Validate:** Path namespace matches the resource's `tenant_meta.namespace`, not a parent.

```python
namespace = resource.tenant_meta.namespace
```

### `update_mask` validation errors

`update(uuid, payload=...)` requires a non-empty `update_mask` with mutable paths. Resource-instance + field kwargs derive the mask automatically:

```python
client.Namespace.update(ns.uuid, payload=updated_payload, update_mask="meta.description")
client.Namespace.update(ns, meta_description="new description")
```

### List field mask (dict rows) vs partial **model** responses

**Masked list (non-empty `mask`):** dict wire rows — use `isinstance(row, dict)` or omit `mask` for models.

**Unmasked list:** typed models; some fields may be `None` when omitted on the wire (`Finding.context`, `Project.spec.platform_source`, `BaseMeta.name`).

### Tenant-context read-only resources

`authentication_log`, `endor_license`, and `policy_template` — `list`/`get` only; no `create`/`update`/`delete` on the Client facade.

## Test debugging

| Skip / symptom | Validate with endorctl | Likely cause |
|----------------|------------------------|--------------|
| 403 Forbidden | Same list/get in namespace | Permissions or system resource |
| "No resources in scope" | `endorctl api list -r <Resource> -n <namespace>` | Empty namespace or wrong scope |
| Validation error on update | Compare `update_mask` to `get_mutable_fields_cls()` | Immutable field in mask |

```bash
endorctl api list -r Finding -n <namespace> --traverse
endorctl api get -r Project -n <namespace> --uuid <project-uuid>
```

Integration-test cleanup and outcome matrix: [validation-reference.md](validation-reference.md).
