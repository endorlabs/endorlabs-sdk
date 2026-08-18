# Patch-fix report

Findings fixable by a patch, aggregated by package name + current version — mirrors `export-version`'s row shape and sort order (`(package_name, current_version)`), sourced from `Finding` instead of `DependencyMetadata`.

## CLI

```bash
uv run --env-file .env endor-estate patch-fix-report --namespace example-tenant.child

uv run endor-estate patch-fix-report --namespace example-tenant.child \
  --gate fix-available --severity CRITICAL --severity HIGH -o patch_report.csv
```

Default `--gate` is `any`: the union of the Endor Patch catalog (`spec.fixing_patch.endor_patch_available`) and the fix-available tag (`FINDING_TAGS_FIX_AVAILABLE`), so patch-available vs patch-to-request can be sliced post-hoc from one export. Narrow with `--gate endor-patch` or `--gate fix-available`. Rows group on `spec.target_dependency_package_name` + `target_dependency_version` (same grain as the Endor Patches dashboard).

Output columns: `namespace, package_name, current_version, patch_version, finding_count, distinct_patch_version_count, distinct_upgrade_path_count, project_count`.

## Library

```python
from endorlabs.workflows.findings.patch_fix_report import build_patch_fix_report

result = build_patch_fix_report(client, "example-tenant.child", gate="fix-available")
result.table.rows  # rollup rows
```

## Notes

- Rows group on the vulnerable library (`target_dependency_package_name` + `target_dependency_version`). Findings without a computed `fixing_upgrades.upgrade_list` are included when they have a target coordinate. `upgrade_list` is not the family key.
- Default pull is any reachability. The product Patches dashboard Available header is RF or PRF only — quote the filter before comparing counts.
- Finding lists exclude dismissed rows (`spec.dismiss != true`), matching the product findings UI exception filter.
- `endor_patch_available` skews toward ecosystems where Endor curates patches (e.g. Maven); expect few or zero Endor-patch rows for npm/PyPI-heavy estates. Use default `--gate any` (or `--gate fix-available`) for broader coverage.
