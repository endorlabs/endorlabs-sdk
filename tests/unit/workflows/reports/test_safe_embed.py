"""A02: HTML-safe JSON embed boundary."""

from __future__ import annotations

from endorlabs.workflows.reports.export.html.safe_embed import (
    html_escape_text,
    html_safe_json,
)


def test_html_safe_json_escapes_script_breakout() -> None:
    raw = html_safe_json({"x": "</script><div onclick=alert(1)>"})
    assert "<" not in raw
    assert ">" not in raw
    assert "\\u003c/script\\u003e" in raw


def test_html_escape_text_escapes_markup() -> None:
    assert "&lt;" in html_escape_text("<b>")
    assert "&amp;" in html_escape_text("a&b")
