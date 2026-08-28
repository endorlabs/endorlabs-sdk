# GitHub Actions scripts

Scripts invoked only from workflows or composite actions under `.github/`. Keep regen and pre-commit policy in [`devtools/`](../../devtools/README.md) (`codegen/`, `precommit/`, `ship/`).

| Script | Role |
| ------ | ---- |
| [`check_endorctl_version.py`](check_endorctl_version.py) | Compare published endorctl vs committed OpenAPI provenance (CI cron / release gates) |

Model-sync bot: [`.github/workflows/model-sync-dispatch.yml`](../workflows/model-sync-dispatch.yml).

Run locally the same way CI does, for example:

```bash
uv run python .github/scripts/check_endorctl_version.py
```
