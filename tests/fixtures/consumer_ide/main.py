"""Minimal consumer script for manual IDE typing checks."""

from __future__ import annotations

import endorlabs


def smoke() -> None:
    """Exercise common Client facade entry points for Pyright/Pylance."""
    c = endorlabs.Client(tenant="tenant.example")
    _ = c.Project.list(traverse=True)
    _ = c.Project.search_by_name("foo")
    _ = c.ScanResult.get_logs("scan-uuid")
    _ = c.Finding.list_by_project("proj-uuid")


if __name__ == "__main__":
    smoke()
