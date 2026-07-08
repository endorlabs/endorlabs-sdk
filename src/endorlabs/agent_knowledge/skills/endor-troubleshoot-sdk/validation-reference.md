# SDK behavior validation reference

Companion to [SKILL.md](SKILL.md) for **triangulating** SDK behavior against
`endorctl`, shipped `contracts/`, and OpenAPI — not a catalog of platform bugs.

Use this when deciding whether a report is a client bug, wrong namespace scope,
backend behavior, or model-sync drift.

**Normative semantics:** `contracts/` shards in the wheel. Repo clone:
[`docs/contracts.md`](https://github.com/endorlabs/endorlabs-sdk/blob/main/docs/contracts.md). **Model shape drift:**
**endor-model-sync-drift** — not hand-edits under `src/endorlabs/generated/`.

---

## Triangulation workflow

1. **Capture the SDK call** — resource kind, `Client(tenant=…)`, list `namespace`,
   `filter`, `traverse`, `mask`, and the full exception (`type`, message,
   `response.text` when present).
2. **Replay with endorctl** — same resource (PascalCase), namespace, filter, and
   traverse. Do not change parameters between runs.
3. **Check contracts** — namespace scoping, list mask semantics, update_mask rules.
4. **Classify** using the matrix below before changing SDK code.

```bash
# Same scope as a failing SDK list
endorctl api list -r Finding -n <namespace> --traverse

# Same resource as a failing SDK get
endorctl api get -r Project -n <namespace> --uuid <uuid>
```

OpenAPI (after `init()`): `.endorlabs-context/platform/openapi/openapiv2.swagger.json`.

---

## Outcome matrix

| What you observe | Likely layer | Next step |
|------------------|--------------|-----------|
| SDK and endorctl both fail the same way | Platform or wrong scope | Narrow namespace; retry at child scope; cite error text as **evidence** |
| endorctl succeeds, SDK fails on parse | Model-sync / facade tolerance | **endor-model-sync-drift**; compare wire JSON to Pydantic model |
| endorctl succeeds, SDK fails on URL/namespace | SDK path construction | Inspect `tenant_meta.namespace` on resource objects; pass resource to `get`/`update`/`delete` |
| SDK returns empty list, endorctl has rows | Wrong list namespace | Resolve `Project` first; `namespace=project.namespace` (see `endor-namespace-scoping`) |
| Masked `list()` rows are `dict`, caller expects models | Documented contract | Non-empty `mask=` → dict rows; omit `mask` for typed models |
| pytest skip: "No resources in scope" | Test data / auth | `endorctl api list` in `ENDOR_NAMESPACE`; not necessarily an SDK defect |

---

## Scope checks (validate before filing SDK bugs)

### Namespace for project-scoped lists

`Client(tenant=<root>)` with default `traverse=False` lists **only that path
segment**. Project-scoped resources (`Finding`, `ScanResult`, `PackageVersion`, …)
usually live in **child** namespaces. Resolve `Project`, then pass
`namespace=project.namespace` or use `list_by_project` accessors.

### Acting on traversed rows

After `list(traverse=True)`, pass the **resource object** to `get`/`update`/`delete`
so the SDK uses `tenant_meta.namespace`. UUID-only calls may 404 when the client
default namespace differs from the owning namespace.

### Path namespace vs body UUID

For body-UUID operations (e.g. scan-log-request), the path namespace must be the
**owning** namespace of that resource. A parent namespace may error even with a valid
UUID — validate with endorctl using the owning namespace from the resource row.

### List errors at tenant root

Broad lists at tenant root may return server errors for some resource kinds, or
omit fields the full OpenAPI schema marks required. If endorctl shows the same
5xx, treat as platform/scope behavior and retry at a child namespace. If endorctl
returns 200 but SDK deserialization fails, treat as model-sync drift.

### List mask vs model leniency

- **Non-empty `mask`:** `list()` returns wire **dict** rows — not partial Pydantic models.
- **No effective mask:** rows are models; the SDK may allow `None` on select fields
  when the wire omits them (`Finding.context`, `Project.spec.platform_source`, …).

---

## Integration tests (maintainers)

When pytest skips or integration tests disagree with manual API use:

1. Run `endorctl api list -r <Resource> -n <namespace>` (PascalCase) with the same
   namespace as tests (`ENDOR_NAMESPACE` or default `auri`).
2. Run pytest **without** `--disable-warnings` to see skip vs SDK warning source.
3. Follow cleanup and CREATE/try/finally patterns in
   [`docs/contributing/integration-resource-tests.md`](https://github.com/endorlabs/endorlabs-sdk/blob/main/docs/contributing/integration-resource-tests.md).

**Leftover test resources** after interrupted runs — list with endorctl, delete only
rows matching test name/tag patterns (policies need both test tag and test-only name
prefix). Repo clone: [`docs/contributing/troubleshooting.md`](https://github.com/endorlabs/endorlabs-sdk/blob/main/docs/contributing/troubleshooting.md).

---

## References

- Skill entrypoint: [SKILL.md](SKILL.md)
- Contracts: `contracts/list-parameters.md`, `contracts/resource-discovery.md`
- Reference: `reference/filter-enum-snippets.md` (codegen filter enum literals)
- Contributor troubleshooting: `docs/contributing/troubleshooting.md` (repo clone only)
