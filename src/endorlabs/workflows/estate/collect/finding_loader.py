"""Load Finding records from workspace data."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from endorlabs.workflows.estate.contracts import RESOURCE_FINDING
from endorlabs.workflows.estate.workspace.paths import resource_path


def load_finding_records(workspace_root: Path) -> list[dict[str, Any]]:
    path = resource_path(workspace_root, RESOURCE_FINDING)
    if not path.is_file():
        return []
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            records.append(json.loads(line))
    return records
