"""Dependency coordinate parsing helpers."""

from __future__ import annotations


def parse_dep_name(dep_name: str) -> tuple[str, str]:
    """Split ``npm://express@4.22.1`` into ``('npm://express', '4.22.1')``."""
    if "@" not in dep_name:
        return dep_name, ""
    idx = dep_name.rfind("@")
    if idx <= 0:
        return dep_name, ""
    if dep_name[idx - 1] == "/":
        return dep_name, ""
    return dep_name[:idx], dep_name[idx + 1 :]
