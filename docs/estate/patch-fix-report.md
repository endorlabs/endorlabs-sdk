# Patch-fix report

Findings fixable by a patch, aggregated by package name + current version — mirrors `export-version`'s row shape and sort order (`(package_name, current_version)`), sourced from `Finding` instead of `DependencyMetadata`.

## CLI

```bash
uv run --env-file .env endor-estate patch-fix-report --namespace example-tenant.child

uv run endor-estate patch-fix-report --namespace example-tenant.child \
  --gate fix-available --severity CRITICAL --severity HIGH -o patch_report.csv
```

Default `--gate` is `any`: the union of the Endor Patch catalog (`spec.fixing_patch.endor_patch_available`) and the fix-available tag (`FINDING_TAGS_FIX_AVAILABLE`), so patch-available vs patch-to-request can be sliced post-hoc from one export. Narrow with `--gate endor-patch` or `--gate fix-available`. In all modes, the row's target version comes from `spec.fixing_upgrades.upgrade_list` on the same Finding — no second resource fetch.

Output columns: `namespace, package_name, current_version, patch_version, finding_count, distinct_patch_version_count, distinct_upgrade_path_count, project_count`.

## Library

```python
from endorlabs.workflows.findings.patch_fix_report import build_patch_fix_report

result = build_patch_fix_report(client, "example-tenant.child", gate="fix-available")
result.table.rows  # rollup rows
```

## Notes

- A finding only produces a rollup row once the platform has computed an upgrade path (`fixing_upgrades.upgrade_list` populated) — findings tagged fix-available or Endor-patch-available without a computed path are excluded from the table (still counted in `signal_breakdown`).
- `endor_patch_available` skews toward ecosystems where Endor curates patches (e.g. Maven); expect few or zero Endor-patch rows for npm/PyPI-heavy estates. Use default `--gate any` (or `--gate fix-available`) for broader coverage.
