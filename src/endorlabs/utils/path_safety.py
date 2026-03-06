"""Path containment utilities for safe file writes.

Ensures that file write operations cannot escape an allowed base directory
via ``../`` sequences or symlink resolution.  All file writes in the SDK
that target paths derived from parameters, API responses, or user-provided
configuration should go through these helpers.
"""

from __future__ import annotations

from pathlib import Path


def safe_write_text(
    base_dir: Path,
    target: Path,
    content: str,
    encoding: str = "utf-8",
) -> None:
    """Write *content* to *target* after verifying containment in *base_dir*.

    Resolves both paths to their absolute, symlink-free form and checks that
    *target* is inside *base_dir*.  Creates intermediate directories as needed.

    Args:
        base_dir: The allowed root directory.
        target: The file to write (may be relative or contain ``../``).
        content: Text content to write.
        encoding: Text encoding (default ``utf-8``).

    Raises:
        ValueError: If the resolved *target* is outside *base_dir*.
    """
    resolved = target.resolve()
    base_resolved = base_dir.resolve()
    if not resolved.is_relative_to(base_resolved):
        raise ValueError(f"Path {resolved} is outside base directory {base_resolved}")
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(content, encoding=encoding)


def safe_write_bytes(
    base_dir: Path,
    target: Path,
    data: bytes,
) -> None:
    """Write *data* to *target* after verifying containment in *base_dir*.

    Resolves both paths to their absolute, symlink-free form and checks that
    *target* is inside *base_dir*.  Creates intermediate directories as needed.

    Args:
        base_dir: The allowed root directory.
        target: The file to write (may be relative or contain ``../``).
        data: Binary content to write.

    Raises:
        ValueError: If the resolved *target* is outside *base_dir*.
    """
    resolved = target.resolve()
    base_resolved = base_dir.resolve()
    if not resolved.is_relative_to(base_resolved):
        raise ValueError(f"Path {resolved} is outside base directory {base_resolved}")
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_bytes(data)
