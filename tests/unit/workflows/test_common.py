"""Unit tests for endorlabs.workflows.common."""

from unittest.mock import Mock

from endorlabs.workflows.common import (
    WorkflowResult,
    _build_url_variants,
    find_project_by_repository_url,
)

# ---------------------------------------------------------------------------
# WorkflowResult
# ---------------------------------------------------------------------------


class TestWorkflowResult:
    """Tests for WorkflowResult base dataclass."""

    def test_defaults(self) -> None:
        r = WorkflowResult()
        assert r.status == "success"
        assert r.message == ""
        assert r.errors == []
        assert r.ok is True

    def test_error_status(self) -> None:
        r = WorkflowResult(status="error", message="boom", errors=["e1"])
        assert r.ok is False
        assert r.errors == ["e1"]

    def test_partial_status(self) -> None:
        r = WorkflowResult(status="partial")
        assert r.ok is False


# ---------------------------------------------------------------------------
# _build_url_variants
# ---------------------------------------------------------------------------


class TestBuildUrlVariants:
    """Tests for URL variant generation."""

    def test_github_url_produces_expected_variants(self) -> None:
        url = "https://github.com/org/repo"
        variants = _build_url_variants(url)
        # Must contain meta.name, spec.git.web_url, api.github.com, and .git variants
        assert any("meta.name" in v and url in v for v in variants)
        assert any("spec.git.web_url" in v and url in v for v in variants)
        assert any("api.github.com" in v for v in variants)
        assert any(".git" in v for v in variants)
        assert any("spec.git.full_name" in v and "repo" in v for v in variants)

    def test_non_github_url(self) -> None:
        url = "https://gitlab.com/team/project"
        variants = _build_url_variants(url)
        # Should still produce variants without error
        assert len(variants) >= 3
        assert any("meta.name" in v for v in variants)

    def test_trailing_slash_stripped_for_repo_name(self) -> None:
        url = "https://github.com/org/repo/"
        variants = _build_url_variants(url)
        # The repo name extraction should handle trailing slash
        assert any("repo" in v for v in variants)


# ---------------------------------------------------------------------------
# find_project_by_repository_url
# ---------------------------------------------------------------------------


def _make_mock_client(
    filter_results: dict[str, list] | None = None,
    all_results: list | None = None,
) -> Mock:
    """Build a mock Client with project.list() behaviour.

    Args:
        filter_results: Mapping of filter substring -> return value.
        all_results: Return value when list() is called with no filter.
    """
    client = Mock()
    filter_results = filter_results or {}
    all_results = all_results or []

    def _list_side_effect(
        namespace: str | None = None,
        filter: str | None = None,
        max_pages: int | None = None,
        **kwargs: object,
    ) -> list:
        if filter:
            for key, value in filter_results.items():
                if key in filter:
                    return value
        return all_results

    client.Project.list.side_effect = _list_side_effect
    return client


def _make_project(uuid: str = "proj-uuid", name: str = "test-project") -> Mock:
    """Create a mock Project resource."""
    proj = Mock()
    proj.uuid = uuid
    proj.meta.name = name
    proj.model_dump.return_value = {"meta": {"name": name}, "uuid": uuid}
    return proj


class TestFindProjectByRepositoryUrl:
    """Tests for find_project_by_repository_url."""

    def test_finds_by_meta_name_filter(self) -> None:
        proj = _make_project()
        client = _make_mock_client(
            filter_results={"meta.name": [proj]},
        )
        result = find_project_by_repository_url(
            client, "ns", "https://github.com/org/repo"
        )
        assert result == "proj-uuid"

    def test_finds_by_web_url_filter(self) -> None:
        proj = _make_project()
        client = _make_mock_client(
            filter_results={"spec.git.web_url": [proj]},
        )
        result = find_project_by_repository_url(
            client, "ns", "https://github.com/org/repo"
        )
        assert result == "proj-uuid"

    def test_fallback_to_full_search(self) -> None:
        proj = _make_project(name="https://github.com/org/repo.git")
        proj.model_dump.return_value = {
            "meta": {"name": "https://github.com/org/repo.git"},
            "uuid": "proj-uuid",
        }
        client = _make_mock_client(all_results=[proj])
        result = find_project_by_repository_url(
            client, "ns", "https://github.com/org/repo"
        )
        assert result == "proj-uuid"

    def test_returns_none_when_not_found(self) -> None:
        client = _make_mock_client()
        result = find_project_by_repository_url(
            client, "ns", "https://github.com/org/nonexistent"
        )
        assert result is None

    def test_returns_first_match(self) -> None:
        proj1 = _make_project(uuid="first")
        proj2 = _make_project(uuid="second")
        client = _make_mock_client(
            filter_results={"meta.name": [proj1, proj2]},
        )
        result = find_project_by_repository_url(
            client, "ns", "https://github.com/org/repo"
        )
        assert result == "first"

    def test_uses_provided_namespace(self) -> None:
        client = _make_mock_client()
        find_project_by_repository_url(
            client, "my-tenant.my-ns", "https://github.com/org/repo"
        )
        # Verify namespace was passed to all list calls
        for call in client.Project.list.call_args_list:
            assert call.kwargs.get("namespace") == "my-tenant.my-ns"
