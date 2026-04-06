"""Code generation utilities for model-sync."""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
from pathlib import Path
from typing import Any

from .provenance import watermark_header, write_json

logger = logging.getLogger(__name__)


def load_profiles(profiles_dir: Path) -> dict[str, Any]:
    """Load profile files used for sync policy metadata."""
    profile_files = (
        "aliases.json",
        "base_class_map.json",
        "enum_policy.json",
        "partition_rules.json",
    )
    payload: dict[str, Any] = {}
    for filename in profile_files:
        path = profiles_dir / filename
        payload[filename] = (
            {"missing": True}
            if not path.exists()
            else json.loads(path.read_text(encoding="utf-8"))
        )
    return payload


def _run_command(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    resolved = list(command)
    executable = shutil.which(resolved[0])
    if executable is not None:
        resolved[0] = executable
    return subprocess.run(  # noqa: S603
        resolved,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
    )


def _repo_relative_cli_argument(path: Path, repo_root: Path) -> str:
    """Repo-root-relative path with POSIX separators (stable command logs)."""
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _build_codegen_command(
    repo_root: Path, input_path: Path, output_file: Path
) -> list[str]:
    return [
        "datamodel-codegen",
        "--input",
        _repo_relative_cli_argument(input_path, repo_root),
        "--input-file-type",
        "jsonschema",
        "--output",
        _repo_relative_cli_argument(output_file, repo_root),
        "--output-model-type",
        "pydantic_v2.BaseModel",
        "--target-python-version",
        "3.13",
        "--use-union-operator",
        "--field-constraints",
        "--disable-timestamp",
    ]


def generate_modules(
    *,
    repo_root: Path,
    model_output: Path,
    schema_shards: dict[str, dict[str, Any]],
    provenance: dict[str, Any],
) -> tuple[bool, str, list[str]]:
    """Generate module files from deterministic schema shards."""
    shards_dir = model_output / "schema_shards"
    generated_dir = model_output / "generated"
    mapping_dir = model_output / "mapping"
    shards_dir.mkdir(parents=True, exist_ok=True)
    generated_dir.mkdir(parents=True, exist_ok=True)
    mapping_dir.mkdir(parents=True, exist_ok=True)

    module_paths = sorted(schema_shards)
    total = len(module_paths)
    progress_path = mapping_dir / "progress.json"
    write_json(
        progress_path,
        {"total_modules": total, "completed_modules": 0, "last_module": None},
    )
    logger.info("model-sync: preparing %s module shard(s)", total)

    header = watermark_header(provenance)
    commands: list[str] = []
    for index, module_path in enumerate(module_paths, start=1):
        shard_path = shards_dir / f"{module_path.replace('/', '__')}.json"
        shard_payload = schema_shards[module_path]
        shard_path.write_text(
            json.dumps(shard_payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        output_file = generated_dir / f"{module_path}.py"
        output_file.parent.mkdir(parents=True, exist_ok=True)
        command = _build_codegen_command(repo_root, shard_path, output_file)
        commands.append(" ".join(command))
        result = _run_command(command, repo_root)
        if result.returncode != 0:
            message = (result.stderr or result.stdout).strip()
            return (
                False,
                f"Shard generation failed for {module_path}: {message}",
                commands,
            )

        generated_content = output_file.read_text(encoding="utf-8")
        output_file.write_text(header + "\n" + generated_content, encoding="utf-8")

        if index == 1 or index % 10 == 0 or index == total:
            logger.info(
                "model-sync: generated %s/%s module shard(s) (current: %s)",
                index,
                total,
                module_path,
            )
        write_json(
            progress_path,
            {
                "total_modules": total,
                "completed_modules": index,
                "last_module": module_path,
            },
        )
    return (True, f"Generated {total} module shard(s).", commands)
