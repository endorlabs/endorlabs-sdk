"""
SQLite3 database schema and operations for finding correlation analysis.

This module provides database schema creation and basic operations for storing
findings, rules, and ground truth data.
"""

import json
import logging
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class FindingDatabase:
    """SQLite3 database for storing findings, rules, and analysis data."""

    def __init__(self, db_path: str):
        """
        Initialize database connection.

        Args:
            db_path: Path to SQLite3 database file
        """
        self.db_path = Path(db_path)
        self.conn: Optional[sqlite3.Connection] = None
        self._create_schema()

    def _create_schema(self) -> None:
        """Create database schema if it doesn't exist."""
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row

        cursor = self.conn.cursor()

        # Findings table
        cursor.execute(
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
        cursor.execute(
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
        cursor.execute(
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
        cursor.execute(
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
            "CREATE INDEX IF NOT EXISTS idx_rule_patterns_rule_uuid ON rule_patterns(rule_uuid)",
            "CREATE INDEX IF NOT EXISTS idx_rule_patterns_rule_id ON rule_patterns(rule_id)",
            "CREATE INDEX IF NOT EXISTS idx_rule_patterns_type ON rule_patterns(pattern_type)",
            "CREATE INDEX IF NOT EXISTS idx_ground_truth_file ON ground_truth(file_path, line_number)",
            "CREATE INDEX IF NOT EXISTS idx_ground_truth_cwe ON ground_truth(cwe)",
        ]

        for index_sql in indexes:
            cursor.execute(index_sql)

        self.conn.commit()
        logger.info(f"Database schema created/verified at {self.db_path}")

    def insert_finding(
        self,
        uuid: str,
        rule_id: Optional[str] = None,
        rule_name: Optional[str] = None,
        file_path: Optional[str] = None,
        line_number: Optional[int] = None,
        code_snippet: Optional[str] = None,
        finding_metadata: Optional[Dict[str, Any]] = None,
        cwe: Optional[str] = None,
        language: Optional[str] = None,
        label: Optional[str] = None,
        project_uuid: Optional[str] = None,
        level: Optional[str] = None,
        summary: Optional[str] = None,
        description: Optional[str] = None,
    ) -> None:
        """Insert a finding into the database."""
        if self.conn is None:
            raise RuntimeError("Database connection not initialized")

        cursor = self.conn.cursor()
        finding_metadata_json = (
            json.dumps(finding_metadata) if finding_metadata else None
        )

        cursor.execute(
            """
            INSERT OR REPLACE INTO findings (
                uuid, rule_id, rule_name, file_path, line_number, code_snippet,
                finding_metadata, cwe, language, label, project_uuid, level, summary, description
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
        self.conn.commit()

    def insert_rule(
        self,
        uuid: str,
        rule_id: str,
        rule_name: Optional[str] = None,
        language: Optional[str] = None,
        cwe: Optional[str] = None,
        yaml_content: Optional[str] = None,
        rule_json: Optional[Dict[str, Any]] = None,
        disabled: bool = False,
    ) -> None:
        """Insert a rule into the database."""
        if self.conn is None:
            raise RuntimeError("Database connection not initialized")

        cursor = self.conn.cursor()
        rule_json_str = json.dumps(rule_json) if rule_json else None

        cursor.execute(
            """
            INSERT OR REPLACE INTO rules (
                uuid, rule_id, rule_name, language, cwe, yaml_content, rule_json, disabled
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
        self.conn.commit()

    def insert_rule_pattern(
        self,
        rule_uuid: str,
        rule_id: str,
        pattern_type: str,
        pattern_text: Optional[str] = None,
        pattern_json: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Insert a rule pattern into the database."""
        if self.conn is None:
            raise RuntimeError("Database connection not initialized")

        cursor = self.conn.cursor()
        pattern_json_str = json.dumps(pattern_json) if pattern_json else None

        cursor.execute(
            """
            INSERT INTO rule_patterns (
                rule_uuid, rule_id, pattern_type, pattern_text, pattern_json
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (rule_uuid, rule_id, pattern_type, pattern_text, pattern_json_str),
        )
        self.conn.commit()

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
        cursor.execute(
            """
            INSERT OR REPLACE INTO ground_truth (
                file_path, line_number, cwe, label, language
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (file_path, line_number, cwe, label, language),
        )
        self.conn.commit()

    def get_findings_by_rule(
        self, rule_id: str, label: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get findings by rule_id, optionally filtered by label."""
        if self.conn is None:
            raise RuntimeError("Database connection not initialized")

        cursor = self.conn.cursor()
        if label:
            cursor.execute(
                """
                SELECT * FROM findings
                WHERE rule_id = ? AND label = ?
                ORDER BY file_path, line_number
                """,
                (rule_id, label),
            )
        else:
            cursor.execute(
                """
                SELECT * FROM findings
                WHERE rule_id = ?
                ORDER BY file_path, line_number
                """,
                (rule_id,),
            )

        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def get_rule_by_id(self, rule_id: str) -> Optional[Dict[str, Any]]:
        """Get rule by rule_id."""
        if self.conn is None:
            raise RuntimeError("Database connection not initialized")

        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM rules WHERE rule_id = ?", (rule_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_rule_patterns(
        self, rule_id: str, pattern_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get rule patterns, optionally filtered by pattern_type."""
        if self.conn is None:
            raise RuntimeError("Database connection not initialized")

        cursor = self.conn.cursor()
        if pattern_type:
            cursor.execute(
                """
                SELECT * FROM rule_patterns
                WHERE rule_id = ? AND pattern_type = ?
                """,
                (rule_id, pattern_type),
            )
        else:
            cursor.execute(
                "SELECT * FROM rule_patterns WHERE rule_id = ?", (rule_id,)
            )

        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def get_all_findings(self) -> List[Dict[str, Any]]:
        """Get all findings from database."""
        if self.conn is None:
            raise RuntimeError("Database connection not initialized")

        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM findings")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def get_all_rules(self) -> List[Dict[str, Any]]:
        """Get all rules from database."""
        if self.conn is None:
            raise RuntimeError("Database connection not initialized")

        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM rules")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def get_all_rule_patterns(self) -> List[Dict[str, Any]]:
        """Get all rule patterns from database."""
        if self.conn is None:
            raise RuntimeError("Database connection not initialized")

        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM rule_patterns")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def get_all_ground_truth(self) -> List[Dict[str, Any]]:
        """Get all ground truth labels from database."""
        if self.conn is None:
            raise RuntimeError("Database connection not initialized")

        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM ground_truth")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def execute_query(self, sql: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """
        Execute a SQL query and return results.

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
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)

        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def close(self) -> None:
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

