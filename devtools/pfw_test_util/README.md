# PFW test util

Maintainer helper to generate Package Firewall traffic for the known malware-marked
test package ``endor-firewall-test@1.0.0`` (npm + PyPI). Not shipped in the wheel.

## Prerequisites

- ``ENDOR_NAMESPACE`` (or ``-n``) — tenant/namespace path for factory URLs
- Firewall basic auth:
  - ``UV_INDEX_ENDOR_FIREWALL_USERNAME`` / ``UV_INDEX_ENDOR_FIREWALL_PASSWORD``, or
  - ``ENDOR_FIREWALL_USERNAME`` / ``ENDOR_FIREWALL_PASSWORD``
- Load via ``uv run --env-file .env`` (never commit credentials)

## Blast

```bash
uv run --env-file .env python devtools/pfw_test_util/blast_requests.py
uv run --env-file .env python devtools/pfw_test_util/blast_requests.py --include-controls
```

Expected for the **npm version** GET (`…/firewall/npm/endor-firewall-test/1.0.0`):
**HTTP 403** (policy BLOCK; writes `PackageFirewallLog`). Other npm/PyPI URLs are
observational (status printed; not required for exit 0). JSON summary defaults to
``.endorlabs-context/workspace/runs/pfw-test-util/``.

## Pair with log export

After blasting, dump full ``PackageFirewallLog`` rows:

```bash
uv run --env-file .env endor-log-export -n "$ENDOR_NAMESPACE" --source package-firewall --since <ISO> --until <ISO>
```
