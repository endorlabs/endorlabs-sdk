# Risk-weighted version cardinality

Rank estate packages by main-context SCA/vulnerability finding risk; drill version cardinality for top N packages.

## CLI

```bash
uv run --env-file .env endor-estate pull --namespace tenant.example.child

uv run endor-estate analyze --namespace tenant.example.child \
  --only risk,viz \
  --top-n 20
```

Outputs:

- `intermediate-representation/risk_cardinality.json` (`endor.risk_weighted_cardinality.v1`)
- `viz/estate_dashboard.html` (Risk families tab)

## Library

```python
from endorlabs.workflows.estate import analyze_risk_cardinality_from_workspace
```

Reads `data/finding.jsonl` and `data/dependency_metadata.jsonl` — no live API on analyze.
