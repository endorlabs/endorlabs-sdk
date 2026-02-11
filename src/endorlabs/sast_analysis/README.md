# Finding Correlation Analysis - Minimal API

**Experimental:** This feature may change; it is not covered by the same stability guarantees as the rest of the SDK.

Tools for loading findings/rules from API and querying via SQL.

## Usage

### Load Data from API

Demonstrates loading findings and Opengrep/Semgrep rules from the Endor API and persisting to SQLite.

```python
from endorlabs.sast_analysis import FindingDataLoader
from endorlabs.api_client import APIClient

client = APIClient()
loader = FindingDataLoader(".tmp/findings_correlation.db")

findings = loader.load_findings_from_api(client, "tenant.namespace")
loader.save_findings_to_db(findings)

rules = loader.load_rules_from_api(client, "tenant.namespace")
loader.save_rules_to_db(rules)
```

### Query with SQL

Demonstrates querying persisted findings and rules by rule ID and label.

```python
from endorlabs.sast_analysis import FindingDatabase

with FindingDatabase(".tmp/findings_correlation.db") as db:
    results = db.execute_query(
        "SELECT * FROM findings WHERE rule_id = ? AND label = ?",
        ("java-stack-trace-exposed", "FP"),
    )
    findings = db.get_findings_by_rule("java-stack-trace-exposed", label="FP")
    rule = db.get_rule_by_id("java-stack-trace-exposed")
```

## Database Schema

- `findings` - Finding data (uuid, rule_id, file_path, line_number, label, etc.)
- `rules` - Rule definitions (uuid, rule_id, yaml_content, rule_json, etc.)
- `rule_patterns` - Extracted rule patterns
- `ground_truth` - Ground truth labels (TP/FP/FN/TN)

## SQL Query Examples

The snippets above show typical usage. Adapt the SQL to your schema and labels; the `findings` and `rules` tables support standard SQL filters and joins.
