"""One-off maintainer script: split tools/dependency_explorer.py into focused modules."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "src" / "endorlabs"
SOURCE = PKG / "tools" / "dependency_explorer.py"


def _lines(start: int, end: int) -> str:
    text = SOURCE.read_text(encoding="utf-8")
    return "".join(text.splitlines(keepends=True)[start - 1 : end])


HEADERS: dict[str, str] = {
    "utils/artifact_io.py": '''"""JSON artifact helpers for workflow output directories."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from endorlabs.utils.logging_config import get_resource_logger
from endorlabs.utils.path_safety import safe_write_text

logger = get_resource_logger(__name__)

''',
    "utils/api_pagination.py": '''"""Raw API list pagination helpers for workflow modules."""

from __future__ import annotations

from typing import Any

from endorlabs.api_client import APIClient

''',
    "workflows/dependencies/coordinates.py": '''"""Dependency coordinate parsing helpers."""

from __future__ import annotations

''',
    "workflows/dependencies/bom_graph.py": '''"""BOM graph extraction and slim dependency row shaping."""

from __future__ import annotations

from collections import deque
from typing import Any

from endorlabs.workflows.dependencies.coordinates import parse_dep_name

''',
    "workflows/dependencies/metadata_fetch.py": '''"""DependencyMetadata list fetch and summarization."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from endorlabs.api_client import APIClient
from endorlabs.utils.api_pagination import paginate_raw
from endorlabs.workflows.dependencies.bom_graph import render_slim_dependencies

''',
    "workflows/callgraph/proto_decode.py": '''"""Protobuf wire-format decoder for call graph payloads (no compiled proto)."""

from __future__ import annotations

import base64
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

try:
    import zstandard  # type: ignore[import-untyped]
except ImportError:
    zstandard = None  # type: ignore[assignment]

_HAS_ZSTD = zstandard is not None

''',
    "workflows/callgraph/render.py": '''"""Markdown rendering for decoded call graphs."""

from __future__ import annotations

import textwrap

from endorlabs.workflows.callgraph.proto_decode import CallGraphInfo, CallSiteInfo

''',
    "workflows/callgraph/fetch.py": '''"""Call graph API fetch and summary artifact helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

from endorlabs.utils.logging_config import get_resource_logger
from endorlabs.utils.path_safety import safe_write_text
from endorlabs.workflows.callgraph.proto_decode import _HAS_ZSTD, decode_callgraph
from endorlabs.workflows.callgraph.render import render_callgraph_analysis
from endorlabs.utils.api_pagination import extract_objects

if TYPE_CHECKING:
    from endorlabs import Client
    from endorlabs.api_client import APIClient

logger = get_resource_logger(__name__)

''',
    "workflows/agent_context/hydration.py": '''"""Per-project BOM, DependencyMetadata, and call-graph hydration."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import UTC, datetime
from io import StringIO
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from endorlabs.utils.artifact_io import slugify, write_json
from endorlabs.utils.logging_config import get_resource_logger
from endorlabs.workflows.callgraph.fetch import (
    generate_call_graph_analysis_md,
    render_call_graph_summary_md,
    retrieve_call_graph_full,
    summarize_call_graph,
)
from endorlabs.workflows.dependencies.bom_graph import (
    extract_direct_deps,
    render_slim_dependencies,
    retrieve_bom_full,
)
from endorlabs.workflows.dependencies.metadata_fetch import (
    retrieve_dep_metadata_full,
    summarize_dep_metadata,
)

if TYPE_CHECKING:
    from endorlabs import Client
    from endorlabs.api_client import APIClient

logger = get_resource_logger(__name__)

''',
}

SLICES: dict[str, tuple[int, int]] = {
    "utils/artifact_io.py": (762, 784),
    "utils/api_pagination.py": (787, 837),
    "workflows/dependencies/coordinates.py": (840, 849),
    "workflows/dependencies/bom_graph.py": (857, 967),
    "workflows/dependencies/metadata_fetch.py": (975, 1047),
    "workflows/callgraph/proto_decode.py": (50, 495),
    "workflows/callgraph/render.py": (502, 754),
    "workflows/callgraph/fetch.py": (1055, 1226),
    "workflows/agent_context/hydration.py": (1234, 1586),
}


def main() -> None:
    for rel, (start, end) in SLICES.items():
        path = PKG / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        body = _lines(start, end)
        path.write_text(HEADERS[rel] + body, encoding="utf-8")
        print("wrote", path.relative_to(ROOT))


if __name__ == "__main__":
    main()
