from __future__ import annotations

from pathlib import Path

import pytest

from endorlabs.workflows.reports.analyze.depr_coverage import (
    bu_label,
    build_depr_coverage_report,
    safe_write,
    theme_bucket,
)
from endorlabs.workflows.reports.analyze.depr_progress import (
    _parse_args as parse_progress_args,
)
from endorlabs.workflows.reports.analyze.depr_progress import (
    build_progress_artifacts,
    load_checkpoint,
)
from endorlabs.workflows.reports.export.html.depr_coverage import (
    render_progress_markdown,
)


@pytest.mark.parametrize(
    ("rule", "ecosystem", "category", "expected"),
    [
        (
            "could_not_find_artifact",
            "maven",
            "",
            "maven_private_artifactory",
        ),
        ("pnpm_workspace_packages_missing", "npm", "", "pnpm_workspace"),
        ("setup_py_file_generic", "pypi", "", "python_setup_py_hygiene"),
        ("nuget_restore_failed", "nuget", "", "nuget_dotnet"),
    ],
)
def test_theme_bucket_classifies_remediation(
    rule: str,
    ecosystem: str,
    category: str,
    expected: str,
) -> None:
    assert theme_bucket(rule, ecosystem, category)[0] == expected


def test_bu_label_humanizes_namespace() -> None:
    assert bu_label("(root)") == "Tenant root"
    assert bu_label("platform_services") == "Platform Services"


def _checkpoint(
    generated_at: str,
    coverage: float,
    healthy_rate: float,
    resolved: int,
    full: int,
) -> dict:
    return {
        "tenant": "example-tenant",
        "generated_at": generated_at,
        "estate": {
            "coverage_pv_pct": coverage,
            "coverage_fully_resolved_project_pct": healthy_rate,
            "packages_resolved": resolved,
            "full": full,
        },
        "by_child_namespace": [
            {
                "child_namespace": "platform_services",
                "coverage_pv_pct": coverage,
                "packages_resolved": resolved,
                "full_resolution": full,
            }
        ],
        "org_themes": {
            "themes": [
                {
                    "theme_id": "maven_private_artifactory",
                    "projects": 4 if coverage < 70 else 2,
                    "packages": 8 if coverage < 70 else 3,
                }
            ]
        },
    }


def test_render_progress_markdown_uses_checkpoint_metrics() -> None:
    text = render_progress_markdown(
        [
            _checkpoint("20260101T100000Z", 60.0, 50.0, 600, 50),
            _checkpoint("20260115T100000Z", 80.0, 75.0, 800, 75),
        ]
    )
    assert "| Package coverage | 60.0% | 80.0%" in text
    assert "+20.0 pp" in text
    assert "Platform Services" in text
    assert "+200 packages" in text


def test_safe_write_refuses_overwrite(tmp_path: Path) -> None:
    path = tmp_path / "example-tenant__dr_coverage__20260115T100000Z.json"
    safe_write(path, "{}\n")
    with pytest.raises(FileExistsError):
        safe_write(path, "{}\n")


def test_progress_accepts_explicit_json_without_dates(tmp_path: Path) -> None:
    paths = [tmp_path / "first.json", tmp_path / "second.json"]
    args = parse_progress_args(
        ["-n", "example-tenant", "--from-json", *(str(path) for path in paths)]
    )
    assert args.dates is None
    assert args.from_json == paths


def test_load_checkpoint_rejects_non_coverage_json(tmp_path: Path) -> None:
    path = tmp_path / "invalid.json"
    path.write_text('{"generated_at": "20260101T100000Z"}', encoding="utf-8")
    with pytest.raises(TypeError, match="Not a dependency-resolution checkpoint"):
        load_checkpoint(path)


def test_progress_rejects_duplicate_checkpoints(tmp_path: Path) -> None:
    checkpoint = _checkpoint("20260101T100000Z", 60.0, 50.0, 600, 50)
    with pytest.raises(ValueError, match="distinct generated_at"):
        build_progress_artifacts(
            [checkpoint, checkpoint],
            tmp_path,
            "example-tenant",
        )


def test_coverage_rejects_nonpositive_workers() -> None:
    with pytest.raises(ValueError, match="max_workers"):
        build_depr_coverage_report("example-tenant", max_workers=0)
