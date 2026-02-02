"""Test cases for analysis module (experimental).

Tests FindingDatabase schema/insert/query and optionally FindingDataLoader
with mocked API to exercise load/save paths without live API.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

from endorlabs.analysis import FindingDatabase, FindingDataLoader


class TestFindingDatabase:
    """Tests for FindingDatabase schema and CRUD."""

    def test_create_schema_and_insert_finding(self, tmp_path: Path) -> None:
        db_path = tmp_path / "test.db"
        db = FindingDatabase(str(db_path))
        db.insert_finding(
            uuid="f1",
            rule_id="r1",
            rule_name="Rule One",
            file_path="src/foo.py",
            line_number=10,
            summary="Test",
        )
        rows = db.execute_query("SELECT uuid, rule_id, file_path FROM findings")
        assert len(rows) == 1
        assert rows[0]["uuid"] == "f1"
        assert rows[0]["rule_id"] == "r1"
        assert rows[0]["file_path"] == "src/foo.py"
        db.close()

    def test_insert_rule_and_get_rule_by_id(self, tmp_path: Path) -> None:
        db_path = tmp_path / "test.db"
        db = FindingDatabase(str(db_path))
        db.insert_rule(
            uuid="ru1",
            rule_id="rule-one",
            rule_name="Rule One",
            language="python",
        )
        row = db.get_rule_by_id("rule-one")
        assert row is not None
        assert row["rule_id"] == "rule-one"
        assert row["rule_name"] == "Rule One"
        db.close()

    def test_get_findings_by_rule(self, tmp_path: Path) -> None:
        db_path = tmp_path / "test.db"
        db = FindingDatabase(str(db_path))
        db.insert_finding(
            uuid="f1",
            rule_id="r1",
            label="TP",
        )
        db.insert_finding(
            uuid="f2",
            rule_id="r1",
            label="FP",
        )
        rows = db.get_findings_by_rule("r1")
        assert len(rows) == 2
        rows_tp = db.get_findings_by_rule("r1", label="TP")
        assert len(rows_tp) == 1
        assert rows_tp[0]["label"] == "TP"
        db.close()

    def test_context_manager(self, tmp_path: Path) -> None:
        db_path = tmp_path / "test.db"
        with FindingDatabase(str(db_path)) as db:
            assert db.conn is not None
            db.insert_finding(uuid="f1", rule_id="r1")
        assert db.conn is None


class TestFindingDataLoader:
    """Tests for FindingDataLoader with mocked API."""

    def test_load_findings_from_api_empty(self, tmp_path: Path) -> None:
        db_path = tmp_path / "loader.db"
        loader = FindingDataLoader(str(db_path))
        client = MagicMock()
        with patch(
            "endorlabs.resources.finding.list_findings",
            return_value=[],
        ):
            findings = loader.load_findings_from_api(client, "tenant.ns")
        assert findings == []
        loader.db.close()

    def test_load_rules_from_api_empty(self, tmp_path: Path) -> None:
        db_path = tmp_path / "loader.db"
        loader = FindingDataLoader(str(db_path))
        client = MagicMock()
        with patch(
            "endorlabs.resources.semgrep_rule.list_semgrep_rules",
            return_value=[],
        ):
            rules = loader.load_rules_from_api(client, "tenant.ns")
        assert rules == []
        loader.db.close()
