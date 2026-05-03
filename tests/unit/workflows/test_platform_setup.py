"""Unit tests for endorlabs.workflows.platform.setup."""

from unittest.mock import Mock

from endorlabs.workflows.platform.setup import (
    AuthorizationPolicyResult,
    NamespaceResult,
    ScanProfileResult,
    create_authorization_policy,
    create_child_namespace,
    create_github_installation,
    create_scan_profile_with_defaults,
)

# ---------------------------------------------------------------------------
# create_child_namespace
# ---------------------------------------------------------------------------


class TestCreateChildNamespace:
    """Tests for create_child_namespace."""

    def test_dry_run(self) -> None:
        client = Mock()
        result = create_child_namespace(client, "tenant", "child", dry_run=True)
        assert isinstance(result, NamespaceResult)
        assert result.ok is True
        assert "DRY RUN" in result.message
        client.Namespace.create.assert_not_called()

    def test_creates_namespace(self) -> None:
        client = Mock()
        client.Namespace.create.return_value = Mock(uuid="ns-1")

        result = create_child_namespace(
            client, "tenant", "child", description="My child ns"
        )
        assert result.uuid == "ns-1"
        assert result.name == "child"
        assert result.parent == "tenant"
        assert result.ok is True

    def test_handles_error(self) -> None:
        client = Mock()
        client.Namespace.create.side_effect = RuntimeError("conflict")

        result = create_child_namespace(client, "tenant", "child")
        assert result.status == "error"
        assert "conflict" in result.message


# ---------------------------------------------------------------------------
# create_github_installation
# ---------------------------------------------------------------------------


class TestCreateGithubInstallation:
    """Tests for create_github_installation."""

    def test_dry_run(self) -> None:
        client = Mock()
        result = create_github_installation(client, "ns", "my-install", dry_run=True)
        assert result.ok is True
        assert "DRY RUN" in result.message

    def test_creates_installation(self) -> None:
        client = Mock()
        client.Installation.create.return_value = Mock(uuid="inst-1")

        result = create_github_installation(
            client, "ns", "my-install", github_org="my-org"
        )
        assert result.uuid == "inst-1"
        assert result.ok is True
        kw = client.Installation.create.call_args.kwargs
        assert kw["github_org"] == "my-org"

    def test_handles_error(self) -> None:
        client = Mock()
        client.Installation.create.side_effect = RuntimeError("400")

        result = create_github_installation(client, "ns", "my-install")
        assert result.status == "error"

    def test_extra_kwargs_forwarded(self) -> None:
        client = Mock()
        client.Installation.create.return_value = Mock(uuid="inst-1")

        create_github_installation(client, "ns", "my-install", scan_enabled=True)
        kw = client.Installation.create.call_args.kwargs
        assert kw["scan_enabled"] is True


# ---------------------------------------------------------------------------
# create_scan_profile_with_defaults
# ---------------------------------------------------------------------------


class TestCreateScanProfileWithDefaults:
    """Tests for create_scan_profile_with_defaults."""

    def test_dry_run(self) -> None:
        client = Mock()
        result = create_scan_profile_with_defaults(
            client, "ns", "my-profile", dry_run=True
        )
        assert isinstance(result, ScanProfileResult)
        assert result.ok is True
        assert "DRY RUN" in result.message

    def test_creates_profile(self) -> None:
        client = Mock()
        client.ScanProfile.create.return_value = Mock(uuid="sp-1")

        result = create_scan_profile_with_defaults(
            client, "ns", "my-profile", is_default=True
        )
        assert result.uuid == "sp-1"
        assert result.ok is True
        kw = client.ScanProfile.create.call_args.kwargs
        assert kw["is_default"] is True
        assert kw["propagate"] is True

    def test_propagate_false(self) -> None:
        client = Mock()
        client.ScanProfile.create.return_value = Mock(uuid="sp-1")

        create_scan_profile_with_defaults(client, "ns", "my-profile", propagate=False)
        kw = client.ScanProfile.create.call_args.kwargs
        assert kw["propagate"] is False

    def test_handles_error(self) -> None:
        client = Mock()
        client.ScanProfile.create.side_effect = RuntimeError("500")

        result = create_scan_profile_with_defaults(client, "ns", "my-profile")
        assert result.status == "error"


# ---------------------------------------------------------------------------
# create_authorization_policy
# ---------------------------------------------------------------------------


class TestCreateAuthorizationPolicy:
    """Tests for create_authorization_policy."""

    def test_dry_run(self) -> None:
        client = Mock()
        result = create_authorization_policy(client, "ns", "my-policy", dry_run=True)
        assert isinstance(result, AuthorizationPolicyResult)
        assert result.ok is True
        assert "DRY RUN" in result.message

    def test_creates_policy(self) -> None:
        client = Mock()
        client.AuthorizationPolicy.create.return_value = Mock(uuid="ap-1")

        result = create_authorization_policy(
            client, "ns", "my-policy", description="Test"
        )
        assert result.uuid == "ap-1"
        assert result.ok is True
        kw = client.AuthorizationPolicy.create.call_args.kwargs
        assert kw["description"] == "Test"

    def test_handles_error(self) -> None:
        client = Mock()
        client.AuthorizationPolicy.create.side_effect = RuntimeError("403")

        result = create_authorization_policy(client, "ns", "my-policy")
        assert result.status == "error"
        assert "403" in result.message

    def test_extra_kwargs_forwarded(self) -> None:
        client = Mock()
        client.AuthorizationPolicy.create.return_value = Mock(uuid="ap-1")

        create_authorization_policy(client, "ns", "my-policy", roles=["admin"])
        kw = client.AuthorizationPolicy.create.call_args.kwargs
        assert kw["roles"] == ["admin"]
