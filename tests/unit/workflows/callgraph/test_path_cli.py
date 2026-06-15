"""Unit tests for call-graph search CLI path mode."""

from __future__ import annotations

import json
from pathlib import Path

from endorlabs.workflows.callgraph.search import parse_search_args, run_search_main

_FIXTURE = (
    Path(__file__).resolve().parents[3]
    / "fixtures"
    / "callgraph"
    / "minimal_wrapper_chain.json"
)


def test_parse_search_args_path_flags() -> None:
    args = parse_search_args(
        [
            "--callables",
            "c.json",
            "--edges",
            "e.json",
            "--path-from",
            "APIClient",
            "--path-from",
            "get",
            "--path-to",
            "Client.request",
            "--max-depth",
            "4",
        ]
    )
    assert args.path_from == ["APIClient", "get"]
    assert args.path_to == ["Client.request"]
    assert args.max_depth == 4


def test_run_search_main_path_mode_stdout(capsys) -> None:
    data = json.loads(_FIXTURE.read_text(encoding="utf-8"))
    callables_path = _FIXTURE.parent / "_tmp_callables.json"
    edges_path = _FIXTURE.parent / "_tmp_edges.json"
    callables_path.write_text(json.dumps(data["callables"]), encoding="utf-8")
    edges_path.write_text(json.dumps(data["edges"]), encoding="utf-8")
    try:
        rc = run_search_main(
            [
                "--callables",
                str(callables_path),
                "--edges",
                str(edges_path),
                "--path-from",
                "APIClient",
                "--path-from",
                "get",
                "--path-to",
                "Client.request",
            ]
        )
        assert rc == 0
        out = capsys.readouterr().out
        payload = json.loads(out)
        assert payload["path_found"] is True
    finally:
        callables_path.unlink(missing_ok=True)
        edges_path.unlink(missing_ok=True)


def test_run_search_main_rejects_mixed_modes() -> None:
    rc = run_search_main(
        [
            "--callables",
            "c.json",
            "--edges",
            "e.json",
            "--path-from",
            "a",
            "--path-to",
            "b",
            "--source-pattern",
            "x",
        ]
    )
    assert rc == 2
