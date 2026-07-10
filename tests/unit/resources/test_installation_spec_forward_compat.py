"""Regression tests for Installation spec forward compatibility."""

from endorlabs.resources.installation import Installation, InstallationSpec


def _installation_payload(spec: dict) -> dict:
    return {
        "uuid": "11111111-1111-1111-1111-111111111111",
        "meta": {"name": "sample-installation"},
        "tenant_meta": {"namespace": "tenant"},
        "spec": spec,
    }


def test_installation_spec_accepts_new_bitbucket_shape_without_legacy_fields() -> None:
    """API can return modern bitbucket_config without legacy keys."""
    spec = InstallationSpec(
        bitbucket_config={
            "host_url": "https://bitbucket.org/example",
            "enable_full_scan": True,
            "enable_pr_scans": True,
            "enable_pr_comments": False,
        }
    )

    assert spec.bitbucket_config is not None
    assert spec.bitbucket_config.host_url == "https://bitbucket.org/example"
    assert spec.bitbucket_config.workspace is None
    assert spec.bitbucket_config.access_token is None


def test_installation_model_parses_partial_bitbucket_config() -> None:
    """Top-level Installation model should not fail on partial bitbucket config."""
    installation = Installation(
        **_installation_payload(
            {
                "bitbucket_config": {
                    "host_url": "https://bitbucket.org/example",
                    "enable_pr_comments": False,
                },
                "schema_field_from_future": "allowed-for-forward-compat",
            }
        )
    )

    assert installation.spec is not None
    assert installation.spec.bitbucket_config is not None
    assert (
        installation.spec.bitbucket_config.host_url == "https://bitbucket.org/example"
    )
