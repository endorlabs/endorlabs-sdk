"""Unit tests for sync planner shard composition."""
# pyright: reportMissingImports=false

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[4]
_SCRIPTS_DIR = str(_REPO_ROOT / "scripts")
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

from sync.planner import build_plan


def test_build_plan_includes_transitive_definition_refs() -> None:
    spec = {
        "swagger": "2.0",
        "paths": {
            "/v1/namespaces/{tenant_meta.namespace}/findings": {
                "get": {
                    "operationId": "FindingServiceListFindings",
                    "tags": ["FindingService"],
                    "responses": {
                        "200": {"schema": {"$ref": "#/definitions/v1Finding"}}
                    },
                }
            }
        },
        "definitions": {
            "v1Finding": {
                "type": "object",
                "properties": {
                    "spec": {"$ref": "#/definitions/v1FindingSpec"},
                },
            },
            "v1FindingSpec": {
                "type": "object",
                "properties": {
                    "details": {
                        "type": "array",
                        "items": {"$ref": "#/definitions/v1FindingDetails"},
                    }
                },
            },
            "v1FindingDetails": {"type": "object"},
        },
    }

    plan = build_plan(spec)
    assert plan.schema_shards
    first_shard = next(iter(plan.schema_shards.values()))
    definitions = first_shard["definitions"]
    assert "v1Finding" in definitions
    assert "v1FindingSpec" in definitions
    assert "v1FindingDetails" in definitions
