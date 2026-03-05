"""Unit tests for demo CLI catalog behavior."""

from __future__ import annotations

from types import SimpleNamespace

from endorlabs.agent.demo_cli import (
    TenantCatalog,
    _normalize_wizard_auth_method,
    _parse_args,
    _parse_project_target_choice,
    _prompt_yes_no,
    _resolve_project_by_uuid,
    _select_auto_project_candidate,
    _summarize_findings,
)


def _project(uuid: str, name: str, namespace: str) -> SimpleNamespace:
    """Build a minimal project-like object for catalog tests."""
    return SimpleNamespace(
        uuid=uuid,
        meta=SimpleNamespace(name=name),
        tenant_meta=SimpleNamespace(namespace=namespace),
    )


def test_catalog_keeps_duplicate_repo_urls_by_namespace() -> None:
    """Projects sharing repo URL across namespaces should both be indexed."""
    project_name = "https://github.com/org/repo.git"
    proj_a = _project("uuid-a", project_name, "tenant.ns-a")
    proj_b = _project("uuid-b", project_name, "tenant.ns-b")

    fake_client = SimpleNamespace(
        project=SimpleNamespace(
            list=lambda **_kwargs: [proj_a, proj_b],
        ),
        namespace=SimpleNamespace(
            list=lambda **_kwargs: [],
        ),
    )

    catalog = TenantCatalog()
    catalog.load(fake_client)

    assert len(catalog.projects_by_uuid) == 2
    assert proj_a.uuid in catalog.projects_by_uuid
    assert proj_b.uuid in catalog.projects_by_uuid
    assert len(catalog.project_index) == 2
    assert any("[tenant.ns-a]" in key for key in catalog.project_index)
    assert any("[tenant.ns-b]" in key for key in catalog.project_index)


def test_catalog_fuzzy_match_returns_all_duplicate_repo_projects() -> None:
    """Fuzzy search should return both entries for same repo URL."""
    project_name = "https://github.com/org/repo.git"
    proj_a = _project("uuid-a", project_name, "tenant.ns-a")
    proj_b = _project("uuid-b", project_name, "tenant.ns-b")

    fake_client = SimpleNamespace(
        project=SimpleNamespace(
            list=lambda **_kwargs: [proj_a, proj_b],
        ),
        namespace=SimpleNamespace(
            list=lambda **_kwargs: [],
        ),
    )

    catalog = TenantCatalog()
    catalog.load(fake_client)

    matches = catalog.fuzzy_match("org/repo")
    match_uuids = {p.uuid for p in matches}
    assert match_uuids == {"uuid-a", "uuid-b"}


def test_parse_args_defaults_to_wizard_mode() -> None:
    """CLI defaults to wizard mode unless --agent is requested."""
    parsed = _parse_args([])
    assert parsed.agent is False
    assert parsed.message == []


def test_parse_args_accepts_agent_mode_and_message() -> None:
    """Agent mode accepts trailing message tokens."""
    parsed = _parse_args(["--agent", "what", "is", "my", "risk"])
    assert parsed.agent is True
    assert parsed.message == ["what", "is", "my", "risk"]


def test_parse_project_target_choice_enter_yes_no_uuid_and_invalid() -> None:
    """Project target parser supports enter-auto, y/n, and UUID routing."""
    assert _parse_project_target_choice("").action == "search"
    assert _parse_project_target_choice("Y").action == "search"
    assert _parse_project_target_choice("yes").action == "search"
    assert _parse_project_target_choice("n").action == "skip"
    assert _parse_project_target_choice("Skip").action == "skip"

    parsed_uuid = _parse_project_target_choice("698cfb4f26aee2696691c78e")
    assert parsed_uuid.action == "uuid"
    assert parsed_uuid.uuid == "698cfb4f26aee2696691c78e"

    assert _parse_project_target_choice("not-a-uuid").action == "invalid"


def test_resolve_project_by_uuid_returns_first_match_or_none() -> None:
    """UUID resolution uses traverse search and returns first result."""
    expected = _project(
        "698cfb4f26aee2696691c78e",
        "https://github.com/Endor-Solutions-Architecture/endorlabs-sdk.git",
        "endor-solutions-tgowan.tgowan-endor",
    )
    captured: dict[str, object] = {}

    def _list(**kwargs: object) -> list[SimpleNamespace]:
        captured.update(kwargs)
        return [expected]

    fake_client = SimpleNamespace(project=SimpleNamespace(list=_list))
    found = _resolve_project_by_uuid(fake_client, expected.uuid)
    assert found == expected
    assert captured["traverse"] is True

    fake_client_empty = SimpleNamespace(
        project=SimpleNamespace(list=lambda **_kwargs: []),
    )
    missing = _resolve_project_by_uuid(fake_client_empty, expected.uuid)
    assert missing is None


def test_select_auto_project_candidate_prefers_query_match() -> None:
    """Auto selection should prefer a project matching the user query."""
    proj_a = _project("uuid-a", "https://github.com/org/one.git", "tenant.ns-a")
    proj_b = _project("uuid-b", "https://github.com/org/two.git", "tenant.ns-b")
    selected = _select_auto_project_candidate([proj_a, proj_b], "org/two")
    assert selected == proj_b


def test_select_auto_project_candidate_falls_back_to_first() -> None:
    """Auto selection should fall back to first eligible project."""
    proj_a = _project("uuid-a", "https://github.com/org/one.git", "tenant.ns-a")
    proj_b = _project("uuid-b", "https://github.com/org/two.git", "tenant.ns-b")
    selected = _select_auto_project_candidate([proj_a, proj_b], "does-not-match")
    assert selected == proj_a


def test_prompt_yes_no_enter_defaults_to_yes(monkeypatch: object) -> None:
    """Enter should resolve to yes for consistent wizard y/n prompts."""
    monkeypatch.setattr("builtins.input", lambda _prompt: "")
    assert _prompt_yes_no("Continue? [Y/n]: ", default_yes=True) is True


def test_prompt_yes_no_explicit_no_is_respected(monkeypatch: object) -> None:
    """Explicit no should still disable y/n actions."""
    monkeypatch.setattr("builtins.input", lambda _prompt: "n")
    assert _prompt_yes_no("Continue? [Y/n]: ", default_yes=True) is False


def test_summarize_findings_returns_category_and_tag_counts() -> None:
    """Workflow summary should aggregate categories and tags from findings."""
    findings = [
        SimpleNamespace(
            spec=SimpleNamespace(
                finding_categories=["FINDING_CATEGORY_SAST"],
                finding_tags=["reviewed", "reachable"],
            )
        ),
        SimpleNamespace(
            spec=SimpleNamespace(
                finding_categories=["FINDING_CATEGORY_SAST", "FINDING_CATEGORY_SCA"],
                finding_tags=["reviewed"],
            )
        ),
    ]
    category_counts, tag_counts = _summarize_findings(findings)
    assert category_counts["FINDING_CATEGORY_SAST"] == 2
    assert category_counts["FINDING_CATEGORY_SCA"] == 1
    assert tag_counts["reviewed"] == 2
    assert tag_counts["reachable"] == 1


def test_normalize_wizard_auth_method_supports_browser_alias() -> None:
    """Wizard auth parser should map browser alias to browser-auth."""
    normalized = _normalize_wizard_auth_method("browser", default="api-key")
    assert normalized == "browser-auth"


def test_normalize_wizard_auth_method_falls_back_on_invalid() -> None:
    """Unsupported wizard auth input should fall back to the default."""
    normalized = _normalize_wizard_auth_method("invalid-mode", default="api-key")
    assert normalized == "api-key"
