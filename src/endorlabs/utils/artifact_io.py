"""JSON artifact helpers for workflow output directories."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from endorlabs.utils.logging_config import get_resource_logger
from endorlabs.utils.path_safety import safe_write_text

logger = get_resource_logger(__name__)


def slugify(name: str, max_len: int = 80) -> str:
    """Turn a package/project name into a filesystem-safe slug."""
    s = re.sub(r"https?://github\.com/", "", name)
    s = s.rstrip(".git").rstrip("/")
    s = re.sub(r"[^a-zA-Z0-9._-]+", "_", s)
    s = s.strip("_")
    return s[:max_len] if s else "unknown"


def write_json(path: str | Path, data: Any, *, base_dir: Path | None = None) -> None:
    """Write *data* as formatted JSON, creating parent directories.

    When *base_dir* is provided the target path is resolved and checked
    for containment so that ``../`` sequences cannot escape the intended
    output directory.
    """
    path = Path(path)
    content = json.dumps(data, indent=2, default=str, ensure_ascii=False)
    write_root = base_dir if base_dir is not None else path.parent
    safe_write_text(write_root, path, content)
    logger.info("  Wrote %s", path)
