# Via shared-library exception (portable Rego example)

Except vulnerability findings whose leaf sits **under** a shared library in the
importer `dependency_graph` (the shared lib is on a path from the analyzed
package to the finding target).

## Files

- [`exception.rego`](exception.rego) — drop-in `POLICY_TYPE_EXCEPTION` rule

## Create

1. Set `input_package` to a coordinate substring of the shared library
   (example uses `com.example.shared:common-lib`).
2. Create an exception policy with:
   - **Query:** `data.via_shared_lib_exception.match_finding`
   - **Resource kinds:** `Finding`, `PackageVersion`
   - **Project scope:** consumer projects only (exclude the shared-lib producer)
   - **`disable=true`** until validate / rescan looks right
3. Enable and rescan when ready.

## Validate

```bash
endorctl validate policy \
  -p docs/guides/examples/via-shared-lib-exception/exception.rego \
  -q data.via_shared_lib_exception.match_finding \
  -r Finding,PackageVersion \
  -n <namespace> \
  --uuid <consumer-project-uuid> \
  -o json
```

Expect matches on leaves reachable under the shared lib, and **no** matches on
sibling transitive leaves that only enter through other paths.

## What not to use

| Approach | Why it fails for “via shared lib” |
|----------|-----------------------------------|
| BOM-presence (`some dep; graph[dep]; contains(dep, shared)`) | Shared lib **key exists** in the BOM → every transitive finding on that importer matches |
| SCA template **Dependency Name** = shared lib | Matches the **leaf** name, not an intermediate on the path |
| Blanket `FINDING_TAGS_TRANSITIVE` | Too broad |
| `FINDING_TAGS_PATH_EXTERNAL` alone | Polyrepo-only; does not fire in monorepos |
| Rego recursion / hand-unrolled hops | Recursion is rejected; hop caps are fragile vs `graph.reachable` |

## Notes

- Match key is `spec.target_dependency_package_name` (full graph node, e.g.
  `mvn://…@version`).
- Producer scope: set **project exclusions** (or tags) so the shared-lib project
  is out of scope; the Rego also skips when the importer PackageVersion name
  contains `input_package`.
- `graph.reachable` is an OPA builtin (allowed under Endor’s restricted
  capabilities). Prefer it over recursion or fixed-depth parent walks.
