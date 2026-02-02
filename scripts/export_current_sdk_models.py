#!/usr/bin/env python3
"""Export current SDK model field paths to JSON for OSS model experiment comparison.

One-off script for G:/temp/endor-oss-model-experiment. Run from endor-cockpit repo:

  uv run python scripts/export_current_sdk_models.py
  uv run python scripts/export_current_sdk_models.py -o /path/to/current_sdk_models.json

Writes model name -> list of dot-separated field paths (same shape as enumerate_sdk_models_flat_paths).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Export current SDK model paths to JSON")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output file (default: stdout)",
    )
    args = parser.parse_args()
    try:
        from endorlabs.utils.model_consistency import enumerate_sdk_models_flat_paths
    except ImportError as e:
        print(f"Import error: {e}", file=sys.stderr)
        return 1
    data = enumerate_sdk_models_flat_paths()
    out = json.dumps(data, indent=2)
    if args.output is not None:
        args.output.write_text(out, encoding="utf-8")
        print(f"Wrote {args.output}", file=sys.stderr)
    else:
        print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
