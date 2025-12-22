# Finding Correlation Analysis - Simple API

Simple tools for loading findings/rules from API and querying via SQL.

## Usage

### Load Data from API

```python
from endor_cockpit.analysis import FindingDataLoader
from endor_cockpit.api_client import APIClient

client = APIClient()
loader = FindingDataLoader(".tmp/findings_correlation.db")

# Load from API
findings = loader.load_findings_from_api(client, "namespace")
loader.save_findings_to_db(findings)

rules = loader.load_rules_from_api(client, "namespace")
loader.save_rules_to_db(rules)
```

### Query with SQL

```python
from endor_cockpit.analysis import FindingDatabase

with FindingDatabase(".tmp/findings_correlation.db") as db:
    # Execute any SQL query
    results = db.execute_query(
        "SELECT * FROM findings WHERE rule_id = ? AND label = 'FP'",
        ("java-stack-trace-exposed",)
    )
    
    # Or use helper methods
    findings = db.get_findings_by_rule("java-stack-trace-exposed", label="FP")
    rule = db.get_rule_by_id("java-stack-trace-exposed")
```

## Database Schema

- `findings` - Finding data (uuid, rule_id, file_path, line_number, label, etc.)
- `rules` - Rule definitions (uuid, rule_id, yaml_content, rule_json, etc.)
- `rule_patterns` - Extracted rule patterns
- `ground_truth` - Ground truth labels (TP/FP/FN/TN)

## SQL Query Examples

See `maneuvers/example_sql_queries.py` for examples.

