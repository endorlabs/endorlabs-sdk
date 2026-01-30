"""SQLite3 database schema and operations for finding correlation analysis.

This module provides database schema creation and basic operations for storing
findings, rules, and ground truth data.
"""

import json
import logging
import sqlite3
import types
from pathlib import Path
from typing import Any, Self

logger = logging.getLogger(__name__)


class FindingDatabase:
    """SQLite3 database for storing findings, rules, and analysis data."""

    def __init__(self, db_path: str) -> None:
        """Initialize database connection.

        Args:
            db_path: Path to SQLite3 database file

        """
        super().__init__()
        self.db_path = Path(db_path)
        self.conn: sqlite3.Connection | None = None
        self._create_schema()

    def _create_schema(self) -> None:
        """Create database schema if it doesn't exist."""
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row

        cursor = self.conn.cursor()

        # Findings table
        _ = cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS findings (
                uuid TEXT PRIMARY KEY,
                rule_id TEXT,
                rule_name TEXT,
                file_path TEXT,
                line_number INTEGER,
                code_snippet TEXT,
                finding_metadata TEXT,
                cwe TEXT,
                language TEXT,
                label TEXT,
                project_uuid TEXT,
                level TEXT,
                summary TEXT,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        # Rules table
        _ = cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS rules (
                uuid TEXT PRIMARY KEY,
                rule_id TEXT UNIQUE,
                rule_name TEXT,
                language TEXT,
                cwe TEXT,
                yaml_content TEXT,
                rule_json TEXT,
                disabled INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        # Rule patterns table
        _ = cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS rule_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rule_uuid TEXT,
                rule_id TEXT,
                pattern_type TEXT,
                pattern_text TEXT,
                pattern_json TEXT,
                FOREIGN KEY (rule_uuid) REFERENCES rules(uuid)
            )
            """
        )

        # Ground truth table
        _ = cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS ground_truth (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT,
                line_number INTEGER,
                cwe TEXT,
                label TEXT,
                language TEXT,
                UNIQUE(file_path, line_number, cwe, language)
            )
            """
        )

        # Create indexes
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_findings_rule_id ON findings(rule_id)",
            "CREATE INDEX IF NOT EXISTS idx_findings_file_path ON findings(file_path)",
            "CREATE INDEX IF NOT EXISTS idx_findings_cwe ON findings(cwe)",
            "CREATE INDEX IF NOT EXISTS idx_findings_label ON findings(label)",
            "CREATE INDEX IF NOT EXISTS idx_findings_language ON findings(language)",
            "CREATE INDEX IF NOT EXISTS idx_rules_rule_id ON rules(rule_id)",
            "CREATE INDEX IF NOT EXISTS idx_rules_language ON rules(language)",
            (
                "CREATE INDEX IF NOT EXISTS idx_rule_patterns_rule_uuid "
                "ON rule_patterns(rule_uuid)"
            ),
            (
                "CREATE INDEX IF NOT EXISTS idx_rule_patterns_rule_id "
                "ON rule_patterns(rule_id)"
            ),
            (
                "CREATE INDEX IF NOT EXISTS idx_rule_patterns_type "
                "ON rule_patterns(pattern_type)"
            ),
            (
                "CREATE INDEX IF NOT EXISTS idx_ground_truth_file "
                "ON ground_truth(file_path, line_number)"
            ),
            "CREATE INDEX IF NOT EXISTS idx_ground_truth_cwe ON ground_truth(cwe)",
        ]

        for index_sql in indexes:
            _ = cursor.execute(index_sql)

        _ = self.conn.commit()
        logger.info(f"Database schema created/verified at {self.db_path}")

    def insert_finding(
        self,
        uuid: str,
        rule_id: str | None = None,
        rule_name: str | None = None,
        file_path: str | None = None,
        line_number: int | None = None,
        code_snippet: str | None = None,
        finding_metadata: dict[str, Any] | None = None,
        cwe: str | None = None,
        language: str | None = None,
        label: str | None = None,
        project_uuid: str | None = None,
        level: str | None = None,
        summary: str | None = None,
        description: str | None = None,
    ) -> None:
        """Insert a finding into the database."""
        if self.conn is None:
            raise RuntimeError("Database connection not initialized")

        cursor = self.conn.cursor()
        finding_metadata_json = (
            json.dumps(finding_metadata) if finding_metadata else None
        )

        _ = cursor.execute(
            """
            INSERT OR REPLACE INTO findings (
                uuid, rule_id, rule_name, file_path, line_number, code_snippet,
                finding_metadata, cwe, language, label, project_uuid, level,
                summary, description
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                uuid,
                rule_id,
                rule_name,
                file_path,
                line_number,
                code_snippet,
                finding_metadata_json,
                cwe,
                language,
                label,
                project_uuid,
                level,
                summary,
                description,
            ),
        )
        _ = self.conn.commit()

    def insert_rule(
        self,
        uuid: str,
        rule_id: str,
        rule_name: str | None = None,
        language: str | None = None,
        cwe: str | None = None,
        yaml_content: str | None = None,
        rule_json: dict[str, Any] | None = None,
        disabled: bool = False,
    ) -> None:
        """Insert a rule into the database."""
        if self.conn is None:
            raise RuntimeError("Database connection not initialized")

        cursor = self.conn.cursor()
        rule_json_str = json.dumps(rule_json) if rule_json else None

        _ = cursor.execute(
            """
            INSERT OR REPLACE INTO rules (
                uuid, rule_id, rule_name, language, cwe, yaml_content,
                rule_json, disabled
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                uuid,
                rule_id,
                rule_name,
                language,
                cwe,
                yaml_content,
                rule_json_str,
                1 if disabled else 0,
            ),
        )
        _ = self.conn.commit()

    def insert_rule_pattern(
        self,
        rule_uuid: str,
        rule_id: str,
        pattern_type: str,
        pattern_text: str | None = None,
        pattern_json: dict[str, Any] | None = None,
    ) -> None:
        """Insert a rule pattern into the database."""
        if self.conn is None:
            raise RuntimeError("Database connection not initialized")

        cursor = self.conn.cursor()
        pattern_json_str = json.dumps(pattern_json) if pattern_json else None

        _ = cursor.execute(
            """
            INSERT INTO rule_patterns (
                rule_uuid, rule_id, pattern_type, pattern_text, pattern_json
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (rule_uuid, rule_id, pattern_type, pattern_text, pattern_json_str),
        )
        _ = self.conn.commit()

    def insert_ground_truth(
        self,
        file_path: str,
        line_number: int,
        cwe: str,
        label: str,
        language: str,
    ) -> None:
        """Insert ground truth label into the database."""
        if self.conn is None:
            raise RuntimeError("Database connection not initialized")

        cursor = self.conn.cursor()
        _ = cursor.execute(
            """
            INSERT OR REPLACE INTO ground_truth (
                file_path, line_number, cwe, label, language
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (file_path, line_number, cwe, label, language),
        )
        _ = self.conn.commit()

    def get_findings_by_rule(
        self, rule_id: str, label: str | None = None
    ) -> list[dict[str, Any]]:
        """Get findings by rule_id, optionally filtered by label."""
        if self.conn is None:
            raise RuntimeError("Database connection not initialized")

        cursor = self.conn.cursor()
        if label:
            _ = cursor.execute(
                """
                SELECT * FROM findings
                WHERE rule_id = ? AND label = ?
                ORDER BY file_path, line_number
                """,
                (rule_id, label),
            )
        else:
            _ = cursor.execute(
                """
                SELECT * FROM findings
                WHERE rule_id = ?
                ORDER BY file_path, line_number
                """,
                (rule_id,),
            )

        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def get_rule_by_id(self, rule_id: str) -> dict[str, Any] | None:
        """Get rule by rule_id."""
        if self.conn is None:
            raise RuntimeError("Database connection not initialized")

        cursor = self.conn.cursor()
        _ = cursor.execute("SELECT * FROM rules WHERE rule_id = ?", (rule_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_rule_patterns(
        self, rule_id: str, pattern_type: str | None = None
    ) -> list[dict[str, Any]]:
        """Get rule patterns, optionally filtered by pattern_type."""
        if self.conn is None:
            raise RuntimeError("Database connection not initialized")

        cursor = self.conn.cursor()
        if pattern_type:
            _ = cursor.execute(
                """
                SELECT * FROM rule_patterns
                WHERE rule_id = ? AND pattern_type = ?
                """,
                (rule_id, pattern_type),
            )
        else:
            _ = cursor.execute(
                "SELECT * FROM rule_patterns WHERE rule_id = ?", (rule_id,)
            )

        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def get_all_findings(self) -> list[dict[str, Any]]:
        """Get all findings from database."""
        if self.conn is None:
            raise RuntimeError("Database connection not initialized")

        cursor = self.conn.cursor()
        _ = cursor.execute("SELECT * FROM findings")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def get_all_rules(self) -> list[dict[str, Any]]:
        """Get all rules from database."""
        if self.conn is None:
            raise RuntimeError("Database connection not initialized")

        cursor = self.conn.cursor()
        _ = cursor.execute("SELECT * FROM rules")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def get_all_rule_patterns(self) -> list[dict[str, Any]]:
        """Get all rule patterns from database."""
        if self.conn is None:
            raise RuntimeError("Database connection not initialized")

        cursor = self.conn.cursor()
        _ = cursor.execute("SELECT * FROM rule_patterns")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def get_all_ground_truth(self) -> list[dict[str, Any]]:
        """Get all ground truth labels from database."""
        if self.conn is None:
            raise RuntimeError("Database connection not initialized")

        cursor = self.conn.cursor()
        _ = cursor.execute("SELECT * FROM ground_truth")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def execute_query(
        self, sql: str, params: tuple[Any, ...] | None = None
    ) -> list[dict[str, Any]]:
        """Execute a SQL query and return results.

        Args:
            sql: SQL query string
            params: Optional parameters for parameterized query

        Returns:
            List of dictionaries representing rows

        """
        if self.conn is None:
            raise RuntimeError("Database connection not initialized")

        cursor = self.conn.cursor()
        if params:
            _ = cursor.execute(sql, params)
        else:
            _ = cursor.execute(sql)

        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def close(self) -> None:
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None

    def __enter__(self) -> Self:
        """Context manager entry."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> None:
        """Context manager exit."""
        self.close()
