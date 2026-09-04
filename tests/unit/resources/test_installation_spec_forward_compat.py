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


def test_installation_model_parses_huggingface_config() -> None:
    """Installation accepts huggingface_config on forward-compatible rows."""
    installation = Installation(
        **_installation_payload(
            {
                "platform_type": "PLATFORM_SOURCE_HUGGING_FACE",
                "huggingface_config": {
                    "host_url": "https://example.com/example-org",
                },
            }
        )
    )
    assert installation.spec is not None
    dumped = installation.spec.model_dump()
    assert dumped.get("platform_type") == "PLATFORM_SOURCE_HUGGING_FACE"
    assert dumped.get("huggingface_config", {}).get("host_url") == (
        "https://example.com/example-org"
    )
